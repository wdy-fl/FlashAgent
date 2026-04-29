<script>
	import { goto } from '$app/navigation';
	import { username } from './graph/menu/menu.store';

	let inputUsername = $state(
		typeof localStorage !== 'undefined' ? localStorage.getItem('flashagent_username') || '' : ''
	);

	function handleStart() {
		const name = inputUsername.trim();
		if (!name) return;
		username.set(name);
		goto('/graph');
	}
</script>

<div class="flex h-screen items-center justify-center bg-gray-950">
	<div class="text-center">
		<h1 class="mb-8 text-4xl font-bold text-white">FlashAgent</h1>
		<div class="mb-4">
			<input
				type="text"
				bind:value={inputUsername}
				placeholder="输入用户名"
				class="w-64 rounded-lg border border-gray-600 bg-gray-800 px-4 py-2.5 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
			/>
		</div>
		<button
			onclick={handleStart}
			disabled={!inputUsername.trim()}
			class="rounded-lg bg-blue-600 px-8 py-3 text-lg font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
		>
			开始
		</button>
	</div>
</div>
