"""Pydantic models for the /orchestrate API contract."""

from typing import Optional

from pydantic import BaseModel, Field


class OrchestrateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str
    machine_id: str
    session_id: str


class OrchestrateResponse(BaseModel):
    session_id: str
    response: str
    error: Optional[str] = None
