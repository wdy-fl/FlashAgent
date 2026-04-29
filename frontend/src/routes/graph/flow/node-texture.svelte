<!-- routes/graph/flow/node-teature.svelte -->
<script lang="ts">
	import type { NodeProps } from '@xyflow/svelte';
	import { useSvelteFlow, NodeResizer } from '@xyflow/svelte';
	import NodeHandles from './node-handles.svelte';
	import ToolSelector from './tool-selector.svelte';
	import { NodeType } from './node-schema';

	let { id, data, selected, width, height }: NodeProps = $props();
	const { updateNodeData } = useSvelteFlow();

	// 1. Reactive local copy of description
	let localDescription = $state(data.description);
	// 2. Reactive local copy of max_iterations
	let localMaxIterations = $state(data.max_iterations ?? 0);
	// Sync local state when data changes (e.g., workflow switch)
	$effect(() => {
		localDescription = data.description;
		localMaxIterations = data.max_iterations ?? 0;
	});
</script>

<div
	class="relative flex flex-col rounded-md border border-gray-300 bg-gray-200 p-2.5 text-center"
	style="width: {width}px; height: {height}px; overflow: visible;"
>
	<NodeResizer minWidth={260} minHeight={280} isVisible={selected} color="rgb(255,64,0)" />

	<NodeHandles node_type={data.type as NodeType} branches={data.branches as Record<string, string>} />

	<!-- TYPE DISPLAY (read-only) -->
	<div class="mt-2 flex items-center space-x-2">
		<label class="text-sm text-gray-700"> Type: </label>
		<span class="flex-1 bg-gray-100 p-1 text-sm text-gray-600">
			{data.type}
		</span>
	</div>

	<!-- NAME INPUT -->
	{#if data.type !== NodeType.START}
		<div class="mt-2 flex items-center space-x-2">
			<label for="node-name-{id}" class="text-left text-sm text-gray-700"> Name: </label>
			<input
				id="node-name-{id}"
				type="text"
				class="nodrag w-full bg-white p-1 text-sm focus:outline-none"
				value={data.name}
				oninput={(e) => {
					const val = (e.currentTarget as HTMLInputElement).value;
					updateNodeData(id, { name: val });
				}}
			/>
		</div>
	{/if}

	<!-- TOOL SELECTOR -->
	{#if data.type === NodeType.LLM}
		<div class="mt-2">
			<label class="mb-1 block text-left text-sm text-gray-700">Tools:</label>
			<ToolSelector
				nodeId={id}
				selectedTools={(data.tools as string[]) ?? []}
				onchange={(tools) => updateNodeData(id, { tools })}
			/>
		</div>
	{/if}

	<!-- ROUTER BRANCH MANAGEMENT -->
	{#if data.type === NodeType.ROUTER}
		{@const branches = (data.branches as Record<string, string>) ?? {}}
		<div class="mt-2">
			<div class="mb-1 flex items-center justify-between">
				<span class="text-left text-sm text-gray-700">Branches:</span>
				<button
					class="rounded bg-teal-400 px-1.5 py-0.5 text-xs text-white hover:bg-teal-500"
					onclick={() => {
						const newLabel = `Branch${Object.keys(branches).length + 1}`;
						updateNodeData(id, { branches: { ...branches, [newLabel]: '' } });
					}}
				>
					+ Add
				</button>
			</div>
			<div class="space-y-1">
				{#each Object.keys(branches) as label (label)}
					<div class="flex items-center space-x-1">
						<input
							type="text"
							class="nodrag w-full rounded border border-gray-300 bg-white p-1 text-xs focus:outline-none"
							value={label}
							onblur={(e) => {
								const newLabel = (e.currentTarget as HTMLInputElement).value.trim();
								if (newLabel && newLabel !== label) {
									const updated = { ...branches };
									updated[newLabel] = updated[label];
									delete updated[label];
									updateNodeData(id, { branches: updated });
								}
							}}
						/>
						<button
							class="rounded bg-red-100 px-1 py-0.5 text-xs text-red-600 hover:bg-red-200"
							onclick={() => {
								const updated = { ...branches };
								delete updated[label];
								updateNodeData(id, { branches: updated });
							}}
						>
							x
						</button>
					</div>
				{/each}
			</div>
			<!-- Max iterations -->
			<div class="mt-2 flex items-center space-x-1">
				<label for="max-iter-{id}" class="text-xs text-gray-600">Max iterations:</label>
				<input
					id="max-iter-{id}"
					type="number"
					min="0"
					class="nodrag nopan w-16 rounded border border-gray-300 bg-white p-1 text-xs focus:outline-none"
					bind:value={localMaxIterations}
					onblur={() => updateNodeData(id, { max_iterations: localMaxIterations })}
				/>
			</div>
		</div>
	{/if}

	<!-- HUMAN_INPUT CONFIG -->
	{#if data.type === NodeType.HUMAN_INPUT}
		{@const schema = (data.input_schema ?? { input_hint: '', input_type: 'text', options: [] }) as import('./node-schema').HumanInputSchema}
		<div class="mt-2 space-y-2">
			<div>
				<label for="hi-input-hint-{id}" class="text-left text-sm text-gray-700">Input Hint:</label>
				<input
					id="hi-input-hint-{id}"
					type="text"
					class="nodrag w-full rounded border border-gray-300 bg-white p-1 text-sm focus:outline-none"
					placeholder="Message shown to user..."
					value={schema.input_hint ?? ''}
					onblur={(e) => {
						updateNodeData(id, {
							input_schema: { ...schema, input_hint: (e.currentTarget as HTMLInputElement).value }
						});
					}}
				/>
			</div>
			<div>
				<label for="hi-type-{id}" class="text-left text-sm text-gray-700">Input type:</label>
				<select
					id="hi-type-{id}"
					class="nodrag w-full rounded border border-gray-300 bg-white p-1 text-sm focus:outline-none"
					value={schema.input_type ?? 'text'}
					onchange={(e) => {
						updateNodeData(id, {
							input_schema: {
								...schema,
								input_type: (e.currentTarget as HTMLSelectElement).value
							}
						});
					}}
				>
					<option value="text">Text</option>
					<option value="confirm">Confirm / Reject</option>
					<option value="select">Select from options</option>
				</select>
			</div>
			{#if (schema.input_type ?? 'text') === 'select'}
				{@const options = schema.options ?? []}
				<div>
					<div class="mb-1 flex items-center justify-between">
						<span class="text-left text-sm text-gray-700">Options:</span>
						<button
							class="rounded bg-orange-400 px-1.5 py-0.5 text-xs text-white hover:bg-orange-500"
							onclick={() => {
								updateNodeData(id, {
									input_schema: {
										...schema,
										options: [...options, `Option${options.length + 1}`]
									}
								});
							}}
						>
							+ Add
						</button>
					</div>
					<div class="space-y-1">
						{#each options as opt, idx (idx)}
							<div class="flex items-center space-x-1">
								<input
									type="text"
									class="nodrag w-full rounded border border-gray-300 bg-white p-1 text-xs focus:outline-none"
									value={opt}
									onblur={(e) => {
										const updated = [...options];
										updated[idx] = (e.currentTarget as HTMLInputElement).value;
										updateNodeData(id, {
											input_schema: { ...schema, options: updated }
										});
									}}
								/>
								<button
									class="rounded bg-red-100 px-1 py-0.5 text-xs text-red-600 hover:bg-red-200"
									onclick={() => {
										const updated = options.filter((_: string, i: number) => i !== idx);
										updateNodeData(id, {
											input_schema: { ...schema, options: updated }
										});
									}}
								>
									x
								</button>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- DESCRIPTION -->
	{#if data.type !== NodeType.START && data.type !== NodeType.HUMAN_INPUT}
		<div class="mt-2 flex min-h-0 flex-1 flex-col">
			<label for="node-description-{id}" class="mb-1 block text-left text-sm text-gray-700">
				Description:
			</label>

			<!-- 3.1 Bind locally, update only on blur -->
			<textarea
				id="node-description-{id}"
				class="nodrag h-full w-full flex-grow resize-none overflow-y-auto
               rounded border border-gray-300 bg-white p-1 text-sm
               placeholder:text-gray-400 focus:outline-none"
				placeholder="Enter description here"
				bind:value={localDescription}
				onblur={() => updateNodeData(id, { description: localDescription })}
			></textarea>
		</div>
	{/if}
</div>
