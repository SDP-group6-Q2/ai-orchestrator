"""Compatibility node wrapper around the class-based synthesizer."""

from src.agents import SynthesizerAgent
from src.state import GraphState


def make_synthetizer_node(agent: SynthesizerAgent | None = None):
    synthesizer = agent or SynthesizerAgent()

    def synthetizer_node(state: GraphState) -> GraphState:
        return synthesizer.run(state)

    return synthetizer_node


synthetizer_node = make_synthetizer_node()
