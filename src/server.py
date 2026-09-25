"""HTTP entry point: a single POST /chat endpoint over the assistant.

Run with: uvicorn src.server:app --host 0.0.0.0 --port 8001

The caller (the backend) sends the end user's JWT as `Authorization: Bearer <token>`. It is forwarded to the
MCP server on every tool call, so the platform's access rules apply to that user; this service never sees
credentials of its own.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import ollama
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.assistant import ask
from src.mcp_client import McpUnavailableError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

app = FastAPI(title="ai-orchestrator")


class TraceEntry(BaseModel):
    tool: str
    args: dict[str, Any] = {}
    summary: str = ""
    error: bool = False


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    trace: list[TraceEntry] | None = None  # what an earlier assistant turn retrieved


class ChatRequest(BaseModel):
    question: str
    machine_id: str
    visibility: Literal["full", "technician", "commercial"]
    history: list[HistoryTurn] = []


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEntry] = []  # this turn's tool calls: store it with the answer, send it back in `history`


def _bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return token.strip()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    token = _bearer_token(authorization)
    try:
        result = await ask(
            request.question,
            request.machine_id,
            request.visibility,
            token,
            history=[turn.model_dump(exclude_none=True) for turn in request.history],  # type: ignore[misc]
        )
    except McpUnavailableError as error:
        raise HTTPException(status_code=503, detail="The data tools are temporarily unavailable.") from error
    except (ollama.ResponseError, ConnectionError) as error:
        # The language model service failed or is unreachable: not our bug, and worth retrying.
        logger.exception("Language model call failed")
        raise HTTPException(status_code=502, detail="The language model is temporarily unavailable.") from error
    return ChatResponse(answer=result.answer, trace=result.trace)  # type: ignore[arg-type]
