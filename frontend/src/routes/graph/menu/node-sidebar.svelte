<!-- routes/graph/menu/node-sidebar.svelte -->
<script lang="ts">
	import { NodeType } from '../flow/node-schema';
	import { sidebarOpen, placementMode } from './sidebar.store';

	const nodeTypeConfig = [
		{
			type: NodeType.START,
			label: 'Start',
			icon: '\u25B6',
			color: 'bg-green-100 text-green-700 border-green-300',
			activeColor: 'bg-green-200',
			description: 'Entry point'
		},
		{
			type: NodeType.LLM,
			label: 'LLM',
			icon: '\u2726',
			color: 'bg-blue-100 text-blue-700 border-blue-300',
			activeColor: 'bg-blue-200',
			description: 'LLM prompt'
		},
		{
			type: NodeType.ROUTER,
			label: 'Router',
			icon: '\u2442',
			color: 'bg-teal-100 text-teal-700 border-teal-300',
			activeColor: 'bg-teal-200',
			description: 'Multi-branch'
		},
		{
			type: NodeType.INFO,
			label: 'Info',
			icon: '\u2139',
			color: 'bg-purple-100 text-purple-700 border-purple-300',
			activeColor: 'bg-purple-200',
			description: 'Display text'
		},
		{
			type: NodeType.HUMAN_INPUT,
			label: 'Human',
			icon: '\u270B',
			color: 'bg-orange-100 text-orange-700 border-orange-300',
			activeColor: 'bg-orange-200',
			description: 'User input'
		}
	];

	function handleDragStart(event: DragEvent, nodeType: NodeType) {
		if (!event.dataTransfer) return;
		event.dataTransfer.setData('application/flashagent-nodetype', nodeType);
		event.dataTransfer.effectAllowed = 'move';
	}

	function handleClick(nodeType: NodeType) {
		placementMode.update((current) => (current === nodeType ? null : nodeType));
	}

	function toggleSidebar() {
		sidebarOpen.update((v) => !v);
	}
</script>

<div
	class="sidebar"
	class:sidebar-expanded={$sidebarOpen}
	class:sidebar-collapsed={!$sidebarOpen}
>
	<button class="toggle-btn" onclick={toggleSidebar} title={$sidebarOpen ? 'Collapse' : 'Expand'}>
		{$sidebarOpen ? '\u276E' : '\u276F'}
	</button>

	<div class="node-list">
		{#each nodeTypeConfig as config (config.type)}
			<button
				class="node-item {config.color}"
				class:ring-2={$placementMode === config.type}
				class:ring-blue-500={$placementMode === config.type}
				draggable="true"
				ondragstart={(e) => handleDragStart(e, config.type)}
				onclick={() => handleClick(config.type)}
				title={config.label}
			>
				<span class="node-icon">{config.icon}</span>
				{#if $sidebarOpen}
					<div class="node-info">
						<span class="node-label">{config.label}</span>
						<span class="node-desc">{config.description}</span>
					</div>
				{/if}
			</button>
		{/each}
	</div>
</div>

<style>
	.sidebar {
		display: flex;
		flex-direction: column;
		background: #f8f9fa;
		border-right: 1px solid #e0e0e0;
		transition: width 200ms ease;
		overflow: hidden;
		flex-shrink: 0;
		z-index: 5;
	}
	.sidebar-expanded {
		width: 200px;
	}
	.sidebar-collapsed {
		width: 48px;
	}
	.toggle-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 36px;
		border: none;
		background: none;
		cursor: pointer;
		color: #666;
		font-size: 14px;
		border-bottom: 1px solid #e0e0e0;
	}
	.toggle-btn:hover {
		background: #e9ecef;
	}
	.node-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 6px;
		overflow-y: auto;
	}
	.node-item {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px;
		border: 1px solid;
		border-radius: 6px;
		cursor: grab;
		transition: background 150ms;
		text-align: left;
		font-size: 13px;
	}
	.node-item:hover {
		filter: brightness(0.95);
	}
	.node-item:active {
		cursor: grabbing;
	}
	.node-icon {
		font-size: 18px;
		flex-shrink: 0;
		width: 24px;
		text-align: center;
	}
	.node-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.node-label {
		font-weight: 600;
		line-height: 1.2;
	}
	.node-desc {
		font-size: 11px;
		opacity: 0.7;
		line-height: 1.2;
	}
</style>
