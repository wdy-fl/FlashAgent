<!-- src/routes/graph/menu/RunWindow.svelte -->
<script lang="ts">
	import { openRunWindow, username, llmModel, apiKey } from './menu.store';
	import { currentWorkflowName } from '../flow/graphs.store.svelte';
	import { get } from 'svelte/store';

	const SERVER_URL = import.meta.env.VITE_BACKEND_URL;

	interface OutputItem {
		nodeId: string;
		nodeName: string;
		nodeType: string;
		hasTools: boolean;
		content: string;
	}

	// Connection & execution state
	let ws: WebSocket | null = $state(null);
	let isRunning = $state(false);
	let isWaitingInput = $state(false);
	let outputItems = $state<OutputItem[]>([]);

	// Human input state
	let inputPrompt = $state('');
	let inputType = $state<'text' | 'confirm' | 'select'>('text');
	let inputOptions = $state<string[]>([]);
	let userInput = $state('');

	// Auto-scroll
	let outputContainer: HTMLDivElement | undefined = $state();

	function scrollToBottom() {
		if (outputContainer) {
			outputContainer.scrollTop = outputContainer.scrollHeight;
		}
	}

	/** Style mapping per node type */
	function getCardStyle(item: OutputItem): string {
		if (item.nodeType === 'LLM') {
			return item.hasTools
				? 'border-purple-200 bg-purple-50'
				: 'border-blue-200 bg-blue-50';
		}
		switch (item.nodeType) {
			case 'ROUTER':
				return 'border-amber-200 bg-amber-50';
			case 'INFO':
				return 'border-gray-200 bg-gray-50';
			case 'HUMAN_INPUT':
				return 'border-green-200 bg-green-50';
			default:
				return 'border-gray-200 bg-gray-50';
		}
	}

	function getLabelStyle(item: OutputItem): string {
		if (item.nodeType === 'LLM') {
			return item.hasTools
				? 'bg-purple-200 text-purple-800'
				: 'bg-blue-200 text-blue-800';
		}
		switch (item.nodeType) {
			case 'ROUTER':
				return 'bg-amber-200 text-amber-800';
			case 'INFO':
				return 'bg-gray-200 text-gray-800';
			case 'HUMAN_INPUT':
				return 'bg-green-200 text-green-800';
			default:
				return 'bg-gray-200 text-gray-800';
		}
	}

	function getLabel(item: OutputItem): string {
		if (item.nodeType === 'LLM' && item.hasTools) return 'Tool Call';
		switch (item.nodeType) {
			case 'LLM': return 'LLM';
			case 'ROUTER': return 'Router';
			case 'INFO': return 'Info';
			case 'HUMAN_INPUT': return 'You';
			default: return item.nodeType;
		}
	}

	/** Format content: try JSON pretty-print, fall back to raw text */
	function formatContent(content: string): string {
		try {
			const parsed = JSON.parse(content);
			return JSON.stringify(parsed, null, 2);
		} catch {
			return content;
		}
	}

	/** Establish WebSocket connection */
	function connectWs(): WebSocket {
		const wsUrl = SERVER_URL.replace(/^http/, 'ws');
		const user = get(username);
		const socket = new WebSocket(`${wsUrl}/ws/run/${encodeURIComponent(user)}`);

		socket.onmessage = (event) => {
			const msg = JSON.parse(event.data);
			switch (msg.type) {
				case 'output':
					if (msg.content) {
						outputItems.push({
							nodeId: msg.node_id,
							nodeName: msg.node_name,
							nodeType: msg.node_type,
							hasTools: msg.has_tools,
							content: msg.content
						});
						setTimeout(scrollToBottom, 0);
					}
					break;
				case 'input_request':
					isWaitingInput = true;
					inputPrompt = msg.input_hint;
					inputType = msg.input_type;
					inputOptions = msg.options || [];
					if (msg.input_type === 'select' && inputOptions.length > 0) {
						userInput = inputOptions[0];
					}
					break;
				case 'completed':
					isRunning = false;
					break;
				case 'stopped':
					isRunning = false;
					isWaitingInput = false;
					break;
				case 'status':
					isRunning = msg.is_running;
					isWaitingInput = msg.is_waiting;
					if (msg.output_history) {
						outputItems = msg.output_history
							.filter((e: { type: string }) => e.type === 'output')
							.map((e: { node_id: string; node_name: string; node_type: string; has_tools: boolean; content: string }) => ({
								nodeId: e.node_id,
								nodeName: e.node_name,
								nodeType: e.node_type,
								hasTools: e.has_tools,
								content: e.content
							}));
						setTimeout(scrollToBottom, 0);
					}
					// Restore input panel state when waiting for input
					if (msg.is_waiting) {
						inputPrompt = msg.input_hint || '';
						inputType = msg.input_type || 'text';
						inputOptions = msg.input_options || [];
						if (msg.input_type === 'select' && inputOptions.length > 0) {
							userInput = inputOptions[0];
						}
					}
					break;
				case 'error':
					outputItems.push({
						nodeId: '',
						nodeName: 'Error',
						nodeType: 'ERROR',
						hasTools: false,
						content: msg.message
					});
					isRunning = false;
					setTimeout(scrollToBottom, 0);
					break;
			}
		};

		socket.onclose = () => {
			ws = null;
		};
		return socket;
	}

	/** Run: start execution via WebSocket with workflow_name */
	async function handleRun() {
		const workflowName = get(currentWorkflowName);
		if (!workflowName) {
			alert('请先保存工作流再运行');
			return;
		}

		isRunning = true;
		outputItems = [];

		ws = connectWs();
		ws.onopen = () => {
			ws!.send(
				JSON.stringify({
					type: 'start',
					llm_model: get(llmModel),
					api_key: get(apiKey),
					workflow_name: workflowName
				})
			);
		};
	}

	/** Stop: stop execution but keep window open */
	function handleStop() {
		if (ws && ws.readyState === WebSocket.OPEN) {
			ws.send(JSON.stringify({ type: 'stop' }));
		}
	}

	/** Close: close window but don't stop execution */
	function handleClose() {
		if (ws) {
			ws.close();
			ws = null;
		}
		openRunWindow.set(false);
	}

	/** Submit user input */
	function submitInput() {
		if (!ws) return;
		ws.send(JSON.stringify({ type: 'input', input: userInput }));
		userInput = '';
		isWaitingInput = false;
	}

	/** Auto-reconnect when window opens if a session might be running */
	$effect(() => {
		if ($openRunWindow && !ws) {
			const socket = connectWs();
			socket.onopen = () => {
				socket.send(JSON.stringify({ type: 'status' }));
			};
			ws = socket;
		}
	});
</script>

<div class="run-sidebar">
	<!-- Header -->
	<div class="flex items-center justify-between border-b border-gray-200 px-4 py-3">
		<h2 class="text-base font-bold">Workflow: {$currentWorkflowName}</h2>
		<button
			onclick={handleClose}
			disabled={isRunning}
			class="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 {isRunning ? 'cursor-not-allowed opacity-50' : ''}"
		>
			<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- Button bar: Run / Stop -->
	<div class="flex gap-2 border-b border-gray-200 px-4 py-2">
		<button
			onclick={handleRun}
			disabled={isRunning || !$currentWorkflowName}
			class={`flex-1 rounded px-4 py-2 text-sm font-bold text-white ${
				isRunning || !$currentWorkflowName
					? 'cursor-not-allowed bg-gray-400'
					: 'bg-blue-500 hover:bg-blue-700'
			}`}
		>
			Run
		</button>
		<button
			onclick={handleStop}
			disabled={!isRunning}
			class={`flex-1 rounded px-4 py-2 text-sm font-bold text-white ${
				!isRunning
					? 'cursor-not-allowed bg-gray-400'
					: 'bg-red-500 hover:bg-red-700'
			}`}
		>
			Stop
		</button>
	</div>

	{#if !$currentWorkflowName}
		<p class="px-4 py-2 text-sm text-red-500">请先保存工作流再运行</p>
	{/if}

	<!-- Output area: structured cards -->
	<div bind:this={outputContainer} class="flex-1 overflow-y-auto space-y-2 p-3">
		{#each outputItems as item}
			<div class="rounded border-l-4 {getCardStyle(item)} p-3">
				<div class="mb-1 flex items-center gap-2">
					<span class="rounded px-2 py-0.5 text-xs font-semibold {getLabelStyle(item)}">
						{getLabel(item)}
					</span>
					<span class="text-sm font-medium text-gray-700">{item.nodeName}</span>
				</div>
				<pre class="whitespace-pre-wrap text-sm text-gray-800">{formatContent(item.content)}</pre>
			</div>
		{/each}

		{#if !isRunning && outputItems.length > 0}
			<div class="text-center text-sm text-gray-400 py-2">
				[Workflow completed]
			</div>
		{/if}
	</div>

	<!-- Input panel: shown when workflow pauses for user input -->
	{#if isWaitingInput}
		<div class="border-t-2 border-blue-400 bg-blue-50 p-4">
			<p class="mb-2 font-semibold text-blue-800">{inputPrompt}</p>

			{#if inputType === 'text'}
				<input
					type="text"
					bind:value={userInput}
					class="w-full rounded border p-2"
					placeholder="Please enter..."
				/>
			{:else if inputType === 'confirm'}
				<div class="flex space-x-2">
					<button
						onclick={() => {
							userInput = 'yes';
							submitInput();
						}}
						class="rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600"
					>
						Confirm
					</button>
					<button
						onclick={() => {
							userInput = 'no';
							submitInput();
						}}
						class="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600"
					>
						Reject
					</button>
				</div>
			{:else if inputType === 'select'}
				<select bind:value={userInput} class="w-full rounded border p-2">
					{#each inputOptions as opt}
						<option value={opt}>{opt}</option>
					{/each}
				</select>
			{/if}

			{#if inputType !== 'confirm'}
				<button
					onclick={submitInput}
					disabled={!userInput.trim()}
					class={`mt-2 rounded px-4 py-2 text-white ${
						!userInput.trim()
							? 'cursor-not-allowed bg-gray-400'
							: 'bg-blue-500 hover:bg-blue-600'
					}`}
				>
					Submit
				</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.run-sidebar {
		display: flex;
		flex-direction: column;
		width: 420px;
		min-width: 320px;
		height: 100%;
		background: white;
		border-left: 1px solid #e5e7eb;
		overflow: hidden;
	}
</style>
