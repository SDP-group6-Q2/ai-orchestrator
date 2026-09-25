"""Assistant entry points: `ask` / `run` over the agent.

Async, because the agent's tools (MCP calls) are. The agent is built once per process, on first use, after the
MCP tools have been loaded.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, TypedDict

import ollama
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from src.agent import build_agent
from src.context import AgentContext
from src.mcp_client import load_tools
from src.trace import TraceEntry, extract_trace, render_trace_context

logger = logging.getLogger(__name__)

# Older messages are dropped: the caller (the backend) keeps the whole conversation, the model needs a window.
MAX_HISTORY_MESSAGES = 20


class HistoryTurn(TypedDict, total=False):
    role: str  # "user" | "assistant"
    content: str
    trace: list[TraceEntry]  # tools an assistant turn called (see src.trace)


@dataclass
class AskResult:
    answer: str
    trace: list[TraceEntry]  # this turn's tool calls, for the caller to store and send back in `history`


def _history_to_messages(history: list[HistoryTurn]) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


_agent = None
_agent_lock = asyncio.Lock()


async def get_agent():
    """Build the agent once per process. Model settings come from LLAMA_MODEL / LLAMA_BASE_URL.

    Raises McpUnavailableError if the MCP server's tools can't be loaded; the next call retries."""
    global _agent
    async with _agent_lock:
        if _agent is None:
            tools = await load_tools()
            llm = ChatOllama(
                model=os.getenv("LLAMA_MODEL", "gpt-oss:20b-cloud"),
                base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434"),
            )
            _agent = build_agent(llm=llm, tools=tools, checkpointer=InMemorySaver())
        return _agent


# The model writes ids and names with typographic hyphens (MCH‑0001, U+2011) whatever the prompt says. They break
# copy/paste, search and id matching, so they are turned back into ASCII hyphens after the fact.
_TYPOGRAPHIC_HYPHEN_IN_ID = re.compile(r"\b([A-Z]{2,5})[\u2010-\u2015](?=\d)")
_TYPOGRAPHIC_HYPHEN_INSIDE_WORD = re.compile(r"(?<=[A-Za-z0-9])[\u2010\u2011\u2012](?=[A-Za-z0-9])")


def normalize_answer(text: str) -> str:
    text = _TYPOGRAPHIC_HYPHEN_IN_ID.sub(r"\1-", text)
    return _TYPOGRAPHIC_HYPHEN_INSIDE_WORD.sub("-", text)


def _context_message(machine_id: str | None, history: list[HistoryTurn]) -> SystemMessage:
    if machine_id:
        text = (
            f"Current machine_id: {machine_id}. Pass this machine_id to any tool that needs one, "
            "unless the user asks about a different machine."
        )
    else:
        text = "No machine is in scope for this conversation."
    text += " Reply in English."
    earlier = render_trace_context(history)  # type: ignore[arg-type]
    return SystemMessage(content=f"{text}\n\n{earlier}" if earlier else text)


async def run(
    question: str,
    machine_id: str | None,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> dict[str, Any]:
    """Run one request and return the agent's final state. `token` is the end user's JWT: it is forwarded to
    the MCP server on every tool call (never shown to the model), and `visibility` is their tier, which decides
    which tools and skills the model gets."""
    history = (history or [])[-MAX_HISTORY_MESSAGES:]
    agent = await get_agent()
    return await agent.ainvoke(
        {
            "messages": [
                _context_message(machine_id, history),
                *_history_to_messages(history),
                HumanMessage(content=question),
            ],
        },  # type: ignore
        # The agent is shared across requests, so each call gets its own thread: reusing one would make the
        # checkpointer accumulate messages across requests. The caller owns history.
        config={
            "configurable": {"thread_id": str(uuid.uuid4())},
            # Labels for LangSmith traces (when enabled): searchable by tier, never by user, and never the token.
            "run_name": "assistant-chat",
            "tags": [f"tier:{visibility}"],
            "metadata": {
                "visibility": visibility,
                "machine_in_scope": bool(machine_id),
                "history_messages": len(history),
            },
        },
        context=AgentContext(machine_id=machine_id, visibility=visibility, token=SecretStr(token)),
    )


async def ask(
    question: str,
    machine_id: str | None,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> AskResult:
    for attempt in (1, 2):
        try:
            state = await run(question, machine_id, visibility, token, history=history)
            break
        except ollama.ResponseError as error:
            # The hosted model service sometimes fails transiently (5xx). Every tool is a read-only lookup, so
            # running the request again is safe; anything else (or a second failure) is the caller's to handle.
            if attempt == 2 or error.status_code < 500:
                raise
            logger.warning("Language model returned %s; retrying once", error.status_code)
    return AskResult(answer=normalize_answer(state["messages"][-1].content), trace=extract_trace(state["messages"]))
