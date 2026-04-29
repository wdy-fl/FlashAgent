<!-- src/routes/graph/menu/CustomToolWindow.svelte -->
<script lang="ts">
	import { openCustomToolWindow, username } from './menu.store';
	import { get } from 'svelte/store';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	type ToolEntry = {
		name: string;
		description: string;
		code: string;
	};

	let tools = $state<ToolEntry[]>([]);
	let loading = $state(false);
	let error = $state('');

	// Form state
	let editingName = $state('');
	let formName = $state('');
	let formDescription = $state('');
	let formCode = $state('');
	let showForm = $state(false);

	function getUser(): string {
		return get(username);
	}

	async function loadTools() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${SERVER_URL}/custom-tools/${encodeURIComponent(getUser())}`);
			const data = await res.json();
			tools = data.tools ?? [];
		} catch (e) {
			error = `Failed to load tools: ${e}`;
		} finally {
			loading = false;
		}
	}

	async function saveTool() {
		if (!formName.trim()) return;
		error = '';
		try {
			const user = encodeURIComponent(getUser());
			const body = JSON.stringify({
				name: formName.trim(),
				description: formDescription,
				code: formCode
			});
			const headers = { 'Content-Type': 'application/json' };

			if (editingName) {
				await fetch(`${SERVER_URL}/custom-tools/${user}/${encodeURIComponent(editingName)}`, {
					method: 'PUT',
					headers,
					body
				});
			} else {
				await fetch(`${SERVER_URL}/custom-tools/${user}`, {
					method: 'POST',
					headers,
					body
				});
			}
			resetForm();
			await loadTools();
		} catch (e) {
			error = `Failed to save tool: ${e}`;
		}
	}

	async function removeTool(name: string) {
		error = '';
		try {
			await fetch(
				`${SERVER_URL}/custom-tools/${encodeURIComponent(getUser())}/${encodeURIComponent(name)}`,
				{ method: 'DELETE' }
			);
			await loadTools();
		} catch (e) {
			error = `Failed to remove tool: ${e}`;
		}
	}

	function startEdit(tool: ToolEntry) {
		editingName = tool.name;
		formName = tool.name;
		formDescription = tool.description;
		formCode = tool.code;
		showForm = true;
	}

	function startAdd() {
		resetForm();
		showForm = true;
	}

	function resetForm() {
		editingName = '';
		formName = '';
		formDescription = '';
		formCode = '';
		showForm = false;
	}

	function handleClose() {
		resetForm();
		openCustomToolWindow.set(false);
	}

	$effect(() => {
		if ($openCustomToolWindow) {
			loadTools();
		}
	});
</script>

{#if $openCustomToolWindow}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
		<div class="max-h-[80vh] w-[560px] overflow-y-auto rounded-lg bg-white p-6 shadow-lg">
			<h2 class="mb-4 text-xl font-semibold">Custom Tools</h2>

			{#if error}
				<div class="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</div>
			{/if}

			<!-- Tool List -->
			{#if loading}
				<p class="mb-3 text-sm text-gray-500">Loading...</p>
			{:else if tools.length === 0}
				<p class="mb-3 text-sm text-gray-500">No custom tools created yet.</p>
			{:else}
				<div class="mb-4 space-y-2">
					{#each tools as tool (tool.name)}
						<div class="flex items-center justify-between rounded border border-gray-200 p-2">
							<div>
								<span class="text-sm font-medium">{tool.name}</span>
								{#if tool.description}
									<p class="text-xs text-gray-500">{tool.description}</p>
								{/if}
							</div>
							<div class="flex items-center space-x-1">
								<button
									onclick={() => startEdit(tool)}
									class="rounded bg-blue-100 px-2 py-1 text-xs text-blue-600 hover:bg-blue-200"
								>
									Edit
								</button>
								<button
									onclick={() => removeTool(tool.name)}
									class="rounded bg-red-100 px-2 py-1 text-xs text-red-600 hover:bg-red-200"
								>
									Remove
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<!-- Add/Edit Form -->
			{#if showForm}
				<div class="mb-4 rounded border border-gray-200 p-3">
					<h3 class="mb-2 text-sm font-medium">
						{editingName ? `Edit: ${editingName}` : 'Add Custom Tool'}
					</h3>
					<div class="space-y-2">
						<input
							type="text"
							placeholder="Tool name"
							bind:value={formName}
							disabled={!!editingName}
							class="w-full rounded border border-gray-300 p-1.5 text-sm focus:outline-none
								{editingName ? 'bg-gray-100' : ''}"
						/>
						<input
							type="text"
							placeholder="Description"
							bind:value={formDescription}
							class="w-full rounded border border-gray-300 p-1.5 text-sm focus:outline-none"
						/>
						<textarea
							placeholder={'@tool\ndef add(a: int, b: int):\n    """Add two numbers"""\n    return a + b'}
							bind:value={formCode}
							class="h-40 w-full resize-y rounded border border-gray-300 p-1.5 font-mono text-sm focus:outline-none"
						></textarea>
						<div class="flex space-x-2">
							<button
								onclick={saveTool}
								class="rounded bg-teal-500 px-3 py-1.5 text-sm text-white hover:bg-teal-600"
							>
								Save
							</button>
							<button
								onclick={resetForm}
								class="rounded bg-gray-200 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-300"
							>
								Cancel
							</button>
						</div>
					</div>
				</div>
			{:else}
				<button
					onclick={startAdd}
					class="mb-4 rounded bg-teal-500 px-3 py-1.5 text-sm text-white hover:bg-teal-600"
				>
					+ Add Tool
				</button>
			{/if}

			<!-- Close -->
			<div class="flex justify-end">
				<button
					onclick={handleClose}
					class="rounded bg-gray-500 px-4 py-2 font-bold text-white hover:bg-gray-700"
				>
					Close
				</button>
			</div>
		</div>
	</div>
{/if}
