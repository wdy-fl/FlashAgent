# tool_executor.py

from typing import Dict, Any

from langchain_core.tools import BaseTool


class ToolExecutor:
    """Unified tool execution entry point for custom tools."""

    def __init__(self, username: str, tools: Dict[str, BaseTool]):
        self._username = username
        self._tools = tools

    def get_bound_tools(self, tool_ids: list[str]) -> list[BaseTool]:
        """Get BaseTool instances for the specified tool IDs, for use with llm.bind_tools()."""
        tools = []
        for tid in tool_ids:
            if tid in self._tools:
                tools.append(self._tools[tid])
        return tools

    def execute(self, tool_id: str, args: Any) -> Any:
        """Execute a custom tool by name."""
        if tool_id not in self._tools:
            raise ValueError(f"Custom tool '{tool_id}' not found in registry")
        tool = self._tools[tool_id]
        if isinstance(args, dict):
            return tool.invoke(args)
        else:
            return tool.invoke({"input": args})
