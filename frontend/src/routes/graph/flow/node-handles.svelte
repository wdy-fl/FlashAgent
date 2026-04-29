<!-- routes/graph/flow/node-handles.svelte -->
<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { NodeType } from './node-schema';

	let { node_type = $bindable(), branches = {} } = $props<{
		node_type: NodeType;
		branches?: Record<string, string>;
	}>();
	let is_start = $derived(node_type === NodeType.START);
	let is_router = $derived(node_type === NodeType.ROUTER);

	let branchKeys = $derived(Object.keys(branches ?? {}));
</script>

<!-- Target handle on left - show for all except START -->
<Handle
	id="in"
	type="target"
	isConnectable={!is_start}
	position={Position.Left}
	style="visibility: {!is_start ? 'visible' : 'hidden'};
		left: -8px; top: calc(50% - 8px); width: 16px; height: 16px;
		background: #3b82f6; border: 2px solid #fff; border-radius: 50%;
		box-shadow: 0 0 0 2px #3b82f6; z-index: 10; cursor: crosshair;"
/>

<!-- Source handle on right - show for all except ROUTER -->
<Handle
	id="next"
	type="source"
	isConnectable={!is_router}
	position={Position.Right}
	style="visibility: {!is_router ? 'visible' : 'hidden'};
		right: -8px; top: calc(50% - 8px); width: 16px; height: 16px;
		background: #f97316; border: 2px solid #fff; border-radius: 50%;
		box-shadow: 0 0 0 2px #f97316; z-index: 10; cursor: crosshair;"
/>

<!-- Dynamic branch handles for ROUTER -->
{#if is_router}
	{#each branchKeys as label, i (label)}
		{@const pct = branchKeys.length === 1 ? 50 : 15 + (70 * i) / (branchKeys.length - 1)}
		<Handle
			id="branch-{label}"
			type="source"
			isConnectable={true}
			position={Position.Right}
			style="right: -8px; top: {pct}%; width: 16px; height: 16px;
				background: #14b8a6; border: 2px solid #fff; border-radius: 50%;
				box-shadow: 0 0 0 2px #14b8a6; z-index: 10; cursor: crosshair;"
		/>
	{/each}
{/if}
