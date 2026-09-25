"""Assistant entry points: `ask` / `run` over the LangGraph orchestration graph.

Async, because the agents' tools (MCP calls) are. The graph is built once per process, on first use, after
the MCP tools have been loaded.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import TypedDict, cast

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from src.context import AgentContext
from src.graph import build_graph
from src.mcp_client import load_tools
from src.state import GraphState


class HistoryTurn(TypedDict):
    role: str  # "user" | "assistant"
    content: str


def _history_to_messages(history: list[HistoryTurn]) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


_graph = None
_graph_lock = asyncio.Lock()


async def get_graph():
    """Build the graph once per process. Model settings come from LLAMA_MODEL / LLAMA_BASE_URL.

    Raises McpUnavailableError if the MCP server's tools can't be loaded; the next call retries."""
    global _graph
    async with _graph_lock:
        if _graph is None:
            tools = await load_tools()
            llm = ChatOllama(
                model=os.getenv("LLAMA_MODEL", "gpt-oss:20b-cloud"),
                base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434"),
            )
            _graph = build_graph(llm=llm, checkpointer=InMemorySaver(), tools=tools)
        return _graph


async def run(
    question: str,
    machine_id: str,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> GraphState:
    """Run one request. `token` is the end user's JWT: it is forwarded to the MCP server on every tool
    call (never shown to the model), and `visibility` is their tier, used by the graph's up-front gate."""
    context_message = SystemMessage(
        content=(
            f"Current machine_id: {machine_id}. Pass this machine_id to any tool that needs one, "
            "unless the user asks about a different machine."
        )
    )
    prior_messages = _history_to_messages(history) if history else []
    graph = await get_graph()
    result = await graph.ainvoke(
        {
            "messages": [context_message, *prior_messages, HumanMessage(content=question)],
        },  # type: ignore
        # The graph is shared across requests, so each call gets its own thread: reusing one would make the
        # checkpointer accumulate messages across requests. The caller owns history.
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
        context=AgentContext(machine_id=machine_id, visibility=visibility, token=token),
    )
    return cast(GraphState, result)


async def ask(
    question: str,
    machine_id: str,
    visibility: str,
    token: str,
    history: list[HistoryTurn] | None = None,
) -> str:
    result = await run(question, machine_id, visibility, token, history=history)
    return result["messages"][-1].content
