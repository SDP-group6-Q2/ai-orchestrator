

"""FleetAssistant high-level entry point."""

from __future__ import annotations

from langchain_ollama import ChatOllama
import uuid

from typing import cast

from src.graph import build_graph
from src.state import GraphState

from langgraph.checkpoint.memory import InMemorySaver


class FleetAssistant:
    def __init__(self, model: str = "gpt-oss:20b-cloud", llama_base_url: str = "http://localhost:11434"):
        self.llm = ChatOllama(model=model, base_url=llama_base_url)

        self._checkpointer = InMemorySaver()
        self.config = {"configurable": {"thread_id": uuid.uuid4()}}
        
        self._graph = build_graph(llm = self.llm, checkpointer=self._checkpointer).compile(checkpointer=self._checkpointer)

    def run(self, question: str, user_id: str, machine_id: str) -> GraphState:
        result = self._graph.invoke(
            {
                "messages": [{"role": "user", "content": question}],
                "user_info": {"user_id": user_id, "machine_id": machine_id},
            },
            config=self.config
        )
        return cast(GraphState, result)

    def ask(self, question: str, user_id: str, machine_id: str) -> str:
        result = self.run(question, user_id, machine_id)
        return result["messages"][-1].content