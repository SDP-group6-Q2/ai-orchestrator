"""Pydantic models for the /orchestrate API contract."""

from typing import Optional

from pydantic import BaseModel, Field


class OrchestrateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str
    customer_id: str
    machine_id: Optional[str] = None
    session_id: str


class Citation(BaseModel):
    source: str
    snippet: str


class OrchestrateResponse(BaseModel):
    session_id: str
    intent: str
    selected_agent: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    error: Optional[str] = None
