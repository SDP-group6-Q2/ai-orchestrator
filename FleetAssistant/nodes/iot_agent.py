"""Compatibility node wrapper around the class-based IoT agent."""

from FleetAssistant.agents import IotAgent
from FleetAssistant.state import GraphState


def make_iot_agent_node(agent: IotAgent | None = None):
    iot_agent = agent or IotAgent()

    def iot_agent_node(state: GraphState) -> GraphState:
        return iot_agent.run(state)

    return iot_agent_node


iot_agent_node = make_iot_agent_node()
