<!-- src/routes/graph/flow/graphs-algo.svelte -->
<script lang="ts" module>
	import { currentNodes, serial_number, currentWorkflowName, savedNodesJson } from './graphs.store.svelte';

	export function NewWorkflow() {
		currentNodes.set([]);
		serial_number.set(1);
		currentWorkflowName.set(null);
		savedNodesJson.set('[]');
	}
</script>
