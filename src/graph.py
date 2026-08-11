"""LangGraph wiring for the FleetAssistant local orchestration flow."""

from langchain.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import InMemorySaver

from src.agents import (
    FleetOrchestrator,
    IotAgent,
    ManualsAgent,
    OrdersAgent,
    ServiceAgent,
    SynthesizerAgent,
)
from src.nodes import (
    make_iot_agent_node,
    make_manuals_agent_node,
    make_orchestrator_node,
    make_orders_agent_node,
    make_service_agent_node,
    make_synthetizer_node,
)
from src.state import GraphState

def build_graph(llm: BaseChatModel, checkpointer: InMemorySaver):
    if not checkpointer:
        raise ValueError("A checkpointer must be provided to build the graph.")


    builder = StateGraph(GraphState)

    builder.add_node("orchestrator", make_orchestrator_node(FleetOrchestrator(llm=llm)))
    builder.add_node("manuals_agent", make_manuals_agent_node(ManualsAgent(llm=llm)))
    builder.add_node("iot_agent", make_iot_agent_node(IotAgent(llm=llm)))
    builder.add_node("orders_agent", make_orders_agent_node(OrdersAgent(llm=llm)))
    builder.add_node("service_agent", make_service_agent_node(ServiceAgent(llm=llm)))
    builder.add_node("synthetizer", make_synthetizer_node(SynthesizerAgent(llm=llm)))

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        lambda state: state["next_node"],
        {
            "manuals": "manuals_agent",
            "iot": "iot_agent",
            "orders": "orders_agent",
            "service": "service_agent",
            "finish": "synthetizer",
        },
    )
    builder.add_edge("manuals_agent", "orchestrator")
    builder.add_edge("iot_agent", "orchestrator")
    builder.add_edge("orders_agent", "orchestrator")
    builder.add_edge("service_agent", "orchestrator")
    builder.add_edge("synthetizer", END)

    return builder