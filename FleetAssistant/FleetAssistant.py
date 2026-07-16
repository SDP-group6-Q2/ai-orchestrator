

"""FleetAssistant high-level entry point."""

from __future__ import annotations

from typing import cast

from FleetAssistant.graph import build_graph
from FleetAssistant.state import GraphState


class FleetAssistant:
    def __init__(self, graph=None, llama_model: str = "llama3.1:cloud", llama_base_url: str = "http://localhost:11434"):
        self._llama_model = llama_model
        self._llama_base_url = llama_base_url
        self._graph = graph or build_graph(model=llama_model, base_url=llama_base_url)

    def run(self, question: str, user_id: str, machine_id: str) -> GraphState:
        initial_state: GraphState = {
            "request": question,
            "user_info": {"user_id": user_id, "machine_id": machine_id},
            "agent_calls": [],
            "plan": [],
            "current_step": 0,
            "response": "",
            "next_node": "",
            "error": None,
        }
        return cast(GraphState, self._graph.invoke(initial_state))

    def ask(self, question: str, user_id: str, machine_id: str) -> str:
        result = self.run(question, user_id, machine_id)
        return result.get("response", "")