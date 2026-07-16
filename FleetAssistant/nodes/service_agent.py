"""Compatibility node wrapper around the class-based service agent."""

from FleetAssistant.agents import ServiceAgent
from FleetAssistant.state import GraphState


def make_service_agent_node(agent: ServiceAgent | None = None):
    service_agent = agent or ServiceAgent()

    def service_agent_node(state: GraphState) -> GraphState:
        return service_agent.run(state)

    return service_agent_node


service_agent_node = make_service_agent_node()
