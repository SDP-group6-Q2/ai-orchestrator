"""Assistant entry points: `ask` / `run` over the LangGraph orchestration graph."""

from __future__ import annotations

import os
import uuid
from functools import lru_cache
from typing import TypedDict, cast

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from src.context import AgentContext
from src.graph import build_graph
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


@lru_cache(maxsize=1)
def get_graph():
    """Build the graph once per process. Model settings come from LLAMA_MODEL / LLAMA_BASE_URL."""
    llm = ChatOllama(
        model=os.getenv("LLAMA_MODEL", "gpt-oss:20b-cloud"),
        base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434"),
    )
    return build_graph(llm=llm, checkpointer=InMemorySaver())


def run(
    question: str,
    user_id: str,
    machine_id: str,
    history: list[HistoryTurn] | None = None,
) -> GraphState:
    context_message = SystemMessage(
        content=(
            f"Current user_id: {user_id}. Current machine_id: {machine_id}. "
            "Tools default to this machine automatically when machine_id is omitted -- only pass a "
            "different machine_id if the user asks about another machine."
        )
    )
    prior_messages = _history_to_messages(history) if history else []
    result = get_graph().invoke(
        {
            "messages": [context_message, *prior_messages, HumanMessage(content=question)],
        },  # type: ignore
        # The graph is shared across requests, so each call gets its own thread: reusing one per user
        # would make the checkpointer accumulate messages across requests. The caller owns history.
        config={"configurable": {"thread_id": str(uuid.uuid4())}},
        context=AgentContext(user_id=user_id, machine_id=machine_id),
    )
    return cast(GraphState, result)


def ask(
    question: str,
    user_id: str,
    machine_id: str,
    history: list[HistoryTurn] | None = None,
) -> str:
    result = run(question, user_id, machine_id, history=history)
    return result["messages"][-1].content
