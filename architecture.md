# FlashAgent - AI Quick Reference

> A visual node-based workflow builder for LLM-powered applications using LangGraph.

## Project Overview

**Purpose**: GUI for creating and executing LLM workflows visually with human-in-the-loop support
**Version**: 2.2.3
**License**: MIT
**Architecture**: Single-repo (formerly git submodules, now inlined)

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  Frontend (SvelteKit + @xyflow/svelte)        Port 3000         │
│  - Visual node editor for workflow design                       │
│  - SSOT reactive stores (currentNodes → derived currentEdges)   │
│  - Sidebar execution panel with HITL input                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP REST + WebSocket
┌─────────────────────────▼───────────────────────────────────────┐
│  Backend (FastAPI + LangGraph)                Port 5000         │
│  - Executes workflows via LangGraph StateGraph                  │
│  - Multi-user workspaces: workspace/{username}/                 │
│  - WebSocket streaming with pause/resume for HITL               │
│  - MemorySaver checkpointer for interrupt/replay                │
│  - Native LangChain tool calling with @tool decorator           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  LLM Provider                                                   │
│  - DeepSeek API (OpenAI-compatible endpoint)                    │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
FlashAgent/
├── backend/                     # FastAPI + LangGraph
│   └── src/
│       ├── main.py              # FastAPI server, WebSocket /ws/run endpoint
│       ├── WorkFlow.py          # LangGraph StateGraph builder, node execution
│       ├── llm.py               # LLM provider factory (DeepSeek only)
│       ├── NodeData.py          # NodeData dataclass with backward compat
│       ├── tool_executor.py     # Unified tool dispatch (custom tools)
│       ├── custom_tool_registry.py  # Per-user custom Python tool CRUD (@tool decorator)
│       ├── custom_tool_routes.py    # Custom tools REST API
│       ├── FileTransmit.py      # File upload/download/clean-cache routes
│       ├── workflow_routes.py   # Workflow CRUD API
│       ├── workflow_session.py  # WebSocket workflow session (pause/resume/stop)
│       ├── ServerTee.py         # Stdout tee to log files with subscriber streaming
│       └── util.py              # Logger utility
│
├── frontend/                    # SvelteKit 2 + Svelte 5
│   └── src/
│       ├── routes/
│       │   ├── graph/           # Main workflow editor
│       │   │   ├── +page.svelte # Graph editor page
│       │   │   ├── flow/        # Graph visualization & state
│       │   │   │   ├── graphs.store.svelte.ts  # SSOT reactive stores
│       │   │   │   ├── node-schema.ts          # NodeType enum, converters
│       │   │   │   ├── graph-algo.svelte       # AddNode/RemoveNode/AddEdge/NodeVerify
│       │   │   │   ├── node-texture.svelte     # Node rendering (type-specific UI)
│       │   │   │   ├── tool-selector.svelte    # Custom tool picker
│       │   │   │   ├── graphs-io.svelte        # Workflow CRUD via backend API
│       │   │   │   ├── graphs-algo.svelte      # NewWorkflow helper
│       │   │   │   ├── node-handles.svelte     # xyflow Handle rendering
│       │   │   │   └── flow-algo.svelte        # screenToFlow mount helper
│       │   │   └── menu/        # UI panels
│       │   │       ├── toolbar.svelte       # Top nav: workflow CRUD, tool windows
│       │   │       ├── RunWindow.svelte     # Sidebar execution panel + HITL
│       │   │       ├── CustomToolWindow.svelte  # Custom Python tool CRUD
│       │   │       ├── ConfigWindow.svelte  # LLM model/key config
│       │   │       ├── node-sidebar.svelte  # Node type palette (drag/click)
│       │   │       ├── FileTransmit.svelte  # Upload/download/clean helpers
│       │   │       ├── graph-button.svelte  # Right-click context menu
│       │   │       ├── menu.store.ts        # UI state stores (username, llmModel, apiKey)
│       │   │       └── sidebar.store.ts     # placementMode store
│       │   └── doc/             # Documentation viewer (iframe)
│       └── lib/util/serialization.ts  # Type re-exports from node-schema
│
└── docs/                        # Design documents
    ├── competitive-analysis.md
    ├── requirements-agent-capabilities.md
    ├── langgraph-application.md
    ├── langgraph-gap-analysis.md
    └── hitl/                    # Modular HITL design docs
        ├── README.md
        ├── 01-overview.md
        ├── 02-frontend-node.md
        ├── 03-backend-execution.md
        ├── 04-websocket-communication.md
        ├── 05-frontend-runwindow.md
        ├── 06-workflow-crud-compat.md
        └── 07-implementation-plan.md
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend Framework | SvelteKit 2.16 + Svelte 5 (runes) |
| Graph Visualization | @xyflow/svelte 1.0.2 |
| Styling | Tailwind CSS 4 |
| Build Tool | Vite 6.2 |
| Backend Framework | FastAPI (Python 3.12) |
| Workflow Engine | LangGraph + LangChain |
| LLM Provider | DeepSeek API (OpenAI-compatible) |
| Tool System | LangChain `@tool` decorator + `bind_tools()` |

## Node Types

```typescript
enum NodeType {
  START        // Entry point, initializes state
  LLM          // LLM prompt execution, optional tool binding via native tool calling
  ROUTER       // Multi-branch routing via LangGraph Command(goto=...)
  INFO         // Display-only information node
  HUMAN_INPUT  // Human-in-the-loop input (interrupts execution)
}

interface HumanInputSchema {
  input_hint: string;              // Prompt text shown to user
  input_type: 'text' | 'confirm' | 'select';
  options?: string[];              // For 'select' type
}

interface JsonNodeData {
  uniq_id: string;
  name: string;
  description: string;             // Prompt template or info text
  nexts: string[];                 // Next node IDs (for LLM/INFO/HUMAN_INPUT)
  type: string;                    // NodeType value
  tools?: string[];                // Tool IDs bound to LLM node
  branches?: Record<string, string>; // ROUTER branch label -> target node ID
  max_iterations?: number;         // ROUTER max loop count (0 = unlimited)
  input_schema?: HumanInputSchema; // HUMAN_INPUT only
  ext: { pos_x?, pos_y?, width?, height? };
}
```

Legacy type names `TOOL` and `CONDITION` are auto-migrated to `LLM` and `ROUTER` in the backend (`parse_nodes_from_json`). Unrecognized types in the frontend default to `NodeType.LLM`.

## Tool System

LLM nodes can bind custom tools, unified through `ToolExecutor`:

- **Custom tools**: Plain name (e.g., `add`) — Python functions defined via CustomToolWindow, stored in `workspace/{username}/custom_tools/`, loaded via `exec()` with LangChain `@tool` decorator at runtime
- Tool binding uses native LangChain `llm.bind_tools()` for automatic tool calling
- `ToolExecutor` dispatches tool calls by name, executing the corresponding `BaseTool` instance

## Backend API

### Workflow Execution

| Method | Path | Description |
|--------|------|-------------|
| WS | `/ws/run/{username}` | Execute workflow (WebSocket, with human-in-the-loop) |

**WebSocket protocol:**

| Message Type | Direction | Fields | Description |
|-------------|-----------|--------|-------------|
| `start` | Client → Server | `workflow_name`, `llm_model?`, `api_key?` | Start workflow execution |
| `input` | Client → Server | `content` | Resume from HUMAN_INPUT interrupt |
| `stop` | Client → Server | — | Cancel running workflow |
| `status` | Client → Server | — | Query current session state |
| `output` | Server → Client | `data` | Execution output text |
| `input_request` | Server → Client | `input_hint`, `input_type`, `options?` | Waiting for human input |
| `completed` | Server → Client | — | Workflow finished successfully |
| `stopped` | Server → Client | — | Workflow cancelled by user |
| `error` | Server → Client | `data` | Error message |

### Workflow CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/workflows/{username}` | List saved workflow names |
| GET | `/workflows/{username}/{name}` | Get workflow JSON |
| POST | `/workflows/{username}` | Save workflow (`?overwrite=true` to update) |
| DELETE | `/workflows/{username}/{name}` | Delete a workflow |

### File Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload/{username}` | Upload files to workspace (multipart) |
| GET | `/download/{username}` | Download workspace as ZIP |
| POST | `/clean-cache/{username}` | Clear workspace files (preserves `workflows/`) |

### Custom Tools

| Method | Path | Description |
|--------|------|-------------|
| GET | `/custom-tools/{username}` | List all custom tools |
| POST | `/custom-tools/{username}` | Create a new custom tool (409 if exists) |
| PUT | `/custom-tools/{username}/{tool_name}` | Update existing tool |
| DELETE | `/custom-tools/{username}/{tool_name}` | Delete a custom tool |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chatbot/{username}` | Direct LLM chat (`{input_string, llm_model, api_key}`) |

## Pipeline State

The LangGraph `PipelineState` TypedDict has four fields:

| Field | Type | Reducer | Description |
|-------|------|---------|-------------|
| `history` | `Annotated[list[BaseMessage], operator.add]` | Append | Running conversation as LangChain message objects (AIMessage, HumanMessage, ToolMessage, SystemMessage), clipped to 100 messages |
| `task` | `Annotated[str, operator.add]` | Append (concat) | Task string |
| `iteration_counts` | `Annotated[Dict[str,int], lambda x,y: {**x,**y}]` | Merge dicts | Per-router iteration tracking |
| `human_input` | `Annotated[str, lambda x,y: y]` | Last-wins | User input from HUMAN_INPUT nodes |

**Key changes from earlier versions:**
- `history` changed from `str` to `list[BaseMessage]` — enables native LangChain tool calling with proper message sequencing (AIMessage with tool_calls → ToolMessage → AIMessage)
- `router_result` field removed — ROUTER nodes now use LangGraph `Command(goto=...)` for routing, and router decisions are stored as AIMessage entries in `history`
- `clip_history()` clips to 100 messages (was 16K chars when history was a string)

## Workflow Execution Flow

1. User designs workflow as nodes on visual canvas
2. Frontend saves workflow to backend via `POST /workflows/{username}`
3. User clicks Run → WebSocket connects to `/ws/run/{username}`, sends `start` with `workflow_name`
4. Backend creates `WorkflowSession`, reads workflow JSON, registers custom tools via `@tool` decorator, builds `StateGraph` with `MemorySaver` checkpointer
5. Graph executes via `graph.astream()`, HUMAN_INPUT nodes trigger `interrupt_before` pause
6. For LLM nodes with tools: `llm.bind_tools()` enables native tool calling — the LLM generates `AIMessage` with `tool_calls`, which are executed and results returned as `ToolMessage`, then the LLM continues
7. For ROUTER nodes: LLM output determines next node via `Command(goto=...)` instead of `router_result` state field
8. Output streams back via WebSocket; on `input_request`, sidebar shows input panel
9. User submits input → `input` message → `WorkflowSession.resume()` → execution continues
10. On completion, `[Workflow completed]` marker appended; session cleaned up after 5-minute delay

## SSOT Design

Nodes are the **Single Source of Truth**. Edges are **derived** from node data:
- `nexts: string[]` → sequential edges (LLM, INFO, HUMAN_INPUT, START)
- `branches: Record<string, string>` → branch edges (ROUTER only)

`NodeVerify` enforces graph integrity:
- ROUTER nodes use `branches` only (no `nexts`)
- Non-ROUTER nodes use `nexts` only (no `branches`)
- START nodes cannot be targets of `nexts`
- START and HUMAN_INPUT cannot be branch targets
- `input_schema` only exists on HUMAN_INPUT nodes
- DFS-based cycle detection labels back-edges as `loop`

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `backend/src/main.py` | FastAPI app, CORS, WebSocket `/ws/run`, `/chatbot` routes, router includes |
| `backend/src/WorkFlow.py` | LangGraph StateGraph builder (`build_graph`), node execution functions, PipelineState |
| `backend/src/llm.py` | `get_llm()` provider factory (DeepSeek only), `clip_history()`, `ChatBot()` |
| `backend/src/NodeData.py` | `NodeData` dataclass with backward compat `from_dict()` |
| `backend/src/tool_executor.py` | `ToolExecutor` — tool dispatch for custom tools, `get_bound_tools()` for `bind_tools()` |
| `backend/src/custom_tool_registry.py` | `CustomToolRegistry` — per-user Python tool CRUD, `register_all()` with `@tool` decorator |
| `backend/src/custom_tool_routes.py` | Custom tools REST API |
| `backend/src/workflow_routes.py` | Workflow CRUD API with name validation |
| `backend/src/workflow_session.py` | `WorkflowSession` — WebSocket session with pause/resume/stop |
| `backend/src/FileTransmit.py` | File upload/download/clean-cache routes |
| `backend/src/ServerTee.py` | Stdout tee to log files with subscriber streaming |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/routes/graph/+page.svelte` | Main graph editor page with drag-and-drop placement + sidebar RunWindow |
| `frontend/src/routes/graph/flow/node-schema.ts` | `NodeType` enum, `JsonNodeData`/`FlowNodeData`, converters |
| `frontend/src/routes/graph/flow/graphs.store.svelte.ts` | SSOT stores: `currentNodes`, `currentEdges` (derived), `currentWorkflowName` |
| `frontend/src/routes/graph/flow/graph-algo.svelte` | AddNode, RemoveNode, AddEdge, RemoveEdge, NodeVerify |
| `frontend/src/routes/graph/flow/node-texture.svelte` | Node rendering with type-specific UI |
| `frontend/src/routes/graph/flow/tool-selector.svelte` | Custom tool picker |
| `frontend/src/routes/graph/flow/graphs-io.svelte` | Workflow CRUD via backend API |
| `frontend/src/routes/graph/menu/RunWindow.svelte` | Sidebar execution panel + HITL input |
| `frontend/src/routes/graph/menu/CustomToolWindow.svelte` | Custom Python tool CRUD modal |
| `frontend/src/routes/graph/menu/ConfigWindow.svelte` | LLM model name + API key config |
| `frontend/src/routes/graph/menu/toolbar.svelte` | Top navigation bar with workflow management |

## Environment Variables

| Variable | Scope | Default | Description |
|----------|-------|---------|-------------|
| `VITE_BACKEND_URL` | Frontend (compile-time) | `http://localhost:5000` | Backend URL |
| `BACKEND_PORT` | Backend | `5000` | Backend listen port |
| `VITE_DEEPSEEK_API_KEY` | Frontend (compile-time) | — | DeepSeek API key |

## Development Commands

```bash
# Frontend
cd frontend
npm install
npm run dev              # Dev server on port 3000
npm run build            # Production build
npm run check            # Type checking
npm run lint             # Prettier + ESLint
npm run test:unit        # Vitest (client/jsdom + server/node workspaces)
npm run test:e2e         # Playwright (requires build first)

# Backend
cd backend
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 5000
```

## How to Extend

### Add a new node type
1. Add to `NodeType` enum in `frontend/src/routes/graph/flow/node-schema.ts`
2. Update `NodeVerify` in `graph-algo.svelte` for edge rules
3. Update rendering in `node-texture.svelte`
4. Add execution logic in `backend/src/WorkFlow.py` (`build_graph()`)

### Add a new LLM provider
1. Update `get_llm()` in `backend/src/llm.py` with a model name detection pattern
2. Add corresponding `langchain-*` package dependency

### Add a new tool source
1. Add dispatch logic in `backend/src/tool_executor.py`
2. Update `custom_tool_registry.py` or create new registry module
3. Add frontend UI in `frontend/src/routes/graph/flow/tool-selector.svelte`

## File Formats

### Workflow JSON (`workspace/{username}/workflows/{name}.json`)
```json
{
  "name": "my-workflow",
  "nodes": [
    {
      "uniq_id": "1",
      "name": "Start",
      "description": "",
      "type": "START",
      "nexts": ["2"],
      "tools": [],
      "branches": {},
      "max_iterations": 0,
      "input_schema": {},
      "ext": { "pos_x": 100, "pos_y": 100, "width": 280, "height": 280 }
    }
  ],
  "updated_at": "2026-04-22T12:00:00"
}
```

### Custom Tool (`workspace/{username}/custom_tools/{name}.json`)
```json
{
  "name": "add",
  "description": "Add two numbers",
  "code": "def add(a, b):\n    return a + b"
}
```

> **Note**: Custom tool code is loaded via `exec()` with LangChain `@tool` decorator. The registry wraps user-defined functions into `BaseTool` instances for `llm.bind_tools()`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `allow_origins` in `backend/src/main.py` |
| LLM model not supported | Currently only DeepSeek models are supported via `get_llm()` |
| WebSocket disconnect | Session continues in background; reconnect sends `status` to resume |
| Custom tool not found | Check `workspace/{username}/custom_tools/` for the tool JSON file |
| Tool calling fails | Verify custom tool code uses valid Python and `@tool` decorator is compatible |
