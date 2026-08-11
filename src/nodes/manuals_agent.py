"""Compatibility node wrapper around the class-based manuals agent."""

from src.agents import ManualsAgent
from src.state import GraphState

from langchain_core.language_models import BaseChatModel

def make_manuals_agent_node(llm: BaseChatModel):
    manuals_agent = ManualsAgent(llm)

    def manuals_agent_node(state: GraphState) -> GraphState:
        return manuals_agent.run(state)

    return manuals_agent_node

