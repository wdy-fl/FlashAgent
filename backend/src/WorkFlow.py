# WorkFlow.py

import json
from typing import Dict, List, TypedDict, Any, Annotated, Optional
import operator

from langgraph.graph import StateGraph, END, START
from langgraph.types import Command
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from NodeData import NodeData
from llm import get_llm, clip_history
from tool_executor import ToolExecutor
from util import logger

def escape_for_template(text: str) -> str:
    """Escape curly braces in user text so LangChain PromptTemplate treats them as literals."""
    return text.replace("{", "{{").replace("}", "}}")

def parse_nodes_from_json(graph_data: Dict[str, Any]) -> Dict[str, NodeData]:
    """
    Parses node data from a graph's JSON structure.

    Args:
        graph_data: A dictionary representing a graph.
    Returns:
        A dictionary of NodeData objects keyed by their unique IDs.
    """
    node_map = {}
    for node_data in graph_data.get("nodes", []):
        node = NodeData.from_dict(node_data)
        node_map[node.uniq_id] = node
    return node_map

def find_nodes_by_type(node_map: Dict[str, NodeData], node_type: str) -> List[NodeData]:
    return [node for node in node_map.values() if node.type == node_type]


def serialize_history(messages: list[BaseMessage]) -> str:
    """Serialize message history to a string for ROUTER prompt templates."""
    parts = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            parts.append(f"Human: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                tool_names = [tc["name"] for tc in msg.tool_calls]
                parts.append(f"AI (called tools: {tool_names}): {msg.content}")
            else:
                parts.append(f"AI: {msg.content}")
        elif isinstance(msg, ToolMessage):
            parts.append(f"Tool result: {msg.content}")
        elif isinstance(msg, SystemMessage):
            parts.append(f"System: {msg.content}")
    return "\n".join(parts)


class PipelineState(TypedDict):
    history: Annotated[list[BaseMessage], operator.add]
    task: Annotated[str, operator.add]
    iteration_counts: Annotated[Dict[str, int], lambda x, y: {**x, **y}]
    human_input: Annotated[str, lambda x, y: y]


def llm_node(name: str, state: PipelineState, system_prompt: str, llm) -> dict:
    """LLM node without tools — invoke LLM and return AIMessage."""
    logger(f"{name} is working...")
    messages = clip_history(state["history"])
    system_msg = SystemMessage(content=system_prompt)
    ai_message = llm.invoke([system_msg] + messages)
    return {"history": [ai_message]}


def llm_with_tools_node(name: str, state: PipelineState, system_prompt: str, llm,
                        bound_tools: list, tool_node_id: str, downstream_ids: list) -> Command:
    """LLM node with tools — uses native tool calling, routes via Command."""
    logger(f"{name} is working (with tools)...")
    messages = clip_history(state["history"])
    system_msg = SystemMessage(content=system_prompt)
    llm_with_tools = llm.bind_tools(bound_tools)
    ai_message = llm_with_tools.invoke([system_msg] + messages)

    update = {"history": [ai_message]}

    if ai_message.tool_calls:
        tool_names = [tc["name"] for tc in ai_message.tool_calls]
        logger(f"{name}: requesting tools: {tool_names}")
        return Command(goto=tool_node_id, update=update)
    else:
        if downstream_ids:
            return Command(goto=downstream_ids, update=update)
        else:
            return Command(goto=END, update=update)


def tool_execution_node(name: str, state: PipelineState, executor: ToolExecutor,
                        llm_node_id: str) -> Command:
    """Execute tool calls from the last AIMessage and route back to LLM node."""
    last_message = state["history"][-1]
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        try:
            result = executor.execute(tool_name, args)
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
        except Exception as e:
            tool_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"]))

    logger(f"Executed tools: {[tc['name'] for tc in last_message.tool_calls]}")
    return Command(goto=llm_node_id, update={"history": tool_messages})


def router_switch(name: str, state: PipelineState, prompt_template: str, llm,
                  branch_mapping: Dict[str, str], max_iterations: int = 0) -> Command:
    logger(f"{name} is working (router)...")
    branch_labels = list(branch_mapping.keys())

    # Check iteration limit
    counts = state.get("iteration_counts", {})
    current_count = counts.get(name, 0) + 1

    if max_iterations > 0 and current_count >= max_iterations:
        switch_val = branch_labels[0]
        logger(f"Router {name}: max iterations ({max_iterations}) reached, forcing '{switch_val}'")
        return Command(
            goto=branch_mapping[switch_val],
            update={
                "history": [AIMessage(content=f"Router {name}: max iterations reached, chose: {switch_val}")],
                "iteration_counts": {name: current_count},
            }
        )

    # Serialize message history for ROUTER's JSON-mode prompt
    messages = clip_history(state["history"])
    history_str = serialize_history(messages)

    prompt = PromptTemplate.from_template(prompt_template)
    llm_chain = prompt | llm | StrOutputParser()
    generation = llm_chain.invoke({"history": history_str})
    data = json.loads(generation)

    switch_val = str(data["switch"])
    # Validate against available branches
    if switch_val not in branch_labels:
        logger(f"Router {name}: invalid switch '{switch_val}', defaulting to '{branch_labels[0]}'")
        switch_val = branch_labels[0]

    return Command(
        goto=branch_mapping[switch_val],
        update={
            "history": [AIMessage(content=f"Router chose: {switch_val}")],
            "iteration_counts": {name: current_count},
        }
    )


def info_add(name: str, state: PipelineState, information: str, llm) -> dict:
    logger(f"{name} is adding information...")
    return {"history": [HumanMessage(content=information)]}


def human_input_node(name: str, state: PipelineState, input_hint: str) -> dict:
    """
    HUMAN_INPUT node execution function.

    By the time this function runs, the workflow has already been interrupted
    (via interrupt_before), the user has submitted input, and update_state
    has injected it into state["human_input"]. This function simply consumes
    the input and records it in history.

    All HUMAN_INPUT nodes are mandatory. Empty input validation is handled
    upstream in resume() — empty input causes re-request rather than
    termination, preserving workflow progress.

    Returns an incremental dict (not the full state) because LangGraph uses
    Annotated reducers to merge — returning the full state would cause
    operator.add fields like history to be appended twice.
    """
    user_input = state.get("human_input", "")
    logger(f"{name} received input: {user_input}")

    return {
        "history": [HumanMessage(content=f"[Human Input - {name}]: {user_input}")],
        "human_input": ""  # Clear after consumption
    }


def build_graph(node_map: Dict[str, NodeData], llm, username: str = "default",
                checkpointer=None, tools: Dict[str, BaseTool] = None):
    """Build the LangGraph state machine.

    Returns (compiled_graph, sub_node_map) where sub_node_map maps
    internal sub-node IDs (e.g., "{id}_llm", "{id}_tools") back to
    the user-visible node ID.
    """
    # Define the state machine
    graph = StateGraph(PipelineState)
    sub_node_map: Dict[str, str] = {}

    # Create ToolExecutor for this build
    executor = ToolExecutor(username, tools or {})

    # Helper: map user node ID to graph sub-node ID
    def graph_id(nid):
        node = node_map.get(nid)
        if node and node.type == "LLM":
            return f"{nid}_llm"
        return nid

    # Start node, only one start point
    start_node = find_nodes_by_type(node_map, "START")[0]
    logger(f"Start root ID: {start_node.uniq_id}")

    # Pre-compute downstream graph IDs for each LLM node
    llm_nodes = find_nodes_by_type(node_map, "LLM")
    llm_downstream = {}
    for current_node in llm_nodes:
        llm_downstream[current_node.uniq_id] = [graph_id(nid) for nid in current_node.nexts]

    # LLM nodes
    for current_node in llm_nodes:
        llm_sub_id = f"{current_node.uniq_id}_llm"
        sub_node_map[llm_sub_id] = current_node.uniq_id
        node_tools_ids = list(current_node.tools)
        downstream_ids = llm_downstream[current_node.uniq_id]

        if node_tools_ids:
            # LLM with tools: create llm + tools sub-nodes
            tool_sub_id = f"{current_node.uniq_id}_tools"
            sub_node_map[tool_sub_id] = current_node.uniq_id

            bound_tools = executor.get_bound_tools(node_tools_ids)
            system_prompt = f"You are {escape_for_template(current_node.name)}. {escape_for_template(current_node.description)}"

            graph.add_node(
                llm_sub_id,
                lambda state, name=current_node.name, sp=system_prompt, l=llm,
                       bt=bound_tools, tid=tool_sub_id, ds=downstream_ids:
                    llm_with_tools_node(name, state, sp, l, bt, tid, ds)
            )
            graph.add_node(
                tool_sub_id,
                lambda state, name=current_node.name, ex=executor, lid=llm_sub_id:
                    tool_execution_node(name, state, ex, lid)
            )
            # Routing handled by Command — no regular edges from these sub-nodes
        else:
            # LLM without tools
            system_prompt = current_node.description
            graph.add_node(
                llm_sub_id,
                lambda state, name=current_node.name, sp=system_prompt, l=llm:
                    llm_node(name, state, sp, l)
            )
            # Regular edges to downstreams
            if downstream_ids:
                for ds_id in downstream_ids:
                    graph.add_edge(llm_sub_id, ds_id)
            else:
                graph.add_edge(llm_sub_id, END)

    # Add INFO nodes
    info_nodes = find_nodes_by_type(node_map, "INFO")
    for info_node in info_nodes:
        graph.add_node(
            info_node.uniq_id,
            lambda state, template=info_node.description, llm=llm, name=info_node.name: info_add(name, state, template, llm)
        )
        downstream_ids = [graph_id(nid) for nid in info_node.nexts]
        if downstream_ids:
            for ds_id in downstream_ids:
                graph.add_edge(info_node.uniq_id, ds_id)
        else:
            graph.add_edge(info_node.uniq_id, END)

    # Add HUMAN_INPUT nodes
    human_nodes = find_nodes_by_type(node_map, "HUMAN_INPUT")
    interrupt_node_ids = []
    for h_node in human_nodes:
        h_input_schema = h_node.input_schema or {}
        graph.add_node(
            h_node.uniq_id,
            lambda state, name=h_node.name,
                   input_hint=h_input_schema.get("input_hint", "Please provide input"):
                human_input_node(name, state, input_hint)
        )
        interrupt_node_ids.append(h_node.uniq_id)
        downstream_ids = [graph_id(nid) for nid in h_node.nexts]
        if downstream_ids:
            for ds_id in downstream_ids:
                graph.add_edge(h_node.uniq_id, ds_id)
        else:
            graph.add_edge(h_node.uniq_id, END)

    # START edges
    for next_id in start_node.nexts:
        graph.add_edge(START, graph_id(next_id))

    # Find all router nodes
    router_nodes = find_nodes_by_type(node_map, "ROUTER")
    for router in router_nodes:
        # Build branch mapping: label → target sub-node ID or END
        branch_mapping = {}
        for label, target_id in (router.branches or {}).items():
            branch_mapping[label] = graph_id(target_id) if target_id else END

        branch_labels = list(branch_mapping.keys()) if branch_mapping else ["True", "False"]
        router_template = f"""{escape_for_template(router.description)}
        history: {{history}}
        Available branches: {branch_labels}
        Respond in JSON: {{{{"switch": "<branch_label>"}}}}
        """
        graph.add_node(
            router.uniq_id,
            lambda state, template=router_template, llm=llm, name=router.name,
                   mapping=branch_mapping, max_iter=router.max_iterations:
                router_switch(name, state, template, llm, mapping, max_iter)
        )

        logger(f"{router.name} {router.uniq_id}'s router branches: {branch_mapping}")

    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_node_ids:
        compile_kwargs["interrupt_before"] = interrupt_node_ids

    return graph.compile(**compile_kwargs), sub_node_map
