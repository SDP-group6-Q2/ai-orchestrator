"""Graph wiring for the FleetAssistant orchestration flow."""

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.agents import make_supervisor_agent


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver):
    if not checkpointer:
        raise ValueError("A checkpointer must be provided to build the graph.")

    return make_supervisor_agent(llm, checkpointer=checkpointer)
