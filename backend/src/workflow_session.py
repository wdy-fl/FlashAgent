# workflow_session.py

import json
import os
from typing import AsyncIterator, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from WorkFlow import (
    PipelineState, build_graph, parse_nodes_from_json,
)
from custom_tool_registry import get_custom_tool_registry
from util import logger


class WorkflowSession:
    """
    Encapsulates a single workflow execution session with support for
    pause/resume/stop. Session lifecycle is independent of WebSocket
    connections — the session keeps running in the background if the
    frontend disconnects, and can be reconnected to later.

    Only single-graph workflows are supported.
    """

    def __init__(self, username: str, llm, thread_id: str, workflow_name: str):
        self.username = username
        self.llm = llm
        self.thread_id = thread_id
        self.workflow_name = workflow_name
        self.config = {"configurable": {"thread_id": thread_id}}
        self.graph = None

        # Sub-node ID → user-visible node ID mapping
        self.sub_node_map: Dict[str, str] = {}

        # Execution state
        self.is_running: bool = False
        self.is_waiting: bool = False
        self._cancelled: bool = False

        # Node config map (for looking up input_schema on interrupt)
        self.node_map: Dict = {}

        # Output history: for replaying on reconnect
        self.output_history: List[Dict] = []
        self._MAX_HISTORY = 1000

        self._build_graph()

    def _build_graph(self):
        """
        Load a saved workflow and build the graph.

        Reads from workspace/{username}/workflows/{workflow_name}.json.
        The file format is { name, nodes, updated_at } — a single workflow
        object, compatible with parse_nodes_from_json.

        MemorySaver checkpointer is created per-session and passed to
        build_graph so that interrupt_before can work correctly.
        """
        workspace = os.path.join("workspace", self.username)
        workflow_path = os.path.join(workspace, "workflows", f"{self.workflow_name}.json")

        with open(workflow_path, 'r') as f:
            data = json.load(f)

        # Register custom tools
        custom_tools_dir = os.path.join(workspace, "custom_tools")
        custom_registry = get_custom_tool_registry(self.username, base_dir=custom_tools_dir)
        tools = custom_registry.register_all()

        graph_data = data
        self.node_map = parse_nodes_from_json(graph_data)
        self.checkpointer = MemorySaver()
        self.graph, self.sub_node_map = build_graph(
            self.node_map, self.llm, self.username,
            checkpointer=self.checkpointer,
            tools=tools
        )

    def get_node_input_schema(self, node_id: str) -> dict:
        """Look up the input_schema of a HUMAN_INPUT node by its ID."""
        node = self.node_map.get(node_id)
        if not node:
            return {"input_hint": "Please provide input", "input_type": "text", "options": []}
        input_schema = getattr(node, 'input_schema', None)
        if not input_schema:
            return {"input_hint": "Please provide input", "input_type": "text", "options": []}
        return input_schema

    def _record(self, event: Dict) -> Dict:
        """Record an output event to history for reconnect replay."""
        self.output_history.append(event)
        if len(self.output_history) > self._MAX_HISTORY:
            self.output_history = self.output_history[-self._MAX_HISTORY:]
        return event

    def _check_interrupt(self) -> Optional[Dict]:
        """Check if the graph is paused at an interrupt point.
        Returns a waiting_for_input event or None."""
        snapshot = self.graph.get_state(self.config)
        if not self._cancelled and snapshot.next:
            self.is_waiting = True
            return self._record({
                "type": "waiting_for_input",
                "pending_node_id": snapshot.next[0]
            })
        else:
            self.is_running = False
            return None

    def _resolve_node_id(self, node_id: str) -> str:
        """Map internal sub-node ID back to user-visible node ID."""
        return self.sub_node_map.get(node_id, node_id)

    def _extract_content(self, node_type: str, delta: Dict) -> str:
        """Extract user-visible content from an updates delta.

        With message-list history, delta['history'] is a list of
        BaseMessage objects. We extract text and tool call info from them.
        """
        messages = delta.get("history", [])
        if not messages:
            return "(no output)"

        parts = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                if msg.content:
                    parts.append(msg.content)
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        args_str = json.dumps(tc["args"], ensure_ascii=False)
                        parts.append(f"Calling tool: {tc['name']}({args_str})")
            elif isinstance(msg, ToolMessage):
                parts.append(f"Tool result: {msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(msg.content)

        return "\n".join(parts) if parts else "(no output)"

    def _format_output_event(self, node_id: str, delta: Dict) -> Dict:
        """Build a structured output event, resolving sub-node IDs."""
        user_node_id = self._resolve_node_id(node_id)
        node = self.node_map.get(user_node_id)
        return self._record({
            "type": "output",
            "node_id": user_node_id,
            "node_name": node.name if node else user_node_id,
            "node_type": node.type if node else "UNKNOWN",
            "has_tools": bool(node.tools) if node else False,
            "content": self._extract_content(node.type if node else "UNKNOWN", delta),
        })

    async def run(self) -> AsyncIterator[Dict]:
        """
        Start workflow execution.

        Uses astream() with stream_mode="updates" to get per-node delta
        instead of full state dumps. Filters __interrupt__ events from
        LangGraph and yields structured output messages with node metadata.
        """
        self.is_running = True
        self._cancelled = False

        async for event in self.graph.astream(
            {
                "history": [],
                "task": "",
                "iteration_counts": {},
                "human_input": ""
            },
            self.config,
            stream_mode="updates"
        ):
            if self._cancelled:
                break
            for node_id, delta in event.items():
                if node_id == "__interrupt__":
                    continue
                yield self._format_output_event(node_id, delta)

        # Check if we paused at a HUMAN_INPUT interrupt
        waiting_event = self._check_interrupt()
        if waiting_event:
            yield waiting_event

    async def resume(self, user_input: str) -> AsyncIterator[Dict]:
        """
        Inject user input and resume execution after a HUMAN_INPUT interrupt.

        Empty input is not allowed — re-yields input_request so the frontend
        can prompt the user again, preserving workflow progress.
        """
        # Empty input validation: all HUMAN_INPUT nodes are mandatory
        if not user_input.strip():
            snapshot = self.graph.get_state(self.config)
            if snapshot.next:
                self.is_waiting = True
                yield self._record({
                    "type": "waiting_for_input",
                    "pending_node_id": snapshot.next[0]
                })
            return  # Stay paused, don't lose progress

        self.is_waiting = False

        self.graph.update_state(
            self.config,
            {"human_input": user_input}
        )

        async for event in self.graph.astream(None, self.config, stream_mode="updates"):
            if self._cancelled:
                break
            for node_id, delta in event.items():
                if node_id == "__interrupt__":
                    continue
                yield self._format_output_event(node_id, delta)

        # Check if we hit another interrupt
        waiting_event = self._check_interrupt()
        if waiting_event:
            yield waiting_event

    def cancel(self):
        """Cancel current execution (triggered by Stop button)."""
        self._cancelled = True
        self.is_running = False
        self.is_waiting = False
        self._record({"type": "stopped", "message": "Workflow stopped by user"})
