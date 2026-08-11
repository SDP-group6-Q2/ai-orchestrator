"""Compatibility node wrapper around the class-based synthesizer."""

from langchain.chat_models import BaseChatModel

from src.agents import SynthesizerAgent
from src.state import GraphState


def make_synthetizer_node(llm: BaseChatModel):
    synthesizer = SynthesizerAgent(llm)

    def synthetizer_node(state: GraphState) -> GraphState:
        return synthesizer.run(state)

    return synthetizer_node

