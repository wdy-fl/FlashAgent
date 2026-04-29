// Backward-compat & round-trip tests for node-schema converters
import { describe, test, expect } from 'vitest';
import {
	NodeType,
	JsonNodeToSvelteNode,
	SvelteNodeToJsonNode,
	type JsonNodeData
} from './node-schema';

// Helper: minimal JsonNodeData
function makeJson(overrides: Partial<JsonNodeData> = {}): JsonNodeData {
	return {
		uniq_id: '1',
		name: 'TestNode',
		description: 'desc',
		nexts: [],
		type: 'LLM',
		ext: { pos_x: 10, pos_y: 20, width: 200, height: 200 },
		...overrides
	};
}

describe('JsonNodeToSvelteNode', () => {
	test('unknown type defaults to LLM', () => {
		const node = JsonNodeToSvelteNode(makeJson({ type: 'UNKNOWN_TYPE' }));
		expect(node.data.type).toBe(NodeType.LLM);
	});

	test('tools array preserved', () => {
		const node = JsonNodeToSvelteNode(makeJson({ tools: ['a', 'b'] }));
		expect(node.data.tools).toEqual(['a', 'b']);
	});

	test('empty tools defaults to empty array', () => {
		const node = JsonNodeToSvelteNode(makeJson({}));
		expect(node.data.tools).toEqual([]);
	});

	test('branches preserved', () => {
		const node = JsonNodeToSvelteNode(
			makeJson({
				type: 'ROUTER',
				branches: { yes: '2', no: '3', maybe: '4' }
			})
		);
		expect(node.data.branches).toEqual({ yes: '2', no: '3', maybe: '4' });
	});

	test('nexts converted to Set', () => {
		const node = JsonNodeToSvelteNode(makeJson({ nexts: ['2', '3'] }));
		expect(node.data.nexts).toBeInstanceOf(Set);
		expect([...node.data.nexts]).toEqual(['2', '3']);
	});

	test('enable_skills field ignored for backward compat', () => {
		// Old JSON with enable_skills should still parse without error
		const node = JsonNodeToSvelteNode(makeJson({ enable_skills: true } as any));
		expect(node.data.tools).toEqual([]);
	});

	test('max_iterations defaults to 0', () => {
		const node = JsonNodeToSvelteNode(makeJson({}));
		expect(node.data.max_iterations).toBe(0);
	});

	test('position and dimensions from ext', () => {
		const node = JsonNodeToSvelteNode(
			makeJson({ ext: { pos_x: 100, pos_y: 200, width: 300, height: 400 } })
		);
		expect(node.position).toEqual({ x: 100, y: 200 });
		expect(node.width).toBe(300);
		expect(node.height).toBe(400);
	});
});

describe('SvelteNodeToJsonNode', () => {
	test('outputs new format fields correctly', () => {
		const flowNode = JsonNodeToSvelteNode(
			makeJson({
				type: 'LLM',
				tools: ['t1', 't2'],
				nexts: ['2', '3']
			})
		);
		const json = SvelteNodeToJsonNode(flowNode);
		expect(json.type).toBe('LLM');
		expect(json.tools).toEqual(['t1', 't2']);
		expect(json.nexts).toEqual(['2', '3']);
		expect(json.branches).toEqual({});
		expect(json.max_iterations).toBe(0);
	});

	test('ROUTER branches round-trip', () => {
		const flowNode = JsonNodeToSvelteNode(
			makeJson({
				type: 'ROUTER',
				branches: { yes: '2', no: '3' },
				max_iterations: 5
			})
		);
		const json = SvelteNodeToJsonNode(flowNode);
		expect(json.type).toBe('ROUTER');
		expect(json.branches).toEqual({ yes: '2', no: '3' });
		expect(json.max_iterations).toBe(5);
	});
});

describe('Round-trip: JsonNodeData → FlowNode → JsonNodeData', () => {
	test('new format round-trips cleanly', () => {
		const original = makeJson({
			type: 'LLM',
			tools: ['a'],
			nexts: ['2'],
			ext: { pos_x: 50, pos_y: 60, width: 280, height: 280 }
		});
		const roundTripped = SvelteNodeToJsonNode(JsonNodeToSvelteNode(original));
		expect(roundTripped.uniq_id).toBe(original.uniq_id);
		expect(roundTripped.name).toBe(original.name);
		expect(roundTripped.description).toBe(original.description);
		expect(roundTripped.type).toBe('LLM');
		expect(roundTripped.tools).toEqual(['a']);
		expect(roundTripped.nexts).toEqual(['2']);
		expect(roundTripped.ext).toEqual(original.ext);
	});
});

describe('input_schema scope', () => {
	test('HUMAN_INPUT node preserves input_schema in round-trip', () => {
		const flowNode = JsonNodeToSvelteNode(
			makeJson({
				type: 'HUMAN_INPUT',
				input_schema: {
					input_hint: '请输入数字',
					input_type: 'text',
					options: []
				}
			})
		);
		expect(flowNode.data.input_schema).toBeDefined();
		expect(flowNode.data.input_schema?.input_hint).toBe('请输入数字');

		const json = SvelteNodeToJsonNode(flowNode);
		expect(json.input_schema).toBeDefined();
		expect((json.input_schema as any).input_hint).toBe('请输入数字');
	});

	test('non-HUMAN_INPUT node does not have input_schema after deserialization', () => {
		const node = JsonNodeToSvelteNode(makeJson({ type: 'LLM' }));
		expect(node.data.input_schema).toBeUndefined();
	});

	test('non-HUMAN_INPUT node discards input_schema from old JSON', () => {
		const node = JsonNodeToSvelteNode(
			makeJson({
				type: 'LLM',
				input_schema: { input_hint: '遗留数据', input_type: 'text', options: [] }
			})
		);
		expect(node.data.input_schema).toBeUndefined();
	});

	test('non-HUMAN_INPUT node does not serialize input_schema', () => {
		const flowNode = JsonNodeToSvelteNode(makeJson({ type: 'LLM' }));
		const json = SvelteNodeToJsonNode(flowNode);
		expect(json.input_schema).toBeUndefined();
	});
});
