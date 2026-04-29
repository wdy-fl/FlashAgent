# LangGraph-GUI Agent 能力扩展需求文档

> 版本: 1.1.0
> 日期: 2026-04-19
> 状态: 待评审

---

## 0. 项目定位

### 定位：轻量级 Agent 编排平台

LangGraph-GUI 定位为**轻量级 AI Agent 可视化编排平台**，对标 Dify / Langflow，核心差异化为：

| 差异维度 | Dify / Langflow | LangGraph-GUI |
|---|---|---|
| 部署复杂度 | 依赖 PostgreSQL, Redis, 向量数据库等 | **零外部依赖**，纯 Docker Compose 开箱即用 |
| 技术栈 | Next.js/React + Flask/FastAPI | **SvelteKit 5 + FastAPI**，更轻量更现代 |
| 架构特色 | 独立边存储 | **SSOT（节点即边的真相源）**，架构更干净 |
| 框架绑定 | 平台自有引擎 / LangChain 绑定 | 当前基于 LangGraph，**未来支持多框架后端** |
| 目标用户 | 全栈 LLM 应用开发者 | 需要构建 Agent 但追求轻量部署的开发者与小团队 |

### 设计原则

1. **轻量优先** — 最小依赖，快速启动，低资源占用
2. **框架解耦** — 后端执行引擎可替换，不绑定单一 Agent 框架
3. **标准协议** — 拥抱 MCP、SKILL 等开放标准，融入 Agent 工具生态
4. **可视化即一切** — 工作流的构建、调试、监控都在画布上完成
5. **企业可用** — 支持复杂编排场景，多用户隔离，可扩展到生产环境

### 未来框架扩展性

当前后端基于 LangGraph StateGraph 执行工作流。架构设计应保证：

- 后端执行引擎通过**抽象接口**与前端解耦
- 前端的节点/边数据模型是**框架无关**的（当前已满足：JsonNodeData 不包含 LangGraph 特有概念）
- 未来可通过实现新的执行引擎适配器来支持 CrewAI、Semantic Kernel、AutoGen 等框架
- 切换框架不影响前端编辑体验和数据格式

---

## 1. 背景与目标

### 1.1 项目现状

LangGraph-GUI 是一个可视化节点工作流编辑器，当前支持 6 种节点类型（START、LLM、TOOL、CONDITION、INFO、SUBGRAPH），能够构建基础的 LLM 工作流。

**当前主要局限：**

| 问题 | 详情 |
|---|---|
| 工具系统封闭 | TOOL 节点只能定义本地 Python 函数，无法接入外部工具生态 |
| 单工具绑定 | LLM 节点只能绑定一个工具，LLM 无法从多个工具中选择 |
| 工具字段 bug | `SvelteNodeToJsonNode` 硬编码 `tool: ''`，序列化时工具配置丢失 |
| 类型定义缺失 | `FlowNodeData` TypeScript 类型未声明 `tool` 字段 |
| 分支能力弱 | CONDITION 节点只支持 True/False 二元分支，无法实现多路路由 |
| 无外部工具协议 | 不支持 MCP 等标准化工具协议 |
| 无可复用能力包 | 没有 SKILL 标准化能力包机制 |

### 1.2 升级目标

构建 **三层工具体系**，使项目具备现代 AI Agent 的核心能力：

1. **MCP 集成**（第一优先级） — 接入外部工具生态
2. **工具集升级** — LLM 节点支持多工具绑定与 LLM 自主选择
3. **SKILL 能力库** — 标准化能力包 + 渐进式发现机制

---

## 2. 总体架构

### 2.1 三层工具体系

```
┌─────────────────────────────────────────────────────────┐
│                    LLM 节点执行时                        │
│                                                         │
│  ┌─────────────────────┐   ┌─────────────────────────┐  │
│  │  第一层：显式工具     │   │ 第二层：Skill 渐进发现   │  │
│  │  (用户手动绑定)      │   │ (运行时自动匹配)         │  │
│  │                     │   │                         │  │
│  │  · CUSTOM_TOOL 函数  │   │  · Skill Discovery      │  │
│  │  · MCP Server 工具   │   │    Engine 匹配元数据     │  │
│  └────────┬────────────┘   └────────┬────────────────┘  │
│           │                         │                   │
│           └─────────┬───────────────┘                   │
│                     ▼                                   │
│           ┌─────────────────┐                           │
│           │  合并工具列表     │                           │
│           │  注入 LLM Prompt │                           │
│           └────────┬────────┘                           │
│                    ▼                                    │
│           ┌─────────────────┐                           │
│           │  LLM 自主选择    │                           │
│           │  调用工具或返回   │                           │
│           └─────────────────┘                           │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 第三层：Skill 全局上下文                              ││
│  │ SKILL.md 的领域知识、约束、指引注入 prompt             ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流概览

```
前端 (SvelteKit)
  │
  ├── MCP 连接管理 UI → 配置 MCP Server 地址
  ├── Skill 管理 UI   → 导入/删除 Skill 包
  ├── LLM 节点 UI    → 绑定 tools[] + enable_skills 开关
  │
  ▼
后端 (FastAPI)
  │
  ├── MCP Client Manager   → 连接 MCP Server, 获取工具列表
  ├── Skill Registry       → 管理已导入 Skill 的元数据和文件
  ├── Skill Discovery      → 运行时上下文匹配
  ├── Tool Executor        → 统一执行 CUSTOM_TOOL / MCP / Skill 工具
  │
  ▼
外部服务
  ├── MCP Server (SSE)     → 提供远程工具调用
  └── LLM Provider         → 推理与工具选择
```

---

## 3. Phase 1：MCP Client 集成

> 优先级：最高
> 目标：后端作为 MCP Client 连接外部 MCP Server，在工作流中调用 MCP 工具

### 3.1 MCP 连接管理

#### 3.1.1 后端 MCP Client Manager

**职责：** 管理与外部 MCP Server 的连接、工具发现、工具调用。

**核心功能：**

- **连接管理**：建立/断开与 MCP Server 的 SSE 连接
- **工具发现**：连接成功后调用 `tools/list` 获取该 Server 提供的所有工具列表（名称、描述、参数 schema）
- **工具调用**：通过 `tools/call` 向 MCP Server 发送工具调用请求并获取结果
- **连接状态**：维护每个 Server 的连接状态（connected / disconnected / error）

**传输协议：** 仅支持 **SSE（Server-Sent Events）** 远程连接方式。

**配置存储：**

- 每个用户独立的 MCP 配置，存储在 `workspace/{username}/mcp_config.json`
- 配置格式：

```json
{
  "servers": [
    {
      "id": "brave-search",
      "name": "Brave Search",
      "url": "http://localhost:8080/sse",
      "enabled": true
    },
    {
      "id": "filesystem",
      "name": "File System",
      "url": "http://remote-server:9090/sse",
      "enabled": true
    }
  ]
}
```

#### 3.1.2 后端 API 新增

| 路由 | 方法 | 说明 |
|---|---|---|
| `/mcp/{username}/servers` | GET | 获取已配置的 MCP Server 列表及状态 |
| `/mcp/{username}/servers` | POST | 添加新的 MCP Server 配置 |
| `/mcp/{username}/servers/{server_id}` | DELETE | 删除 MCP Server 配置 |
| `/mcp/{username}/servers/{server_id}/toggle` | POST | 启用/禁用某个 Server |
| `/mcp/{username}/tools` | GET | 获取所有已连接 Server 提供的工具列表 |
| `/mcp/{username}/tools/{server_id}` | GET | 获取指定 Server 的工具列表 |

**工具列表返回格式：**

```json
{
  "tools": [
    {
      "id": "mcp:brave-search:search",
      "server_id": "brave-search",
      "server_name": "Brave Search",
      "name": "search",
      "description": "Search the web using Brave Search",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": { "type": "string", "description": "Search query" }
        },
        "required": ["query"]
      }
    }
  ]
}
```

#### 3.1.3 前端 MCP 管理 UI

**位置：** 在侧边栏（sidebar）新增 "MCP" 按钮，点击打开 MCP 管理窗口。

**MCP 管理窗口功能：**

1. **Server 列表**：展示所有已配置的 MCP Server
   - 显示：名称、URL、连接状态（绿色/红色指示灯）、启用/禁用开关
   - 操作：删除 Server
2. **添加 Server**：表单输入名称 + URL，点击添加
3. **工具预览**：点击某个 Server，展示其提供的所有工具（名称 + 描述）

#### 3.1.4 MCP 生命周期

```
用户添加 MCP Server (前端)
       │
       ▼
POST /mcp/{username}/servers (后端保存配置)
       │
       ▼
MCP Client Manager 建立 SSE 连接
       │
       ▼
调用 tools/list 获取工具列表 → 缓存
       │
       ▼
工具列表可供前端查询 & LLM 节点绑定
       │
       ▼
工作流运行时，LLM 节点调用 MCP 工具
       │
       ▼
MCP Client Manager 通过 tools/call 发送请求
       │
       ▼
返回结果写入 history
```

### 3.2 工具集统一与 LLM 节点升级

#### 3.2.1 数据模型变更

**前端 `JsonNodeData` 接口变更：**

```typescript
// Before
interface JsonNodeData {
  // ...
  tool: string;           // 单个工具名
  // ...
}

// After
interface JsonNodeData {
  // ...
  tools: string[];        // 工具 ID 数组（支持多个来源的工具）
  enable_skills: boolean; // 是否启用 Skill 渐进式发现（Phase 3）
  // ...
}
```

**工具 ID 命名约定：**

| 来源 | ID 格式 | 示例 |
|---|---|---|
| CUSTOM_TOOL 节点 | `{function_name}` | `RollD20` |
| MCP Server | `mcp:{server_id}:{tool_name}` | `mcp:brave-search:search` |
| Skill（Phase 3） | `skill:{skill_name}:{tool_name}` | `skill:web-research:fetch_url` |

**前端 `FlowNodeData` 类型变更：**

```typescript
// Before: tool 字段未声明，CONDITION 使用 true_next/false_next
interface FlowNodeData {
  uniq_id: string;
  name: string;
  description: string;
  nexts: Set<string>;
  type: NodeType;
  true_next: string | null;
  false_next: string | null;
}

// After: 新增 tools、enable_skills，ROUTER 使用 branches 替代 true_next/false_next
interface FlowNodeData {
  uniq_id: string;
  name: string;
  description: string;
  nexts: Set<string>;
  type: NodeType;
  branches: Record<string, string>;  // 变更：替代 true_next/false_next（ROUTER 节点使用）
  tools: string[];                   // 新增
  enable_skills: boolean;            // 新增（Phase 3 使用）
}
```

**后端 `NodeData` dataclass 变更：**

```python
# Before
@dataclass
class NodeData(Serializable):
    tool: str = ""
    true_next: Optional[int] = None
    false_next: Optional[int] = None

# After
@dataclass
class NodeData(Serializable):
    tools: List[str] = field(default_factory=list)
    enable_skills: bool = False
    branches: Dict[str, str] = field(default_factory=dict)  # 替代 true_next/false_next
```

#### 3.2.2 序列化修复

**当前 bug：** `SvelteNodeToJsonNode` 中硬编码 `tool: ''`，导致工具配置在保存时丢失。

**修复方案：**

```typescript
// Before (SvelteNodeToJsonNode)
tool: ''

// After
tools: node.data.tools ?? []
enable_skills: node.data.enable_skills ?? false
```

同时修复 `JsonNodeToSvelteNode`：

```typescript
// Before
// tool 字段被忽略

// After
tools: json.tools ?? [],
enable_skills: json.enable_skills ?? false
```

#### 3.2.3 节点类型重命名

**变更一：** `NodeType.TOOL` → `NodeType.CUSTOM_TOOL`

**变更二：** `NodeType.CONDITION` → `NodeType.ROUTER`（同时升级为多分支）

**TOOL → CUSTOM_TOOL 影响范围：**

| 文件 | 变更 |
|---|---|
| `frontend/.../node-schema.ts` | 枚举值 `TOOL` → `CUSTOM_TOOL` |
| `frontend/.../node-texture.svelte` | 条件渲染逻辑适配 |
| `frontend/.../node-handles.svelte` | Handle 可见性逻辑适配 |
| `frontend/.../graph-algo.svelte` | `NodeVerify` 中的 TOOL 引用适配 |
| `backend/src/WorkFlow.py` | `find_nodes_by_type(node_map, "TOOL")` → `"CUSTOM_TOOL"` |
| `backend/src/NodeData.py` | type 默认值和文档更新 |

**CONDITION → ROUTER 影响范围：**

| 文件 | 变更 |
|---|---|
| `frontend/.../node-schema.ts` | 枚举值 `CONDITION` → `ROUTER`；移除 `true_next`/`false_next`，新增 `branches` |
| `frontend/.../node-texture.svelte` | CONDITION 渲染替换为 ROUTER（动态分支列表 UI） |
| `frontend/.../node-handles.svelte` | 固定的 True/False Handle → 动态多 Handle（每个分支一个输出 Handle） |
| `frontend/.../graph-algo.svelte` | `NodeVerify` 和 `AddEdge`/`RemoveEdge` 逻辑重构，适配 branches |
| `backend/src/WorkFlow.py` | `condition_switch` → `router_switch`；`conditional_edge` → `router_edge`；`add_conditional_edges` 适配多分支 |
| `backend/src/NodeData.py` | `true_next`/`false_next` → `branches: Dict[str, str]` |

**向后兼容：** `JsonNodeToSvelteNode` 中增加兼容逻辑：
- 旧 `"TOOL"` 类型自动映射为 `"CUSTOM_TOOL"`
- 旧 `"CONDITION"` 类型自动映射为 `"ROUTER"`
- 旧 `{true_next, false_next}` 自动转换为 `branches: {"True": true_next, "False": false_next}`

#### 3.2.4 LLM 节点 UI 改造

**Before（当前）：**

```
┌────────────────────────┐
│ Name: [Dungeon Master]  │
│ Type: [LLM          ▼]  │
│ Tool: [RollD20      ]   │  ← 文本输入框，单个工具名
│ Desc: [You are a DM...] │
└────────────────────────┘
```

**After（升级后）：**

```
┌──────────────────────────────┐
│ Name: [Dungeon Master]        │
│ Type: [LLM              ▼]    │
│ Tools: [点击选择工具... ▼]     │  ← 多选下拉，展示所有可用工具
│   ☑ RollD20 (local)           │
│   ☑ search (mcp:brave)        │
│   ☐ read_file (mcp:fs)        │
│ ☐ Enable Skills               │  ← Skill 发现开关（Phase 3 激活）
│ Desc: [You are a DM...]       │
└──────────────────────────────┘
```

**工具选择器数据来源：**

1. 画布上所有 `CUSTOM_TOOL` 节点定义的函数名
2. 所有已连接且启用的 MCP Server 提供的工具（通过 `/mcp/{username}/tools` 获取）
3. （Phase 3）已导入 Skill 提供的工具

#### 3.2.5 后端工具执行统一

**新增 `ToolExecutor` 类**，统一处理所有来源的工具调用：

```python
class ToolExecutor:
    """统一工具执行器"""

    def __init__(self, tool_registry, mcp_manager, skill_registry=None):
        self.tool_registry = tool_registry      # CUSTOM_TOOL 注册表
        self.mcp_manager = mcp_manager          # MCP Client Manager
        self.skill_registry = skill_registry    # Skill 注册表 (Phase 3)

    def get_tool_info(self, tool_id: str) -> dict:
        """获取工具的描述信息，用于注入 prompt"""
        if tool_id.startswith("mcp:"):
            return self.mcp_manager.get_tool_info(tool_id)
        elif tool_id.startswith("skill:"):
            return self.skill_registry.get_tool_info(tool_id)
        else:
            return self.tool_registry.get_tool_info(tool_id)

    def execute(self, tool_id: str, args: dict) -> str:
        """执行工具调用"""
        if tool_id.startswith("mcp:"):
            _, server_id, tool_name = tool_id.split(":", 2)
            return self.mcp_manager.call_tool(server_id, tool_name, args)
        elif tool_id.startswith("skill:"):
            _, skill_name, tool_name = tool_id.split(":", 2)
            return self.skill_registry.call_tool(skill_name, tool_name, args)
        else:
            return self.tool_registry.call_tool(tool_id, args)
```

#### 3.2.6 Prompt 模板改造

**当前（单工具）：**

```
You have the tool: {tool_info}.
History: {history}
{node_description}
Please output in JSON format: {"function": "...", "args": [...]}
```

**升级后（多工具）：**

```
You are {node_name}.
{node_description}

History:
{history}

Available tools:
{tools_list}

Based on the current task and history, decide your action:
- If you need to use a tool, respond with: {"function": "<tool_name>", "args": {...}}
- If no tool is needed, respond with: {"result": "<your answer>"}
```

其中 `{tools_list}` 格式：

```
1. RollD20() -> int : "掷一个20面骰子"
2. mcp:brave-search:search(query: str) -> str : "Search the web using Brave Search"
3. mcp:fs:read_file(path: str) -> str : "Read a file from the filesystem"
```

**无工具绑定时**（tools 为空且 enable_skills 为 false）：

```
You are {node_name}.
{node_description}

History:
{history}

Please respond in JSON format: {"result": "<your answer>"}
```

行为与当前无 tool 字段的 LLM 节点一致。

---

## 4. Phase 2：CONDITION → ROUTER 多分支升级 + 画布循环增强

> 优先级：中
> 目标：将 CONDITION 节点升级为 ROUTER，支持多路分支；增强循环构建能力

### 4.1 现状分析

当前 CONDITION 节点只支持 True/False 二元分支：

```
数据模型:
  true_next:  string | null
  false_next: string | null

LLM 输出: {"switch": true/false}
画布 UI:  固定两个输出 Handle（True / False）
```

**局限性：**

1. 只能 True/False 二元分支，无法实现意图分类、多路路由
2. 嵌套多个 CONDITION 才能实现多路判断，画布杂乱
3. 没有循环次数限制，可能无限循环
4. 前端没有循环可视化提示

### 4.2 ROUTER 节点设计

#### 4.2.1 核心变更：branches 替代 true_next/false_next

**数据模型：**

```typescript
// Before (CONDITION)
{
  type: "CONDITION",
  true_next: "node_3",
  false_next: "node_5"
}

// After (ROUTER)
{
  type: "ROUTER",
  branches: {
    "True": "node_3",
    "False": "node_5"
  }
}
```

`branches` 是一个 `Record<string, string>` 字典，key 是用户自定义的分支标签（label），value 是目标节点 ID。

**多路路由示例：**

```json
{
  "type": "ROUTER",
  "name": "意图分类",
  "description": "判断用户意图属于哪个类别",
  "branches": {
    "问候": "node_greeting",
    "提问": "node_question",
    "投诉": "node_complaint",
    "其他": "node_fallback"
  },
  "max_iterations": 0
}
```

#### 4.2.2 ROUTER 节点 UI

**画布上的 ROUTER 节点：**

```
┌──────────────────────────────┐
│ ROUTER: 意图分类              │
│ Desc: [判断用户意图...]        │
│                              │
│ Branches:                    │
│   [+ 添加分支]                │
│   ● 问候   ─── ○ (Handle)    │
│   ● 提问   ─── ○ (Handle)    │
│   ● 投诉   ─── ○ (Handle)    │
│   ● 其他   ─── ○ (Handle)    │
│   max_iterations: [0]        │
└──────────────────────────────┘
```

**UI 交互：**

1. **添加分支**：点击 "+" 按钮，输入分支标签名，自动新增一个输出 Handle
2. **删除分支**：每个分支旁有删除按钮，删除分支同时断开该分支连接的边
3. **重命名分支**：点击分支标签可编辑
4. **连线**：每个分支对应一个独立的输出 Handle，用户从 Handle 拖线到目标节点
5. **默认**：新建 ROUTER 节点时预设 "True"、"False" 两个分支（兼容旧用法）

#### 4.2.3 后端执行逻辑

**Prompt 模板：**

```
{node.description}

History: {history}

Based on the context, decide which branch to take.
Available branches: {branch_labels}

Respond in JSON format: {"switch": "<branch_label>"}
```

其中 `{branch_labels}` 是所有分支标签的列表，例如：`["问候", "提问", "投诉", "其他"]`

**路由函数：**

```python
# Before
def conditional_edge(state: PipelineState) -> Literal["True", "False"]:
    if state["condition"] in ["True", "true", True]:
        return "True"
    else:
        return "False"

# After
def router_edge(state: PipelineState) -> str:
    return state["router_result"]  # 直接返回 LLM 选择的分支标签
```

**PipelineState 变更：**

```python
# Before
class PipelineState(TypedDict):
    history: Annotated[str, operator.add]
    task: Annotated[str, operator.add]
    condition: Annotated[bool, lambda x, y: y]

# After
class PipelineState(TypedDict):
    history: Annotated[str, operator.add]
    task: Annotated[str, operator.add]
    router_result: Annotated[str, lambda x, y: y]  # 分支标签字符串
```

**图构建变更：**

```python
# Before (build_subgraph)
subgraph.add_conditional_edges(
    node_id,
    conditional_edge,
    {"True": condition.true_next or END, "False": condition.false_next or END}
)

# After
branch_map = {}
for label, target_id in router_node.branches.items():
    branch_map[label] = target_id if target_id else END
subgraph.add_conditional_edges(node_id, router_edge, branch_map)
```

#### 4.2.4 边的 SSOT 变更

当前系统中，边从节点数据派生（Nodes are SSOT）。ROUTER 节点的边派生规则：

```
ROUTER 节点的出边 = branches 字典的所有 value（目标节点 ID）
```

`graph-algo.svelte` 中的 `NodeVerify`、`AddEdge`、`RemoveEdge` 需要适配：

- **AddEdge**：ROUTER 节点的每个分支 Handle 只能连接一条边（一个分支对应一个目标）
- **RemoveEdge**：删除边时，将对应分支的 value 清空
- **NodeVerify**：验证 ROUTER 节点的 branches 中没有悬空引用

### 4.3 循环增强

#### 4.3.1 max_iterations 字段

**新增字段：**

```typescript
// ROUTER (原 CONDITION) 节点新增
max_iterations: number;  // 最大循环次数，0 表示无限制，默认 10
```

**后端行为：** 在 `PipelineState` 中新增 `iteration_counts: Dict[str, int]` 计数器（每个 ROUTER 节点独立计数）。每次经过某 ROUTER 节点时递增该节点的计数。达到 `max_iterations` 时，自动选择 branches 中的**第一个分支**（退出循环）。

#### 4.3.2 前端循环可视化

- 当边连接形成环时（检测到拓扑环），前端用**虚线 + 特殊颜色**渲染该边
- 在形成环的边上显示标注（如 "loop"）

---

## 5. Phase 3：SKILL 能力库与渐进式发现

> 优先级：低（在 Phase 1 完成后开展）
> 目标：支持标准化 Skill 能力包导入，实现渐进式发现机制

### 5.1 SKILL 标准概述

遵循 AI Agent Skill 开放标准目录结构：

```
skill-name/
├── SKILL.md                # ⭐ 核心必需文件（元数据 + 执行指令）
├── scripts/                # 可选：可执行脚本
│   ├── main.py
│   └── utils.sh
├── references/             # 可选：参考文档
│   ├── api-docs.md
│   └── schema.json
└── assets/                 # 可选：模板和资源文件
    └── report-template.md
```

**SKILL.md 结构：**

```yaml
---
name: skill-name
description: 简短描述（50-150字符）
version: 1.0.0
author: your-name
tags: ["finance", "report"]
category: business
dependencies: ["data-fetch"]
---

## 何时使用
触发场景与关键词...

## 前置条件
...

## 操作步骤
1. ...
2. ...

## 输入输出示例
...

## 约束与边界
...
```

### 5.2 SKILL 在系统中的定位

**SKILL 不是节点类型，而是贯穿整个 Agent 运行时的后台能力库。**

- SKILL 不出现在画布上
- SKILL 通过**渐进式发现**在运行时被动态匹配和激活
- SKILL 为 LLM 提供两种能力：
  1. **工具**：scripts/ 中的可执行函数
  2. **领域知识与行为指引**：SKILL.md 中的指令、约束、操作步骤

### 5.3 Skill 管理

#### 5.3.1 后端 Skill Registry

**职责：** 管理已导入 Skill 的元数据、文件存储、工具注册。

**存储位置：** `workspace/{username}/skills/{skill-name}/`

**Skill 注册流程：**

```
用户上传 Skill 包 (zip)
       │
       ▼
后端解压到 workspace/{username}/skills/{skill-name}/
       │
       ▼
解析 SKILL.md 的 YAML Frontmatter → 提取元数据
       │
       ▼
解析 scripts/ 目录 → 注册可调用工具
       │
       ▼
元数据写入 Skill Registry 索引
```

**Skill 元数据索引（内存 + 持久化）：**

```python
@dataclass
class SkillMeta:
    name: str               # 技能唯一标识
    description: str        # 简短描述
    version: str            # 版本号
    author: str             # 作者
    tags: List[str]         # 分类标签
    category: str           # 类别
    dependencies: List[str] # 依赖技能
    trigger_keywords: List[str]  # 从 SKILL.md "何时使用" 段提取的关键词
    tools: List[str]        # 该 Skill 提供的工具名列表
    skill_md_path: str      # SKILL.md 文件路径
    scripts_dir: str        # scripts/ 目录路径
```

#### 5.3.2 后端 API 新增

| 路由 | 方法 | 说明 |
|---|---|---|
| `/skills/{username}` | GET | 获取已导入的 Skill 列表 |
| `/skills/{username}` | POST | 导入新的 Skill 包（接收 zip 文件） |
| `/skills/{username}/{skill_name}` | GET | 获取指定 Skill 的详细信息 |
| `/skills/{username}/{skill_name}` | DELETE | 删除指定 Skill |
| `/skills/{username}/{skill_name}/tools` | GET | 获取指定 Skill 提供的工具列表 |

#### 5.3.3 前端 Skill 管理 UI

**位置：** 在侧边栏新增 "Skills" 按钮，点击打开 Skill 管理窗口。

**Skill 管理窗口功能：**

1. **已导入 Skill 列表**
   - 显示：名称、描述、版本、标签、工具数量
   - 操作：查看详情、删除
2. **导入 Skill**：上传 zip 文件
3. **Skill 详情**：点击 Skill 展示 SKILL.md 内容、工具列表、scripts 文件列表

### 5.4 渐进式发现引擎（Skill Discovery Engine）

#### 5.4.1 核心概念

渐进式发现的目标是：**不一次性加载所有 Skill，而是根据当前任务上下文动态匹配最相关的 Skill。**

#### 5.4.2 发现流程

```
LLM 节点执行 (enable_skills=true)
       │
       ▼
┌─────────────────────────────────────────┐
│         Skill Discovery Engine          │
│                                         │
│  输入:                                   │
│    - 当前 history (最近 N 条)            │
│    - 当前 node 的 description           │
│    - 当前 task 内容                      │
│                                         │
│  匹配策略:                               │
│    1. 关键词匹配                         │
│       - 输入文本 vs SKILL.md 的:         │
│         · description                    │
│         · tags                           │
│         · trigger_keywords               │
│    2. 语义相似度 (可选, 需要 embedding)   │
│       - 输入文本 embedding vs            │
│         Skill description embedding      │
│    3. 依赖关系                           │
│       - 如果已激活 Skill A 且 A 依赖 B，  │
│         则 B 也被发现                     │
│                                         │
│  输出:                                   │
│    - Top-K 相关 Skill (默认 K=3)         │
│    - 每个 Skill 的:                      │
│      · 工具定义 (从 scripts/ 提取)        │
│      · 行为指引 (从 SKILL.md 提取)        │
└─────────────────────────────────────────┘
       │
       ▼
注入到 LLM 节点的 LLM Prompt 中
```

#### 5.4.3 匹配策略详细设计

**阶段一（MVP）：关键词匹配**

- 从 SKILL.md 的 `description`、`tags`、`category`、"何时使用"段落提取关键词集合
- 对当前上下文文本进行简单的关键词/短语匹配
- 按匹配数量排序，取 Top-K
- 实现简单，无需额外依赖

**阶段二（增强）：语义匹配**

- 使用 embedding 模型（如本地 Ollama embedding 或 OpenAI embedding API）
- 对每个 Skill 的描述预计算 embedding 向量
- 运行时计算当前上下文的 embedding
- 通过余弦相似度匹配
- 需要新增 embedding 依赖

#### 5.4.4 Skill 内容注入 Prompt

当 Skill 被发现后，注入到 LLM 节点的 prompt 中：

```
You are {node_name}.
{node_description}

History:
{history}

Available tools:
{explicit_tools_list}
{discovered_skill_tools_list}

Relevant skill guidance:
---
[Skill: web-research]
{SKILL.md 的"操作步骤"和"约束与边界"段落}
---

Based on the current task and history, decide your action:
- If you need to use a tool, respond with: {"function": "<tool_name>", "args": {...}}
- If no tool is needed, respond with: {"result": "<your answer>"}
```

#### 5.4.5 LLM 节点 enable_skills 字段

- **默认值：false**（不启用 Skill 发现，行为与现有 LLM 完全一致）
- **为 true 时：** 执行前额外运行 Skill Discovery Engine
- **前端 UI：** LLM 节点中显示一个 "Enable Skills" 复选框

### 5.5 Skill 工具执行

Skill 中 scripts/ 的工具执行方式与 CUSTOM_TOOL 类似：

1. 导入 Skill 时，解析 scripts/ 下的 Python 文件
2. 提取 `@tool` 装饰的函数，注册到 Skill 的工具注册表
3. 运行时通过 `ToolExecutor` 统一调用

**工具 ID 格式：** `skill:{skill_name}:{function_name}`

---

## 6. 节点类型变更汇总

### 6.1 变更前后对比

| 节点类型 | 变更前 | 变更后 | 变更说明 |
|---|---|---|---|
| `START` | 入口节点 | **不变** | |
| `LLM` | 单工具绑定 | **多工具绑定 + Skill 开关** | tool→tools[], 新增 enable_skills |
| `TOOL` | 本地 Python 函数定义 | **重命名为 CUSTOM_TOOL** | 功能不变，仅改名 |
| `CONDITION` | 二元分支 | **重命名为 ROUTER，升级为多分支** | true_next/false_next → branches，新增 max_iterations |
| `INFO` | 静态文本注入 | **不变** | |
| `SUBGRAPH` | 嵌套子图 | **不变** | |

### 6.2 完整 NodeType 枚举（变更后）

```typescript
enum NodeType {
  START = 'START',
  LLM = 'LLM',
  CUSTOM_TOOL = 'CUSTOM_TOOL',   // 原 TOOL，重命名
  ROUTER = 'ROUTER',             // 原 CONDITION，重命名 + 多分支升级
  INFO = 'INFO',
  SUBGRAPH = 'SUBGRAPH',
}
```

### 6.3 完整 JsonNodeData 接口（变更后）

```typescript
interface JsonNodeData {
  uniq_id: string;
  name: string;
  description: string;
  nexts: string[];
  type: string;
  tools: string[];                     // 原 tool: string → tools: string[]
  enable_skills: boolean;              // 新增
  branches: Record<string, string>;    // 原 true_next/false_next → branches（ROUTER 使用）
  max_iterations: number;              // 新增（ROUTER 节点使用）
  ext: {
    pos_x?: number;
    pos_y?: number;
    width?: number;
    height?: number;
  };
}
```

---

## 7. 实施计划

### Phase 1：MCP Client 集成 + 工具集升级

**前置修复：**
- [ ] 修复 `SvelteNodeToJsonNode` 中 tool 字段序列化 bug
- [ ] 为 `FlowNodeData` 添加 tools 和 enable_skills 类型声明

**后端任务：**
- [ ] 实现 MCP Client Manager（SSE 连接、工具发现、工具调用）
- [ ] 新增 MCP 管理 API（/mcp/... 系列路由）
- [ ] 实现统一 ToolExecutor 类
- [ ] 改造 LLM 节点执行逻辑（多工具 prompt、LLM 自主选择）
- [ ] TOOL → CUSTOM_TOOL 重命名（后端）
- [ ] NodeData dataclass 更新（tool→tools, 新增 enable_skills）
- [ ] 新增 MCP 相关 Python 依赖（如 `mcp` SDK）

**前端任务：**
- [ ] 数据模型变更（JsonNodeData, FlowNodeData, 序列化/反序列化）
- [ ] TOOL → CUSTOM_TOOL 重命名（前端枚举、UI、验证逻辑）
- [ ] LLM 节点 UI 改造（tools 多选器、enable_skills 开关）
- [ ] MCP 管理窗口 UI
- [ ] 工具选择器组件（展示 CUSTOM_TOOL + MCP 工具列表）
- [ ] 向后兼容处理（旧 JSON 中 tool→tools, TOOL→CUSTOM_TOOL 的自动迁移）

### Phase 2：CONDITION → ROUTER 多分支升级 + 画布循环增强

**后端任务：**
- [ ] CONDITION → ROUTER 重命名（后端枚举、执行逻辑）
- [ ] NodeData: `true_next`/`false_next` → `branches: Dict[str, str]`
- [ ] PipelineState: `condition: bool` → `router_result: str`
- [ ] `condition_switch` → `router_switch`（Prompt 适配多分支标签）
- [ ] `conditional_edge` → `router_edge`（返回分支标签字符串）
- [ ] `build_subgraph`: `add_conditional_edges` 适配 branches 字典
- [ ] ROUTER 节点新增 max_iterations 字段
- [ ] PipelineState 新增 `iteration_counts: Dict[str, int]` 计数器

**前端任务：**
- [ ] CONDITION → ROUTER 重命名（枚举、UI、验证逻辑）
- [ ] `true_next`/`false_next` → `branches` 数据模型迁移
- [ ] ROUTER 节点 UI：动态分支列表（添加/删除/重命名分支）
- [ ] ROUTER 节点 Handle：动态多输出 Handle（每个分支一个）
- [ ] `graph-algo.svelte`: AddEdge/RemoveEdge/NodeVerify 适配 branches
- [ ] 向后兼容：旧 `CONDITION` + `true_next`/`false_next` 自动迁移
- [ ] 前端循环边可视化（虚线 + 标注）

### Phase 3：SKILL 能力库

**后端任务：**
- [ ] 实现 Skill Registry（导入、解析、存储、索引）
- [ ] 实现 Skill Discovery Engine（关键词匹配 MVP）
- [ ] 新增 Skill 管理 API（/skills/... 系列路由）
- [ ] ToolExecutor 扩展支持 Skill 工具
- [ ] LLM 节点执行逻辑扩展（Skill 发现 + 内容注入）

**前端任务：**
- [ ] Skill 管理窗口 UI（导入 zip、列表、详情、删除）
- [ ] 工具选择器扩展（展示 Skill 提供的工具）
- [ ] LLM 节点 enable_skills 开关激活

---

## 8. 向后兼容策略

### 8.1 JSON 数据迁移

旧版 `workflow.json` 加载时自动迁移：

```
旧字段                    →  新字段
type: "TOOL"             →  type: "CUSTOM_TOOL"
type: "CONDITION"        →  type: "ROUTER"
tool: "RollD20"          →  tools: ["RollD20"]
tool: ""                 →  tools: []
true_next: "x"           →  branches: {"True": "x", "False": "y"}
false_next: "y"          →  (合并到 branches)
(缺少 enable_skills)     →  enable_skills: false
(缺少 max_iterations)    →  max_iterations: 0
(缺少 branches)          →  branches: {}
```

### 8.2 API 兼容

- 后端 WorkFlow.py 中的 `find_nodes_by_type` 同时识别 `"TOOL"`/`"CUSTOM_TOOL"` 和 `"CONDITION"`/`"ROUTER"`
- NodeData 的 `from_dict()` 方法兼容旧字段名（`tool`→`tools`，`true_next`+`false_next`→`branches`）

---

## 9. 技术依赖

### 9.1 后端新增依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| `mcp` | latest | MCP Python SDK（SSE Client） |
| `httpx-sse` | latest | SSE 客户端支持 |
| `pyyaml` | (已有) | 解析 SKILL.md YAML frontmatter |

### 9.2 前端

无新增依赖，使用现有技术栈实现。

---

## 10. 非功能需求

### 10.1 安全性

- MCP Server URL 仅支持 HTTP/HTTPS 协议
- CUSTOM_TOOL 节点的 `exec()` 执行机制维持现状（保持简单，安全风险已知且接受）
- Skill 的 scripts/ 执行权限与 CUSTOM_TOOL 一致
- MCP 配置和 Skill 数据按用户隔离（`workspace/{username}/`）

### 10.2 性能

- MCP 工具列表在连接时缓存，不需要每次 LLM 执行时重新获取
- Skill 元数据索引常驻内存，Discovery Engine 匹配操作应在 100ms 内完成
- Skill Discovery 只在 `enable_skills=true` 的 LLM 节点中触发

### 10.3 错误处理

- MCP Server 连接失败：标记状态为 error，不影响其他工具和工作流执行
- MCP 工具调用超时：设置 30 秒超时，超时后返回错误信息写入 history
- Skill 导入失败（格式错误）：返回明确错误信息，不写入 Registry
- Skill Discovery 无匹配：正常执行，仅使用显式绑定的工具

---

## 附录 A：术语表

| 术语 | 定义 |
|---|---|
| MCP | Model Context Protocol，Anthropic 提出的开放协议，用于连接 AI 模型与外部工具/数据源 |
| MCP Server | 实现 MCP 协议的服务端，提供工具和资源供 AI Agent 调用 |
| MCP Client | 实现 MCP 协议的客户端，连接 MCP Server 并调用其工具 |
| SSE | Server-Sent Events，一种基于 HTTP 的服务端推送协议 |
| SKILL | 遵循 AI Agent Skill 开放标准的能力扩展包，以 SKILL.md 为核心文件 |
| 渐进式发现 | Agent 不一次性加载所有 Skill，而是根据当前上下文动态匹配相关 Skill 的机制 |
| CUSTOM_TOOL | 原 TOOL 节点重命名后的名称，用于在画布上定义本地 Python 函数 |
| ROUTER | 原 CONDITION 节点重命名并升级后的名称，支持多路分支路由（替代 True/False 二元分支） |
| ToolExecutor | 统一的工具执行器，处理 CUSTOM_TOOL、MCP、Skill 三种来源的工具调用 |
| Discovery Engine | Skill 发现引擎，负责根据上下文匹配相关 Skill |

## 附录 B：参考资料

- [MCP 规范](https://spec.modelcontextprotocol.io/)
- [AI Agent Skill 开放标准目录结构](#)（本文档第 5.1 节）
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
