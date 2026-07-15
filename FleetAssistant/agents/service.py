"""Class-based service agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

import ollama

from FleetAssistant.state import GraphState
from FleetAssistant.tools.query_service import (
	LocalServiceClient,
	ServiceClient,
	ServiceTicket,
	ServiceVisit,
)

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3

_SYSTEM_PROMPT = (
	"You are the customer service agent for FleetAssistant. "
	"Call list_tickets to fetch the user's open and past support tickets, and "
	"list_service_history to fetch past service visits, before responding. "
	"Answer only once you have grounded evidence from the tools. "
	"Keep the answer concise and practical."
)

_LIST_TICKETS_TOOL = {
	"type": "function",
	"function": {
		"name": "list_tickets",
		"description": "List the user's customer service tickets, open and closed.",
		"parameters": {"type": "object", "properties": {}, "required": []},
	},
}

_LIST_SERVICE_HISTORY_TOOL = {
	"type": "function",
	"function": {
		"name": "list_service_history",
		"description": "List the user's past service visits and interventions.",
		"parameters": {"type": "object", "properties": {}, "required": []},
	},
}


class ServiceAgent:
	def __init__(
		self,
		model: str | None = None,
		base_url: str | None = None,
		client: ServiceClient | None = None,
	):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self._service_client = client or LocalServiceClient()

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _format_tickets(self, tickets: Sequence[ServiceTicket]) -> str:
		if not tickets:
			return "No service tickets found for this user."
		return "\n".join(f"- {t['ticket_id']} ({t['status']}, machine {t['machine_id']}): {t['summary']}" for t in tickets)

	def _format_history(self, visits: Sequence[ServiceVisit]) -> str:
		if not visits:
			return "No service history found for this user."
		return "\n".join(f"- {v['visit_id']} on {v['date']} (machine {v['machine_id']}): {v['summary']}" for v in visits)

	def _call_tool(self, name: str, user_id: str) -> str:
		if name == "list_tickets":
			return self._format_tickets(self._service_client.list_tickets(user_id))
		if name == "list_service_history":
			return self._format_history(self._service_client.list_service_history(user_id))
		raise ValueError(f"Unknown tool call from model: {name!r}")

	def _generate_answer(self, request: str, user_id: str) -> str:
		messages: list[dict] = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
		]
		client = self._client()

		for _ in range(_MAX_TOOL_ROUNDS):
			response = client.chat(
				model=self._model,
				messages=messages,
				tools=[_LIST_TICKETS_TOOL, _LIST_SERVICE_HISTORY_TOOL],
				options={"temperature": 0.1},
			)
			message = response["message"]
			tool_calls = message.get("tool_calls") or []

			if not tool_calls:
				content = (message.get("content") or "").strip()
				if not content:
					raise ValueError("empty response from ollama")
				return content

			assistant_entry: dict = {"role": "assistant", "content": message.get("content") or ""}
			assistant_entry["tool_calls"] = tool_calls
			messages.append(assistant_entry)

			for call in tool_calls:
				function = call["function"]
				tool_result = self._call_tool(function["name"], user_id)
				messages.append({"role": "tool", "content": tool_result})

		raise RuntimeError(f"Service agent exceeded {_MAX_TOOL_ROUNDS} tool-call rounds without a final answer")

	def run(self, state: GraphState) -> GraphState:
		if not state.get("agent_calls"):
			raise ValueError("No agent call was prepared by the orchestrator.")

		call = state["agent_calls"][-1]

		if call["agent_name"] != "service_agent":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"] or state["request"]
		user_id = state["user_info"]["user_id"]
		response = self._generate_answer(request, user_id)

		call["agent_response"] = response
		state["response"] = response
		state["next_node"] = "orchestrator"

		return state
