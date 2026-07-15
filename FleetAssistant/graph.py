"""LangGraph wiring for the FleetAssistant local orchestration flow."""

from langgraph.graph import END, StateGraph

from FleetAssistant.agents import FleetOrchestrator, IotAgent, ManualsAgent, SynthesizerAgent
from FleetAssistant.nodes import (
    make_iot_agent_node,
    make_manuals_agent_node,
    make_orchestrator_node,
    make_synthetizer_node,
)
from FleetAssistant.state import GraphState


def _route_from_orchestrator(state: GraphState) -> str:
    return state.get("next_node", "synthetizer")


def build_graph(model: str | None = None, base_url: str | None = None):
    builder = StateGraph(GraphState)

    builder.add_node("orchestrator", make_orchestrator_node(FleetOrchestrator(model=model, base_url=base_url)))
    builder.add_node("manuals_agent", make_manuals_agent_node(ManualsAgent(model=model, base_url=base_url)))
    builder.add_node("iot_agent", make_iot_agent_node(IotAgent(model=model, base_url=base_url)))
    builder.add_node("synthetizer", make_synthetizer_node(SynthesizerAgent(model=model, base_url=base_url)))

    builder.set_entry_point("orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "manuals_agent": "manuals_agent",
            "iot_agent": "iot_agent",
            "synthetizer": "synthetizer",
        },
    )
    builder.add_edge("manuals_agent", "orchestrator")
    builder.add_edge("iot_agent", "orchestrator")
    builder.add_edge("synthetizer", END)

    return builder.compile()


orchestrator_graph = build_graph()
