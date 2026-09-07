"""Shared state typing for the FleetAssistant orchestration flow."""

from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: Annotated[str, "The intent of the user query, between technical and commercial"]
