<!-- routes/graph/+page.svelte -->
<script lang="ts">
	import { SvelteFlow, Controls, Background, MiniMap, type OnConnect } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import MenuToolbar from './menu/toolbar.svelte';
	import MenuConfigWindow from './menu/ConfigWindow.svelte';
	import MenuRunWindow from './menu/RunWindow.svelte';
	import MenuCustomToolWindow from './menu/CustomToolWindow.svelte';
	import MenuGraphButton from './menu/graph-button.svelte';
	import NodeSidebar from './menu/node-sidebar.svelte';

	import { currentNodes, currentEdges } from './flow/graphs.store.svelte';
	import NodeLayout from './flow/node-texture.svelte';
	import FlowAlgo from './flow/flow-algo.svelte';
	import { AddEdge, AddNode } from './flow/graph-algo.svelte';
	import { NodeType } from './flow/node-schema';
	import { placementMode } from './menu/sidebar.store';
	import { openRunWindow } from './menu/menu.store';

	const handleConnect: OnConnect = (e) => {
		if (e.sourceHandle != null) {
			AddEdge(e.source, e.sourceHandle, e.target);
		}
	};

	// custom node types
	const nodeTypes = {
		textNode: NodeLayout
	};

	function handleDragOver(event: DragEvent) {
		if (event.dataTransfer?.types.includes('application/flashagent-nodetype')) {
			event.preventDefault();
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		const typeStr = event.dataTransfer?.getData('application/flashagent-nodetype');
		if (typeStr && Object.values(NodeType).includes(typeStr as NodeType)) {
			AddNode(event.clientX, event.clientY, typeStr as NodeType);
		}
	}

	function handlePaneClick({ event }: { event: MouseEvent }) {
		if ($placementMode) {
			AddNode(event.clientX, event.clientY, $placementMode);
			$placementMode = null;
		}
	}

	$effect(() => {
		function onKeyDown(e: KeyboardEvent) {
			if (e.key === 'Escape' && $placementMode) {
				$placementMode = null;
			}
		}
		window.addEventListener('keydown', onKeyDown);
		return () => window.removeEventListener('keydown', onKeyDown);
	});
</script>

<div class="page-wrapper">
	<MenuToolbar />
	<MenuConfigWindow />
	<MenuCustomToolWindow />

	<div class="canvas-area">
		<NodeSidebar />
		<div
			class="canvas-wrapper"
			class:cursor-crosshair={$placementMode !== null}
			class:canvas-shrink={$openRunWindow}
			role="application"
			ondragover={handleDragOver}
			ondrop={handleDrop}
		>
			{#if $placementMode}
				<div class="placement-banner">
					Click to place <strong>{$placementMode}</strong> node — Press Esc to cancel
				</div>
			{/if}
			<MenuGraphButton>
				<SvelteFlow
					onconnect={handleConnect}
					onpaneclick={handlePaneClick}
					bind:nodes={$currentNodes}
					edges={$currentEdges}
					{nodeTypes}
					fitView
				>
					<Controls />
					<Background />
					<MiniMap position="top-left" />
					<FlowAlgo />
				</SvelteFlow>
			</MenuGraphButton>
		</div>
		{#if $openRunWindow}
			<MenuRunWindow />
		{/if}
	</div>
</div>

<style>
	.page-wrapper {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: calc(100vh - 20px);
	}
	.canvas-area {
		display: flex;
		flex: 1;
		min-height: 0;
	}
	.canvas-wrapper {
		flex: 1;
		position: relative;
		min-height: 0;
		transition: flex 0.3s ease;
	}
	.canvas-shrink {
		flex: 1;
	}
	.cursor-crosshair {
		cursor: crosshair;
	}
	.placement-banner {
		position: absolute;
		top: 8px;
		left: 50%;
		transform: translateX(-50%);
		background: rgba(59, 130, 246, 0.9);
		color: white;
		padding: 6px 16px;
		border-radius: 6px;
		font-size: 13px;
		z-index: 10;
		pointer-events: none;
	}
</style>
