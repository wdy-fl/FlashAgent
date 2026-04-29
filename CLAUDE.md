# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlashAgent is a visual node-based workflow builder for LLM-powered applications. Single-repo structure (formerly git submodules, now inlined).

- **Frontend**: SvelteKit 2 + Svelte 5 (runes) + @xyflow/svelte + Tailwind CSS 4 — `frontend/`
- **Backend**: FastAPI + LangGraph/LangChain (Python 3.12) — `backend/`

## Common Commands

### Frontend (cd frontend/)
```bash
npm install                      # Install dependencies
npm run dev                      # Dev server on port 3000
npm run build                    # Production build
npm run preview                  # Preview production build on port 4173
npm run check                    # svelte-kit sync + svelte-check (type checking)
npm run lint                     # Prettier (write + check) + ESLint --fix
npm run test:unit                # Vitest (two workspaces: client/jsdom + server/node)
npm run test:e2e                 # Playwright (requires build first)
```

### Backend (cd backend/)
```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 5000   # Run API server
```

## Architecture

### Data Flow
Frontend (SvelteKit, port 3000) → HTTP REST + WebSocket → Backend (FastAPI, port 5000) → DeepSeek API

1. User designs workflow as nodes on a visual canvas
2. Frontend saves workflow to backend via `POST /workflows/{username}`
3. User runs a saved workflow via WebSocket (`ws/run/{username}`) with `workflow_name`
4. Backend creates `WorkflowSession`, loads `workspace/{username}/workflows/{name}.json`, builds LangGraph `StateGraph` and executes with `MemorySaver` checkpointer
5. Output streams back via WebSocket with human-in-the-loop support (HUMAN_INPUT nodes trigger `interrupt_before`)

### Key Design: Nodes are the Single Source of Truth (SSOT)
Edges are **derived** from node data (`nexts`, `branches`), not stored independently. The `NodeVerify` function in `graph-algo.svelte` enforces graph integrity (e.g., ROUTER nodes only use branches, START nodes cannot be edge targets, START and HUMAN_INPUT cannot be branch targets, `input_schema` only on HUMAN_INPUT nodes). The `currentEdges` store is a `derived` store computed from `currentNodes` with DFS-based cycle detection.

### Node Types
`START` (entry point) | `LLM` (LLM prompt, optional native tool binding) | `ROUTER` (multi-branch routing with max_iterations, uses LangGraph `Command(goto=...)`) | `INFO` (display text) | `HUMAN_INPUT` (human-in-the-loop input, interrupts execution)

Legacy type names `TOOL` and `CONDITION` are auto-migrated in the backend (`parse_nodes_from_json`). Unrecognized types in the frontend default to `NodeType.LLM`.

### Tool System
LLM nodes can bind custom tools, unified through `ToolExecutor`:
- **Custom tools**: Plain name (e.g., `add`) — Python functions defined via CustomToolWindow, stored in `workspace/{username}/custom_tools/`, loaded via `exec()` with LangChain `@tool` decorator at runtime
- Tool binding uses native LangChain `llm.bind_tools()` for automatic tool calling
- `ToolExecutor` dispatches tool calls by name, executing the corresponding `BaseTool` instance

### Frontend Key Files
- `frontend/src/routes/graph/+page.svelte` — Main graph editor page with drag-and-drop node placement + sidebar RunWindow
- `frontend/src/routes/graph/flow/graphs.store.svelte.ts` — SSOT reactive stores (`currentNodes`, `currentEdges`, `currentWorkflowName`, `workflowList`). `currentNodes` runs `NodeVerify()` on every write.
- `frontend/src/routes/graph/flow/node-schema.ts` — `NodeType` enum, `JsonNodeData`/`FlowNodeData` interfaces, `JsonNodeToSvelteNode`/`SvelteNodeToJsonNode` converters
- `frontend/src/routes/graph/flow/graph-algo.svelte` — AddNode, RemoveNode, AddEdge, RemoveEdge, NodeVerify, NewWorkflow
- `frontend/src/routes/graph/flow/node-texture.svelte` — Node rendering with type-specific UI (ToolSelector for LLM, branch management for ROUTER, input_schema for HUMAN_INPUT)
- `frontend/src/routes/graph/flow/tool-selector.svelte` — Custom tool picker
- `frontend/src/routes/graph/menu/toolbar.svelte` — Top navigation bar with workflow management (save/load/new/delete)
- `frontend/src/routes/graph/menu/RunWindow.svelte` — Sidebar execution panel with WebSocket streaming and human-in-the-loop
- `frontend/src/routes/graph/menu/CustomToolWindow.svelte` — Custom Python tool CRUD modal
- `frontend/src/routes/graph/menu/ConfigWindow.svelte` — LLM model name + API key config
- `frontend/src/routes/graph/flow/graphs-io.svelte` — Workflow CRUD via backend API (fetchWorkflowList, loadWorkflow, saveWorkflow, deleteWorkflow)
- `frontend/src/lib/util/serialization.ts` — Type re-exports from node-schema

### Backend Key Files
- `backend/src/main.py` — FastAPI app, CORS, `/chatbot`, WebSocket `/ws/run` endpoint, includes routers
- `backend/src/WorkFlow.py` — Core workflow engine: `build_graph()` builds `StateGraph`, node execution functions (`execute_llm`, `execute_tool`, `router_switch`, `info_add`, `human_input_node`), PipelineState definition
- `backend/src/llm.py` — LLM provider factory (`get_llm()`): DeepSeek only, `clip_history()` (100 messages), `ChatBot()`
- `backend/src/NodeData.py` — `NodeData` dataclass with backward compat migration in `from_dict()`
- `backend/src/tool_executor.py` — Tool dispatch for custom tools, `get_bound_tools()` returns `BaseTool` instances for `llm.bind_tools()`
- `backend/src/custom_tool_registry.py` — Per-user custom Python tool CRUD, `register_all()` loads tools via `exec()` with `@tool` decorator
- `backend/src/custom_tool_routes.py` — Custom tools REST API (`/custom-tools/{username}/...`)
- `backend/src/FileTransmit.py` — File upload/download/clean-cache routes (preserves `workflows/` dir on clean)
- `backend/src/workflow_routes.py` — Workflow CRUD API (`/workflows/{username}/...`) with name validation
- `backend/src/workflow_session.py` — WebSocket workflow session with pause/resume/stop, MemorySaver checkpointer
- `backend/src/ServerTee.py` — Stdout tee to daily log files with subscriber streaming

### Backend API

#### Workflow Execution
| Method | Path | Description |
|--------|------|-------------|
| WS | `/ws/run/{username}` | Execute workflow (WebSocket, with human-in-the-loop) |
| POST | `/chatbot/{username}` | Direct LLM chat |

#### Workflow CRUD
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workflows/{username}` | List saved workflows |
| GET | `/workflows/{username}/{name}` | Get a specific workflow |
| POST | `/workflows/{username}` | Save workflow (use `?overwrite=true` to update) |
| DELETE | `/workflows/{username}/{name}` | Delete a workflow |

#### File Operations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload/{username}` | Upload files to workspace (multipart) |
| GET | `/download/{username}` | Download workspace as zip |
| POST | `/clean-cache/{username}` | Clear workspace files (preserves workflows/) |

#### Custom Tools
| Method | Path | Description |
|--------|------|-------------|
| GET | `/custom-tools/{username}` | List all custom tools |
| POST | `/custom-tools/{username}` | Create a new custom tool (409 if exists) |
| PUT | `/custom-tools/{username}/{tool_name}` | Update existing tool |
| DELETE | `/custom-tools/{username}/{tool_name}` | Delete a custom tool |

### Pipeline State
The LangGraph `PipelineState` TypedDict has four fields:
- `history: Annotated[list[BaseMessage], operator.add]` — List of LangChain message objects (AIMessage, HumanMessage, ToolMessage, SystemMessage), clipped to 100 messages
- `task: Annotated[str, operator.add]` — Concatenated task string
- `iteration_counts: Annotated[Dict[str, int], lambda x,y: {**x,**y}]` — Per-router iteration tracking for max_iterations enforcement
- `human_input: Annotated[str, lambda x,y: y]` — Last-wins semantics, user input from HUMAN_INPUT nodes

**Note**: `router_result` field was removed. ROUTER nodes now use LangGraph `Command(goto=...)` for routing, with decisions stored as AIMessage entries in `history`.

## Code Conventions

### Frontend
- Svelte 5 runes (`$state`, `$derived`, `$effect`) — NOT legacy `$:` reactive syntax
- Tailwind CSS 4 (imported via `@import 'tailwindcss'`)
- Prettier: tabs, single quotes, no trailing comma, 100 print width
- ESLint 9 flat config with typescript-eslint + eslint-plugin-svelte
- Module-script `.svelte` files (no template) used for logic modules: `graph-algo.svelte`, `graphs-algo.svelte`, `graphs-io.svelte`, `FileTransmit.svelte`
- Vitest for unit tests (two workspaces: client/jsdom for `.svelte.test` files, server/node for others)

### Backend
- Python 3.12, FastAPI with CORS allow-all in dev
- Multi-user isolation: per-user workspace (`workspace/{username}/`), CustomToolRegistry
- Custom tool code is loaded via `exec()` with LangChain `@tool` decorator — dynamic code execution at runtime
- Workflow execution via `WorkflowSession` using LangGraph `astream()` with `MemorySaver` checkpointer
- Native tool calling: LLM nodes with tools use `llm.bind_tools()` + tool message loop (AIMessage → ToolMessage → AIMessage)

## How to Extend

### Add a new node type
1. Add to `NodeType` enum in `frontend/src/routes/graph/flow/node-schema.ts`
2. Update `NodeVerify` in `graph-algo.svelte` for edge rules
3. Update rendering in `frontend/src/routes/graph/flow/node-texture.svelte`
4. Add execution logic in `backend/src/WorkFlow.py` (`build_graph()`)

### Add a new LLM provider
1. Update `get_llm()` in `backend/src/llm.py` with a model name detection pattern
2. Add corresponding `langchain-*` package dependency

### Add a new tool source
1. Add dispatch logic in `backend/src/tool_executor.py`
2. Update `custom_tool_registry.py` or create new registry module
3. Add frontend UI in `frontend/src/routes/graph/flow/tool-selector.svelte`

## Environment Variables
- `VITE_BACKEND_URL` — Backend URL (compile-time, set in `frontend/vite.config.ts`, default `http://localhost:5000`)
- `BACKEND_PORT` — Backend listen port (default `5000`)
- `VITE_DEEPSEEK_API_KEY` — DeepSeek API key (compile-time, set in `frontend/vite.config.ts`)

## Reference
See `architecture.md` in the repo root for a detailed AI-focused reference document covering the full architecture, API, and data models.
