// routes/graph/flow/graphs.store.svelte.ts
import { writable, derived } from 'svelte/store';
import type { Edge } from '@xyflow/svelte';
import type { FlowNode } from './node-schema';
import { NodeVerify } from './graph-algo.svelte';

export const serial_number = writable<number>(1);

/** Current workflow name, null means unsaved new workflow */
export const currentWorkflowName = writable<string | null>(null);

/** Saved workflow name list (metadata only) */
export const workflowList = writable<string[]>([]);

export const savedNodesJson = writable<string>('[]');

export const currentNodes = (() => {
	const inner = writable<FlowNode[]>([]);

	return {
		subscribe: inner.subscribe,
		set(newNodes: FlowNode[]) {
			inner.set(NodeVerify(newNodes));
		},
		update(fn: (nodes: FlowNode[]) => FlowNode[]) {
			inner.update((n) => NodeVerify(fn(n)));
		}
	};
})();

// derive edges from nodes
export const currentEdges = derived(currentNodes, ($nodes): Edge[] => {
	const edges: Edge[] = [];
	const nodeIds = new Set($nodes.map((n) => n.id));

	// Build adjacency for cycle detection
	const adj = new Map<string, string[]>();
	for (const node of $nodes) {
		const targets: string[] = [];
		const nextsSet = node.data.nexts ?? new Set<string>();
		for (const nextId of nextsSet) targets.push(nextId);
		const branches = (node.data.branches as Record<string, string>) ?? {};
		for (const targetId of Object.values(branches)) {
			if (targetId) targets.push(targetId);
		}
		adj.set(node.id, targets);
	}

	// Simple cycle detection: find back-edges via DFS
	const backEdges = new Set<string>();
	const visited = new Set<string>();
	const inStack = new Set<string>();

	function dfs(nodeId: string) {
		visited.add(nodeId);
		inStack.add(nodeId);
		for (const target of adj.get(nodeId) ?? []) {
			if (!nodeIds.has(target)) continue;
			if (inStack.has(target)) {
				backEdges.add(`${nodeId}→${target}`);
			} else if (!visited.has(target)) {
				dfs(target);
			}
		}
		inStack.delete(nodeId);
	}

	for (const node of $nodes) {
		if (!visited.has(node.id)) dfs(node.id);
	}

	for (const node of $nodes) {
		const nextsSet = node.data.nexts ?? new Set<string>();
		for (const nextId of nextsSet) {
			const isLoop = backEdges.has(`${node.id}→${nextId}`);
			edges.push({
				id: `xy-edge-${node.id}→${nextId}`,
				source: node.id,
				target: nextId,
				label: isLoop ? 'loop' : undefined,
				style: isLoop ? 'stroke-width: 4px; stroke-dasharray: 5 5;' : 'stroke-width: 4px;'
			});
		}

		const branches = (node.data.branches as Record<string, string>) ?? {};
		for (const [label, targetId] of Object.entries(branches)) {
			if (!targetId) continue;
			const isLoop = backEdges.has(`${node.id}→${targetId}`);
			edges.push({
				id: `xy-edge-${node.id}-branch-${label}→${targetId}`,
				source: node.id,
				sourceHandle: `branch-${label}`,
				target: targetId,
				label: isLoop ? `${label} (loop)` : label,
				style: isLoop
					? 'stroke-width: 4px; stroke: teal; stroke-dasharray: 5 5;'
					: 'stroke-width: 4px; stroke: teal;'
			});
		}
	}

	return edges;
});
