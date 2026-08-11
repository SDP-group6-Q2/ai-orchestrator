"""Shared state for the FleetAssistant LangGraph flow."""

from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages, MessagesState


class AgentCallState(TypedDict):
    agent_name: str
    agent_request: str
    agent_response: str


class UserInfoState(TypedDict):
    user_id: int
    machine_id: int

class GraphState(TypedDict):
    user_info: UserInfoState
    messages: Annotated[list, add_messages]
    agent_calls: list[AgentCallState]
    next_node: str

