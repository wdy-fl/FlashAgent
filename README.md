# FlashAgent

FlashAgent 是一个面向 LLM 应用的可视化节点式工作流构建器。通过拖拽和连接画布上的节点来设计工作流，并支持人机协同（Human-in-the-Loop）执行。

## 功能特性

- **可视化工作流编辑器** — 基于 SvelteFlow 的拖拽式节点画布
- **5 种节点类型** — START、LLM、ROUTER（多分支路由，LangGraph Command）、INFO、HUMAN_INPUT
- **人机协同** — HUMAN_INPUT 节点暂停执行等待用户输入（文本/确认/选择）
- **原生工具调用** — 自定义 Python 工具通过 LangChain `@tool` 装饰器注册，LLM 节点使用 `bind_tools()` 实现原生 tool calling
- **DeepSeek LLM** — 支持 DeepSeek 系列模型（OpenAI 兼容接口）
- **多用户隔离** — 每个用户拥有独立的工作区、工作流和工具
- **WebSocket 流式输出** — 实时执行输出，支持暂停/恢复/停止
- **侧边栏执行面板** — 工作流运行结果以结构化卡片呈现，支持实时交互

## 环境要求

- Node.js（前端）
- Python 3.12（后端）
- DeepSeek API Key

## 快速开始

### 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 5000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

两个服务均启动后，访问 [http://localhost:3000](http://localhost:3000) 即可使用。

## 架构

```
浏览器 (SvelteKit) ──HTTP/WebSocket──► FastAPI ──► DeepSeek API
                                          │
                                    LangGraph StateGraph
                                    MemorySaver 检查点
                                    ToolExecutor (自定义工具 @tool)
                                    原生 tool calling (bind_tools)
```

## 节点类型

| 类型 | 说明 |
|------|------|
| START | 入口节点，初始化工作流状态 |
| LLM | LLM 提示执行，可选绑定工具（原生 tool calling） |
| ROUTER | 多分支路由（使用 LangGraph `Command(goto=...)`），支持最大迭代次数限制 |
| INFO | 仅展示信息的节点 |
| HUMAN_INPUT | 暂停执行等待用户输入（文本/确认/选择） |

## 联系与贡献

如有建议、Bug 反馈或任何问题，请使用 [讨论区](https://github.com/LangGraph-GUI/LangGraph-GUI/discussions) 或 [Issue](https://github.com/LangGraph-GUI/LangGraph-GUI/issues)。

## 许可证

本项目基于 MIT 许可证发布，详见 [LICENSE](LICENSE) 文件。
