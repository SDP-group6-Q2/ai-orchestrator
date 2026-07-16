"""Shared state for the FleetAssistant LangGraph flow."""

from typing import TypedDict


class AgentCallState(TypedDict):
    agent_name: str
    agent_request: str
    agent_response: str


class UserInfoState(TypedDict):
    user_id: str
    machine_id: str


class PlanStep(TypedDict):
    next_node: str
    agent_request: str
    rationale: str


class GraphState(TypedDict):
    request: str
    user_info: UserInfoState
    agent_calls: list[AgentCallState]
    plan: list[PlanStep]
    current_step: int
    next_node: str
    response: str
    error: str | None

