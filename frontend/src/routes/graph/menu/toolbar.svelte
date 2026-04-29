<!-- routes/graph/menu/toolbar.svelte -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { handleUpload, handleDownload, handleCleanCache } from './FileTransmit.svelte';
	import { openRunWindow, openConfigWindow, openCustomToolWindow, username } from './menu.store';

	import {
		currentWorkflowName,
		workflowList,
		currentNodes,
		savedNodesJson
	} from '../flow/graphs.store.svelte';
	import {
		saveWorkflow,
		loadWorkflow,
		deleteWorkflow,
		fetchWorkflowList
	} from '../flow/graphs-io.svelte';
	import { SvelteNodeToJsonNode } from '../flow/node-schema';
	import { NewWorkflow } from '../flow/graphs-algo.svelte';
	import { get } from 'svelte/store';

	let fileInput: HTMLInputElement;

	// --- Workflow selector state ---
	let isWorkflowMenuOpen = $state(false);
	let workflowMenuRef: HTMLDivElement;

	// --- Save dialog state ---
	let showSaveDialog = $state(false);
	let saveNameInput = $state('');

	// --- Sidebar action handlers ---
	function triggerFileDialog(e: MouseEvent) {
		e.preventDefault();
		fileInput.click();
	}

	function triggerDownload(e: MouseEvent) {
		e.preventDefault();
		handleDownload();
	}

	function triggerCleanCache(e: MouseEvent) {
		e.preventDefault();
		handleCleanCache();
	}

	function triggerRun(e: MouseEvent) {
		e.preventDefault();
		openRunWindow.set(true);
	}

	function triggerConfig(e: MouseEvent) {
		e.preventDefault();
		openConfigWindow.set(true);
	}

	function triggerCustomTools(e: MouseEvent) {
		e.preventDefault();
		openCustomToolWindow.set(true);
	}

	// --- Workflow handlers ---
	function handleNew() {
		if (!hasUnsavedChanges()) {
			NewWorkflow();
			return;
		}
		const ok = confirm('当前工作流有未保存的修改，确定要新建吗？');
		if (ok) NewWorkflow();
	}

	function handleSave() {
		saveNameInput = $currentWorkflowName ?? '';
		showSaveDialog = true;
	}

	async function confirmSave() {
		const name = saveNameInput.trim();
		if (!name) return;

		const user = get(username);
		const isOverwrite = name === $currentWorkflowName;
		const success = await saveWorkflow(user, name, isOverwrite);
		if (success) {
			showSaveDialog = false;
		}
	}

	async function handleSelectWorkflow(name: string) {
		if (name === $currentWorkflowName) {
			isWorkflowMenuOpen = false;
			return;
		}
		if (hasUnsavedChanges()) {
			const ok = confirm('当前工作流有未保存的修改，确定要切换吗？');
			if (!ok) return;
		}
		const user = get(username);
		await loadWorkflow(user, name);
		isWorkflowMenuOpen = false;
	}

	async function handleDelete() {
		if (!$currentWorkflowName) return;
		const ok = confirm(`确定要删除工作流 "${$currentWorkflowName}" 吗？`);
		if (!ok) return;
		const user = get(username);
		await deleteWorkflow(user, $currentWorkflowName);
	}

	function hasUnsavedChanges(): boolean {
		// New unsaved workflow always has "unsaved changes"
		if (!$currentWorkflowName) {
			return get(currentNodes).length > 0;
		}
		// For saved workflows, compare current state against the snapshot
		const current = JSON.stringify(get(currentNodes).map(SvelteNodeToJsonNode));
		return current !== get(savedNodesJson);
	}

	// Close menus when clicking outside
	onMount(() => {
		fetchWorkflowList(get(username));

		const handleClickOutside = (event: MouseEvent) => {
			if (workflowMenuRef && !workflowMenuRef.contains(event.target as Node)) {
				isWorkflowMenuOpen = false;
			}
		};

		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
		};
	});

	// Shared button classes
	const btnClass = 'rounded px-3 py-1 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900';
	const graphBtnClass =
		'bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-1 px-2 rounded inline-flex items-center text-sm';
</script>

<nav class="flex w-full items-center border-b border-gray-200 bg-white px-4 py-1.5">
	<!-- LEFT: FlashAgent logo + action buttons -->
	<div class="flex items-center gap-1">
		<button
			class="mr-2 rounded px-3 py-1 text-sm font-bold text-blue-600 hover:bg-blue-50"
			onclick={() => goto('/')}
		>
			FlashAgent
		</button>

		<span class="h-5 border-l border-gray-300"></span>

		<button class={btnClass} onclick={triggerFileDialog}>Upload File</button>
		<input type="file" multiple bind:this={fileInput} onchange={handleUpload} class="hidden" />
		<button class={btnClass} onclick={triggerDownload}>Download File</button>
		<button class={btnClass} onclick={triggerCleanCache}>Clean Cache</button>

		<span class="mx-1.5 h-5 border-l border-gray-300"></span>

		<button class={btnClass} onclick={triggerConfig}>LLM Config</button>
		<button class={btnClass} onclick={triggerCustomTools}>Custom Tools</button>

		<span class="mx-1.5 h-5 border-l border-gray-300"></span>

		<button class={btnClass} onclick={triggerRun}>Run</button>
	</div>

	<!-- SPACER -->
	<div class="flex-1"></div>

	<!-- RIGHT: workflow controls -->
	<div class="flex items-center gap-2">
		<!-- Workflow selector -->
		<div class="relative" bind:this={workflowMenuRef}>
			<button class={graphBtnClass} onclick={() => (isWorkflowMenuOpen = !isWorkflowMenuOpen)}>
				{$currentWorkflowName ?? 'Unnamed'}
				<svg
					class="ml-1 h-4 w-4 fill-current"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
				>
					<path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
				</svg>
			</button>
			{#if isWorkflowMenuOpen}
				<div class="dropdown-menu absolute right-0 z-30 mt-1">
					{#each $workflowList as name (name)}
						<button
							class="block w-full px-4 py-2 text-left {name === $currentWorkflowName ? 'bg-blue-100' : ''}"
							onclick={() => handleSelectWorkflow(name)}
						>
							{name}
						</button>
					{/each}
					{#if $workflowList.length === 0}
						<div class="px-4 py-2 text-sm text-gray-400">No saved workflows</div>
					{/if}
				</div>
			{/if}
		</div>

		<button class={btnClass} onclick={handleSave}>Save</button>
		<button class={btnClass} onclick={handleNew}>New</button>
		<button
			class={btnClass}
			onclick={handleDelete}
			disabled={!$currentWorkflowName}
			class:cursor-not-allowed={!$currentWorkflowName}
			class:opacity-50={!$currentWorkflowName}
		>
			Delete
		</button>

		<span class="mx-1.5 h-5 border-l border-gray-300"></span>

		<span class="rounded bg-gray-800 px-3 py-1 text-sm text-gray-300">
			<svg class="mr-1 inline h-4 w-4 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
				<path d="M10 10a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 0114 0H3z" />
			</svg>
			{$username}
		</span>
	</div>
</nav>

<!-- Save dialog -->
{#if showSaveDialog}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="rounded bg-white p-6 shadow-md">
			<h3 class="mb-4 text-lg font-bold">保存工作流</h3>
			<input
				type="text"
				bind:value={saveNameInput}
				class="mb-4 w-full rounded border p-2"
				placeholder="输入工作流名称"
				/>
			<div class="flex justify-end gap-2">
				<button
					class="rounded bg-gray-300 px-4 py-2 hover:bg-gray-400"
					onclick={() => (showSaveDialog = false)}
				>
					取消
				</button>
				<button
					class="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
					onclick={confirmSave}
				>
					确认
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.dropdown-menu {
		background-color: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.1);
		color: black;
		white-space: nowrap;
	}

	.dropdown-menu button {
		color: black;
		background-color: white;
	}

	.dropdown-menu button:hover {
		background-color: #f3f4f6;
	}
</style>
