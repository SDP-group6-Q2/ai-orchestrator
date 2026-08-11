"""Compatibility node wrapper around the class-based IoT agent."""

from langchain_core.language_models import BaseChatModel

from src.agents import IotAgent
from src.state import GraphState


def make_iot_agent_node(llm: BaseChatModel):
    iot_agent = IotAgent(llm)

    def iot_agent_node(state: GraphState) -> GraphState:
        return iot_agent.run(state)

    return iot_agent_node
