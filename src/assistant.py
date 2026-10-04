"""Assistant entry points: `ask` / `run` over the agent.

Async, because the agent's tools (MCP calls) are. The agent is built once per process, on first use, after the
MCP tools have been loaded.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, TypedDict

import anthropic
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from src.agent import build_agent
from src.context import AgentContext
from src.mcp_client import load_tools
from src.trace import TraceEntry, _text, extract_trace, render_trace_context

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
    """Build the agent once per process. The model is ANTHROPIC_MODEL (default claude-opus-5-5); the API key is
    read from ANTHROPIC_API_KEY by the Anthropic SDK.

    Raises McpUnavailableError if the MCP server's tools can't be loaded; the next call retries."""
    global _agent
    async with _agent_lock:
        if _agent is None:
            tools = await load_tools()
            llm = ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
                max_tokens=16000,  # the default (1024) cuts off long answers
                # One retry is done in _retrying, so the SDK's own retries are turned off to avoid stacking them.
                max_retries=0,
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
    messages = [_context_message(machine_id, history), *_history_to_messages(history), HumanMessage(content=question)]
    return await _invoke(messages, machine_id, visibility, token, history_messages=len(history))


async def _invoke(
    messages: list[BaseMessage],
    machine_id: str | None,
    visibility: str,
    token: str,
    history_messages: int,
) -> dict[str, Any]:
    agent = await get_agent()
    return await agent.ainvoke(
        {"messages": messages},  # type: ignore
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
                "history_messages": history_messages,
            },
        },
        context=AgentContext(machine_id=machine_id, visibility=visibility, token=SecretStr(token)),
    )


def _is_transient(error: anthropic.APIError) -> bool:
    # A 5xx, or the connection to the API failing (or timing out) before an answer came back.
    if isinstance(error, anthropic.APIConnectionError):
        return True
    return isinstance(error, anthropic.APIStatusError) and error.status_code >= 500


async def _retrying(call):
    """Await `call()`, running it once more if the Claude API fails transiently. Every tool is a read-only lookup,
    so running again is safe; anything else (or a second failure) is the caller's to handle."""
    for attempt in (1, 2):
        try:
            return await call()
        except anthropic.APIError as error:
            if attempt == 2 or not _is_transient(error):
                raise
            logger.warning("Language model call failed (%s); retrying once", error)


def _is_answer(message: BaseMessage) -> bool:
    """False when the model stopped without a usable answer: an empty message, or the arguments of the tool call
    it meant to make next written out as plain JSON (a model can do this mid-chain; the agent then sees no tool
    call and stops)."""
    text = _text(message.content).strip()
    if not text:
        return False
    try:
        return not isinstance(json.loads(text), (dict, list))
    except ValueError:
        return True


_CONTINUE = SystemMessage(
    content="Your last reply reached the user empty or as raw JSON. Continue: if you need more data, call the "
    "tool through a proper tool call; otherwise write the answer to the user's question now."
)
FALLBACK_ANSWER = (
    "Sorry, I couldn't put an answer together this time. Please try again, or split the question into smaller ones."
)


async def ask(
    question: str,
    machine_id: str | None,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> AskResult:
    state = await _retrying(lambda: run(question, machine_id, visibility, token, history=history))
    messages = state["messages"]
    if not _is_answer(messages[-1]):
        # Continue the same turn once, without the broken message, so the tools already called aren't repeated.
        logger.warning("Model stopped without an answer (%r); asking it to continue", _text(messages[-1].content)[:80])
        retry_messages = [*messages[:-1], _CONTINUE]
        history_messages = len((history or [])[-MAX_HISTORY_MESSAGES:])
        state = await _retrying(lambda: _invoke(retry_messages, machine_id, visibility, token, history_messages))
        messages = state["messages"]
    answer = normalize_answer(_text(messages[-1].content)) if _is_answer(messages[-1]) else FALLBACK_ANSWER
    return AskResult(answer=answer, trace=extract_trace(messages))
