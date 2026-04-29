// vite.config.ts

/// <reference types="vitest" />

import tailwindcss from '@tailwindcss/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	optimizeDeps: {
		exclude: ['clsx', '@xyflow/system', 'classcat']
	},
	server: {
		host: '0.0.0.0',
		port: 3000,
		allowedHosts: ['localhost', '127.0.0.1']
	},
	define: {
		'import.meta.env.VITE_BACKEND_URL': JSON.stringify('http://localhost:5000'),
		'import.meta.env.VITE_DEEPSEEK_API_KEY': JSON.stringify(process.env.DEEPSEEK_API_KEY || '')
	},
	test: {
		workspace: [
			{
				extends: './vite.config.ts',
				plugins: [svelteTesting()],
				test: {
					name: 'client',
					environment: 'jsdom',
					clearMocks: true,
					include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
					exclude: ['src/lib/server/**'],
					setupFiles: ['./vitest-setup-client.ts']
				}
			},
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
