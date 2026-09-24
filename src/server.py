"""HTTP entry point: a single POST /chat endpoint over the assistant.

Run with: uvicorn src.server:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from src.assistant import ask

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="ai-orchestrator")


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    user_id: str
    machine_id: str
    history: list[HistoryTurn] = []


class ChatResponse(BaseModel):
    answer: str


# Plain `def` so FastAPI runs the blocking graph invocation in its threadpool.
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    answer = ask(
        request.question,
        request.user_id,
        request.machine_id,
        history=[turn.model_dump() for turn in request.history],  # type: ignore[arg-type]
    )
    return ChatResponse(answer=answer)
