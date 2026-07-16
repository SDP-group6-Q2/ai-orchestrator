"""Compatibility node wrapper around the class-based orchestrator."""

from FleetAssistant.agents import FleetOrchestrator
from FleetAssistant.state import GraphState


def make_orchestrator_node(agent: FleetOrchestrator | None = None):
    orchestrator = agent or FleetOrchestrator()

    def orchestrator_node(state: GraphState) -> GraphState:
        return orchestrator.run(state)

    return orchestrator_node


orchestrator_node = make_orchestrator_node()
