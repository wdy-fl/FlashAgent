<!-- routes/graph/flow/graph-algo.svelte -->
<script lang="ts" module>
	import { get } from 'svelte/store';
	import { serial_number, currentNodes } from './graphs.store.svelte';
	import type { FlowNode } from './node-schema';
	import { screenToFlow } from '../flow/flow-position.store';
	import { NodeType } from './node-schema';

	/**
	 * Add an outgoing edge from one node to another.
	 *
	 * @param source       the id of the source node
	 * @param sourceHandle one of 'next' | 'branch-{label}'
	 * @param target       the id of the target node
	 */
	export function AddEdge(source: string, sourceHandle: string, target: string): void {
		currentNodes.update((nodes: FlowNode[]) => {
			return nodes.map((node) => {
				if (node.id !== source) return node;

				// clone the node so Svelte sees a change
				const updated = { ...node, data: { ...node.data } };

				if (sourceHandle.startsWith('branch-')) {
					const label = sourceHandle.slice('branch-'.length);
					updated.data.branches = { ...updated.data.branches, [label]: target };
				} else if (sourceHandle === 'next') {
					const nexts = new Set(updated.data.nexts);
					nexts.add(target);
					updated.data.nexts = nexts;
				}

				return updated;
			});
		});
	}

	export function AddNode(
		screen_x: number,
		screen_y: number,
		nodeType: NodeType = NodeType.LLM
	): void {
		// This will never be null—at worst it's our fallback that returns {0,0}
		const ScreenToFlow = get(screenToFlow);
		const { x, y } = ScreenToFlow({ x: screen_x, y: screen_y });

		const serial = get(serial_number);

		const name = nodeType === NodeType.START ? 'Start' : 'Node' + String(serial);
		const branches: Record<string, string> =
			nodeType === NodeType.ROUTER ? { True: '', False: '' } : {};

		const newNode: FlowNode = {
			id: String(serial),
			type: 'textNode',
			data: {
				name,
				description: '',
				type: nodeType,
				nexts: new Set<string>(),
				tools: [],
				branches,
				max_iterations: 0
			},
			position: { x, y },
			width: 280,
			height: 280
		};

		if (nodeType === NodeType.HUMAN_INPUT) {
			newNode.data.input_schema = {
				input_hint: '',
				input_type: 'text',
				options: []
			};
		}

		serial_number.set(serial + 1);
		currentNodes.update((nodes) => [...nodes, newNode]);
	}

	export function RemoveNode(nodeId: string): void {
		currentNodes.update((nodes) => nodes.filter((n) => n.id !== nodeId));
	}

	export function RemoveEdge(sourceHandle: string | null, source: string, target: string): void {
		currentNodes.update((nodes) =>
			nodes.map((node) => {
				if (node.id !== source) return node;

				// clone so Svelte sees the update
				const updated: FlowNode = {
					...node,
					data: { ...node.data, nexts: new Set(node.data.nexts) }
				};

				if (sourceHandle && sourceHandle.startsWith('branch-')) {
					const label = sourceHandle.slice('branch-'.length);
					updated.data.branches = { ...updated.data.branches, [label]: '' };
				} else {
					// remove from the Set<string>
					updated.data.nexts.delete(target);
				}

				return updated;
			})
		);
	}

	export function NodeVerify(allNodes: FlowNode[]): FlowNode[] {
		// Build a map from node-id → FlowNode, so we can look up types of any referenced node
		const idToNode = new Map<string, FlowNode>();
		for (const n of allNodes) {
			idToNode.set(n.id, n);
		}

		return allNodes.map((orig) => {
			// Clone the node object (and its data) so we don't mutate the original
			const updated: FlowNode = {
				...orig,
				data: {
					...orig.data,
					nexts: new Set(orig.data.nexts),
					branches: { ...(orig.data.branches ?? {}) }
				}
			};

			const nodeType = updated.data.type;

			// 1. ROUTER nodes use branches only, clear nexts
			if (nodeType === NodeType.ROUTER) {
				updated.data.nexts = new Set();
			} else {
				// 2. Non-ROUTER nodes don't use branches
				updated.data.branches = {};
			}

			// 3. Remove pointers to START targets
			//    – for “nexts” (Set<string>):
			const cleanedNexts = new Set<string>();
			for (const nextId of updated.data.nexts) {
				const target = idToNode.get(nextId);
				if (!target) continue;
				if (target.data.type !== NodeType.START) {
					cleanedNexts.add(nextId);
				}
			}
			updated.data.nexts = cleanedNexts;

			//    – for branches:
			const cleanedBranches: Record<string, string> = {};
			for (const [label, targetId] of Object.entries(updated.data.branches)) {
				if (!targetId) {
					cleanedBranches[label] = '';
					continue;
				}
				const target = idToNode.get(targetId);
				// HUMAN_INPUT cannot be a branch target (same level as START)
				if (target && target.data.type !== NodeType.START && target.data.type !== NodeType.HUMAN_INPUT) {
					cleanedBranches[label] = targetId;
				} else {
					cleanedBranches[label] = '';
				}
			}
			updated.data.branches = cleanedBranches;

			// 4. Non-HUMAN_INPUT nodes don't use input_schema
			if (nodeType !== NodeType.HUMAN_INPUT) {
				delete updated.data.input_schema;
			}

			return updated;
		});
	}
</script>
