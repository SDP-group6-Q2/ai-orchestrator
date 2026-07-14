"""Shared state passed through the LangGraph orchestration graph."""

from typing import Any, Optional, TypedDict


class Citation(TypedDict):
    source: str
    snippet: str


class OrchestratorState(TypedDict, total=False):
    # Request context
    message: str
    user_id: str
    customer_id: str
    machine_id: Optional[str]
    session_id: str

    # Routing
    intent: str
    selected_agent: str

    # Result
    answer: str
    citations: list[Citation]
    error: Optional[str]

    # Free-form scratch space for agents (kept out of the API contract)
    metadata: dict[str, Any]
