<!-- routes/graph/flow/graphs-io.svelte -->
<script lang="ts" module>
	import { get } from 'svelte/store';
	import { currentNodes, serial_number, currentWorkflowName, workflowList, savedNodesJson } from './graphs.store.svelte';
	import { SvelteNodeToJsonNode, JsonNodeToSvelteNode } from './node-schema';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	/** Fetch workflow list from backend */
	export async function fetchWorkflowList(username: string): Promise<void> {
		try {
			const res = await fetch(`${SERVER_URL}/workflows/${encodeURIComponent(username)}`);
			if (res.ok) {
				const data = await res.json();
				workflowList.set(data.workflows);
			}
		} catch {
			// Backend unreachable, keep existing list
		}
	}

	/** Load a specific workflow onto the canvas */
	export async function loadWorkflow(username: string, name: string): Promise<void> {
		const res = await fetch(
			`${SERVER_URL}/workflows/${encodeURIComponent(username)}/${encodeURIComponent(name)}`
		);
		if (!res.ok) {
			alert('加载工作流失败');
			return;
		}
		const data = await res.json();
		const loaded = data.nodes.map(JsonNodeToSvelteNode);
		currentNodes.set(loaded);
		savedNodesJson.set(JSON.stringify(loaded.map(SvelteNodeToJsonNode)));
		currentWorkflowName.set(name);

		// Update serial_number
		let maxId = 0;
		for (const n of loaded) {
			const num = parseInt(n.id, 10);
			if (!isNaN(num) && num >= maxId) maxId = num;
		}
		serial_number.set(maxId + 1);
	}

	/** Save current canvas to backend */
	export async function saveWorkflow(
		username: string,
		name: string,
		overwrite: boolean
	): Promise<boolean> {
		const nodes = get(currentNodes);
		const jsonNodes = nodes.map(SvelteNodeToJsonNode);

		const params = overwrite ? '?overwrite=true' : '';
		const res = await fetch(`${SERVER_URL}/workflows/${encodeURIComponent(username)}${params}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, nodes: jsonNodes })
		});

		if (res.status === 409) {
			alert(`工作流 "${name}" 已存在，请换一个名称`);
			return false;
		}
		if (!res.ok) {
			alert('保存失败');
			return false;
		}

		currentWorkflowName.set(name);
		savedNodesJson.set(JSON.stringify(get(currentNodes).map(SvelteNodeToJsonNode)));
		await fetchWorkflowList(username);
		return true;
	}

	/** Delete a workflow from backend */
	export async function deleteWorkflow(username: string, name: string): Promise<void> {
		const res = await fetch(
			`${SERVER_URL}/workflows/${encodeURIComponent(username)}/${encodeURIComponent(name)}`,
			{ method: 'DELETE' }
		);
		if (!res.ok) {
			alert('删除失败');
			return;
		}
		await fetchWorkflowList(username);
		currentWorkflowName.set(null);
		currentNodes.set([]);
		savedNodesJson.set('[]');
		serial_number.set(1);
	}
</script>
