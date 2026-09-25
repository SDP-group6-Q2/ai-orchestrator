"""HTTP entry point: a single POST /chat endpoint over the assistant.

Run with: uvicorn src.server:app --host 0.0.0.0 --port 8001

The caller (the backend) sends the end user's JWT as `Authorization: Bearer <token>`. It is forwarded to the
MCP server on every tool call, so the platform's access rules apply to that user; this service never sees
credentials of its own.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.assistant import ask
from src.mcp_client import McpUnavailableError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="ai-orchestrator")


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    machine_id: str
    visibility: Literal["full", "technician", "commercial"]
    history: list[HistoryTurn] = []


class ChatResponse(BaseModel):
    answer: str


def _bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return token.strip()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    token = _bearer_token(authorization)
    try:
        answer = await ask(
            request.question,
            request.machine_id,
            request.visibility,
            token,
            history=[turn.model_dump() for turn in request.history],  # type: ignore[arg-type]
        )
    except McpUnavailableError as error:
        raise HTTPException(status_code=503, detail="The data tools are temporarily unavailable.") from error
    return ChatResponse(answer=answer)
