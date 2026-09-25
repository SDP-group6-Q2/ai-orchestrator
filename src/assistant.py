"""Assistant entry points: `ask` / `run` over the agent.

Async, because the agent's tools (MCP calls) are. The agent is built once per process, on first use, after the
MCP tools have been loaded.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any, TypedDict

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from src.agent import build_agent
from src.context import AgentContext
from src.mcp_client import load_tools
from src.trace import TraceEntry, extract_trace, render_trace_context

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


def _context_message(machine_id: str | None, history: list[HistoryTurn]) -> SystemMessage:
    if machine_id:
        text = (
            f"Current machine_id: {machine_id}. Pass this machine_id to any tool that needs one, "
            "unless the user asks about a different machine."
        )
    else:
        text = "No machine is in scope for this conversation."
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
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
        context=AgentContext(machine_id=machine_id, visibility=visibility, token=token),
    )


async def ask(
    question: str,
    machine_id: str | None,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> AskResult:
    state = await run(question, machine_id, visibility, token, history=history)
    return AskResult(answer=state["messages"][-1].content, trace=extract_trace(state["messages"]))
