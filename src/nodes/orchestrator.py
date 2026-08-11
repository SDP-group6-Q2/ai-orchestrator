"""Compatibility node wrapper around the class-based orchestrator."""

from langchain.chat_models import BaseChatModel

from src.agents import FleetOrchestrator
from src.state import GraphState


def make_orchestrator_node(llm: BaseChatModel):
    orchestrator = FleetOrchestrator(llm)

    def orchestrator_node(state: GraphState) -> GraphState:
        return orchestrator.run(state)

    return orchestrator_node
