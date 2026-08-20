"""Shared state typing for the FleetAssistant orchestration flow."""

from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class CallerInfo(TypedDict):
    user_id: str
    machine_id: int

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user: Annotated[CallerInfo, "The user information of the person interacting with the FleetAssistant"]
    intent: Annotated[str, "The intent of the user query, between technical and commercial"]
