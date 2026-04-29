<!-- routes/graph/flow/tool-selector.svelte -->
<script lang="ts">
	import { get } from 'svelte/store';
	import { username } from '../menu/menu.store';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	type Props = {
		nodeId: string;
		selectedTools: string[];
		onchange: (tools: string[]) => void;
	};

	let { nodeId, selectedTools, onchange }: Props = $props();

	let showDropdown = $state(false);
	let customTools = $state<{ name: string; description: string }[]>([]);

	async function loadCustomTools() {
		try {
			const user = get(username);
			const res = await fetch(`${SERVER_URL}/custom-tools/${encodeURIComponent(user)}`);
			const data = await res.json();
			customTools = data.tools ?? [];
		} catch {
			customTools = [];
		}
	}

	function toggleDropdown() {
		if (!showDropdown) {
			loadCustomTools();
		}
		showDropdown = !showDropdown;
	}

	function isSelected(toolId: string): boolean {
		return selectedTools.includes(toolId);
	}

	function toggleTool(toolId: string) {
		if (isSelected(toolId)) {
			onchange(selectedTools.filter((t) => t !== toolId));
		} else {
			onchange([...selectedTools, toolId]);
		}
	}

	function removeTool(toolId: string) {
		onchange(selectedTools.filter((t) => t !== toolId));
	}
</script>

<div class="relative">
	<!-- Selected tools display -->
	<div
		class="flex min-h-[28px] cursor-pointer flex-wrap gap-1 rounded border border-gray-300 bg-white p-1"
		role="button"
		tabindex="0"
		onclick={toggleDropdown}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') toggleDropdown();
		}}
	>
		{#if selectedTools.length === 0}
			<span class="text-xs text-gray-400">Click to select tools...</span>
		{:else}
			{#each selectedTools as tool (tool)}
				<span
					class="inline-flex items-center rounded bg-teal-100 px-1.5 py-0.5 text-xs text-teal-700"
				>
					{tool}
					<button
						class="ml-1 text-teal-500 hover:text-teal-800"
						onclick={(e) => { e.stopPropagation(); removeTool(tool); }}
					>
						x
					</button>
				</span>
			{/each}
		{/if}
	</div>

	<!-- Dropdown -->
	{#if showDropdown}
		<div
			class="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded border border-gray-300 bg-white shadow-lg"
		>
			<!-- Custom Tools section -->
			{#if customTools.length > 0}
				<div class="border-b border-gray-100 px-2 py-1 text-xs font-semibold text-gray-500">
					Custom Tools
				</div>
				{#each customTools as tool (tool.name)}
					<button
						class="flex w-full items-center px-2 py-1 text-left text-xs hover:bg-gray-100
							{isSelected(tool.name) ? 'bg-teal-50' : ''}"
						onclick={() => toggleTool(tool.name)}
						title={tool.description}
					>
						<span class="mr-1">{isSelected(tool.name) ? '✓' : ' '}</span>
						{tool.name}
					</button>
				{/each}
			{/if}

			{#if customTools.length === 0}
				<div class="px-2 py-2 text-xs text-gray-400">
					No tools available. Create Custom Tools first.
				</div>
			{/if}
		</div>
	{/if}
</div>
