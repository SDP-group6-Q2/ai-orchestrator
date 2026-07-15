"""Compatibility node wrapper around the class-based manuals agent."""

from FleetAssistant.agents import ManualsAgent
from FleetAssistant.state import GraphState


def make_manuals_agent_node(agent: ManualsAgent | None = None):
    manuals_agent = agent or ManualsAgent()

    def manuals_agent_node(state: GraphState) -> GraphState:
        return manuals_agent.run(state)

    return manuals_agent_node


manuals_agent_node = make_manuals_agent_node()
