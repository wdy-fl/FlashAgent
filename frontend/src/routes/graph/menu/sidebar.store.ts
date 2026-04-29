// routes/graph/menu/sidebar.store.ts

import { writable } from 'svelte/store';
import type { NodeType } from '../flow/node-schema';

export const sidebarOpen = writable<boolean>(true);
export const placementMode = writable<NodeType | null>(null);
