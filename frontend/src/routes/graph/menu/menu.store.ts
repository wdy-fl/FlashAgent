// routes/graph/menu/menu.store.ts

import { writable } from 'svelte/store';

export const openRunWindow = writable(false);
export const openConfigWindow = writable(false);
export const openCustomToolWindow = writable(false);

const storedUsername = typeof localStorage !== 'undefined' ? localStorage.getItem('flashagent_username') : null;
export const username = writable<string>(storedUsername || 'unknown');
username.subscribe((value) => {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem('flashagent_username', value);
	}
});

export const llmModel = writable<string>('deepseek-chat');
export const apiKey = writable<string>(import.meta.env.VITE_DEEPSEEK_API_KEY || '');
