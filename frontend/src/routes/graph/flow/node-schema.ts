// routes/graph/flow/node-schema.ts

export enum NodeType {
	START = 'START',
	LLM = 'LLM',
	ROUTER = 'ROUTER',
	INFO = 'INFO',
	HUMAN_INPUT = 'HUMAN_INPUT'
}

export interface HumanInputSchema {
	input_hint: string;
	input_type: 'text' | 'confirm' | 'select';
	options?: string[];
}

export interface JsonNodeData {
	uniq_id: string;
	name: string;
	description: string;
	nexts: string[];
	type: string;
	tools?: string[];
	branches?: Record<string, string>;
	max_iterations?: number;
	input_schema?: HumanInputSchema;
	ext: {
		pos_x?: number;
		pos_y?: number;
		width?: number;
		height?: number;
	};
}

import type { Node } from '@xyflow/svelte';

export type FlowNodeData = {
	description: string;
	name: string;
	type: NodeType;
	nexts: Set<string>;
	tools: string[];
	branches: Record<string, string>;
	max_iterations: number;
	input_schema?: HumanInputSchema;
};

export type FlowNode = Node<FlowNodeData>;

export function JsonNodeToSvelteNode(json: JsonNodeData): FlowNode {
	let nodeType: NodeType;
	if (Object.values(NodeType).includes(json.type as NodeType)) {
		nodeType = json.type as NodeType;
	} else {
		nodeType = NodeType.LLM;
	}

	const tools: string[] = json.tools ?? [];
	const branches: Record<string, string> = json.branches ?? {};

	const data: FlowNodeData = {
		name: json.name,
		description: json.description,
		type: nodeType,
		nexts: new Set(json.nexts),
		tools,
		branches,
		max_iterations: json.max_iterations ?? 0
	};

	if (nodeType === NodeType.HUMAN_INPUT) {
		data.input_schema = json.input_schema ?? {
			input_hint: '',
			input_type: 'text',
			options: []
		};
	}

	return {
		id: json.uniq_id,
		type: 'textNode',
		position: {
			x: json.ext.pos_x ?? 0,
			y: json.ext.pos_y ?? 0
		},
		width: json.ext.width ?? 200,
		height: json.ext.height ?? 200,
		data
	};
}

export function SvelteNodeToJsonNode(node: FlowNode): JsonNodeData {
	const nextsSet = node.data.nexts ?? new Set<string>();
	const result: JsonNodeData = {
		uniq_id: node.id,
		name: node.data.name,
		description: node.data.description,
		nexts: Array.from(nextsSet),
		type: NodeType[node.data.type],
		tools: node.data.tools ?? [],
		branches: node.data.branches ?? {},
		max_iterations: node.data.max_iterations ?? 0,
		ext: {
			pos_x: node.position.x,
			pos_y: node.position.y,
			width: node.width,
			height: node.height
		}
	};

	if (node.data.type === NodeType.HUMAN_INPUT && node.data.input_schema) {
		result.input_schema = node.data.input_schema;
	}

	return result;
}
