

"""FleetAssistant high-level entry point."""

from __future__ import annotations

from langchain_ollama import ChatOllama

from typing import cast, TypedDict

from src.context import AgentContext
from src.graph import build_graph
from src.state import GraphState

from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import AIMessage, HumanMessage, SystemMessage


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


class FleetAssistant:
    def __init__(self, model: str = "gpt-oss:20b-cloud", llama_base_url: str = "http://localhost:11434"):
        self.llm = ChatOllama(model=model, base_url=llama_base_url)

        self._checkpointer = InMemorySaver()

        self._graph = build_graph(llm = self.llm, checkpointer=self._checkpointer)

    def _config_for(self, user_id: str) -> dict:
        # Keyed on user_id (not a fixed uuid generated once in __init__) so that
        # different users' checkpointed conversations never share a thread.
        return {"configurable": {"thread_id": user_id}}

    def run(
        self,
        question: str,
        user_id: str,
        machine_id: str,
        history: list[HistoryTurn] | None = None,
    ) -> GraphState:
        context_message = SystemMessage(
            content=(
                f"Current user_id: {user_id}. Current machine_id: {machine_id}. "
                "Use this machine_id for tool calls unless the user names a different machine."
            )
        )
        prior_messages = _history_to_messages(history) if history else []
        result = self._graph.invoke(
            {
                "messages": [context_message, *prior_messages, HumanMessage(content=question)],
            }, # type: ignore
            config=self._config_for(user_id), # type: ignore
            context=AgentContext(user_id=user_id, machine_id=machine_id),
        )
        return cast(GraphState, result)

    def ask(
        self,
        question: str,
        user_id: str,
        machine_id: str,
        history: list[HistoryTurn] | None = None,
    ) -> str:
        result = self.run(question, user_id, machine_id, history=history)
        return result["messages"][-1].content