"""LangGraph wiring: classify_intent -> conditional routing -> agent -> END."""

from langgraph.graph import END, StateGraph

from app.agents import (
    run_iot_agent,
    run_manuals_agent,
    run_orders_agent,
    run_service_agent,
    run_troubleshooting_agent,
)
from app.nodes import classify_intent
from app.state import OrchestratorState

_AGENT_NODES = {
    "manuals_agent": run_manuals_agent,
    "iot_agent": run_iot_agent,
    "orders_agent": run_orders_agent,
    "troubleshooting_agent": run_troubleshooting_agent,
    "service_agent": run_service_agent,
}


def _route_to_agent(state: OrchestratorState) -> str:
    return state["selected_agent"]


def build_graph():
    builder = StateGraph(OrchestratorState)

    builder.add_node("classify_intent", classify_intent)
    for name, agent_fn in _AGENT_NODES.items():
        builder.add_node(name, agent_fn)

    builder.set_entry_point("classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        _route_to_agent,
        {name: name for name in _AGENT_NODES},
    )
    for name in _AGENT_NODES:
        builder.add_edge(name, END)

    return builder.compile()


orchestrator_graph = build_graph()
