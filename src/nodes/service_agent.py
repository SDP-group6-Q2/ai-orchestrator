"""Compatibility node wrapper around the class-based service agent."""

from langchain_core.language_models import BaseChatModel

from src.agents import ServiceAgent
from src.state import GraphState


def make_service_agent_node(llm: BaseChatModel):
    service_agent = ServiceAgent(llm)

    def service_agent_node(state: GraphState) -> GraphState:
        return service_agent.run(state)

    return service_agent_node