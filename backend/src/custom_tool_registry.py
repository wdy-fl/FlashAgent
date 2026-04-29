# custom_tool_registry.py

import json
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from langchain_core.tools import BaseTool, tool as lc_tool

from util import logger


@dataclass
class CustomToolMeta:
    """Metadata for a custom tool."""
    name: str
    description: str = ""
    code: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class CustomToolRegistry:
    """Manages custom tools for a given user.

    Tools are stored at: workspace/{username}/custom_tools/
    Each tool is a JSON file: {tool_name}.json
    """

    def __init__(self, username: str, base_dir: Optional[str] = None):
        self._username = username
        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path(f"workspace/{username}/custom_tools")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._tools: Dict[str, CustomToolMeta] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan the custom_tools directory and load all tool metadata."""
        self._tools.clear()
        if not self._base_dir.exists():
            return
        for json_file in self._base_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = CustomToolMeta(
                    name=data.get("name", json_file.stem),
                    description=data.get("description", ""),
                    code=data.get("code", "")
                )
                self._tools[meta.name] = meta
                logger(f"Loaded custom tool: {meta.name}")
            except (json.JSONDecodeError, KeyError) as e:
                logger(f"Error loading custom tool {json_file.name}: {e}")

    def _sanitize_name(self, name: str) -> str:
        return re.sub(r'[^\w\-]', '_', name)

    def _save_tool(self, meta: CustomToolMeta) -> None:
        filename = self._sanitize_name(meta.name) + ".json"
        filepath = self._base_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False)

    def list_tools(self) -> List[CustomToolMeta]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[CustomToolMeta]:
        return self._tools.get(name)

    def add_tool(self, name: str, description: str, code: str) -> CustomToolMeta:
        meta = CustomToolMeta(name=name, description=description, code=code)
        self._tools[name] = meta
        self._save_tool(meta)
        logger(f"Added custom tool: {name}")
        return meta

    def update_tool(self, name: str, description: str, code: str) -> Optional[CustomToolMeta]:
        if name not in self._tools:
            return None
        meta = CustomToolMeta(name=name, description=description, code=code)
        self._tools[name] = meta
        self._save_tool(meta)
        logger(f"Updated custom tool: {name}")
        return meta

    def remove_tool(self, name: str) -> bool:
        if name not in self._tools:
            return False
        del self._tools[name]
        filename = self._sanitize_name(name) + ".json"
        filepath = self._base_dir / filename
        if filepath.exists():
            filepath.unlink()
        logger(f"Removed custom tool: {name}")
        return True

    def register_all(self) -> Dict[str, BaseTool]:
        """Register all custom tools via exec() using LangChain @tool decorator.

        Returns a dict mapping tool_name → BaseTool instances.
        """
        tools: Dict[str, BaseTool] = {}
        for meta in self._tools.values():
            try:
                namespace = {
                    "__builtins__": __builtins__,
                    "tool": lc_tool,
                }
                exec(meta.code, namespace)
                # Collect BaseTool instances created by @tool decorator
                for obj in namespace.values():
                    if isinstance(obj, BaseTool):
                        tools[obj.name] = obj
                logger(f"Registered custom tool code: {meta.name}")
            except Exception as e:
                logger(f"Error registering custom tool {meta.name}: {e}")
        return tools


# Per-user singleton instances
_registries: Dict[str, CustomToolRegistry] = {}


def get_custom_tool_registry(username: str, base_dir: Optional[str] = None) -> CustomToolRegistry:
    """Get or create the CustomToolRegistry for a user."""
    cache_key = base_dir or username
    if cache_key not in _registries:
        _registries[cache_key] = CustomToolRegistry(username, base_dir)
    return _registries[cache_key]
