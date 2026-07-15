"""Class-based orders agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

import ollama

from FleetAssistant.state import GraphState
from FleetAssistant.tools.query_orders import (
	ContractRecord,
	LocalOrdersClient,
	OrderRecord,
	OrdersClient,
)

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3

_SYSTEM_PROMPT = (
	"You are the orders agent for FleetAssistant. "
	"Call list_orders to fetch the user's order and shipment history, and list_contracts "
	"to fetch the user's active support/service contracts, before responding. "
	"Answer only once you have grounded evidence from the tools. "
	"Keep the answer concise and practical."
)

_LIST_ORDERS_TOOL = {
	"type": "function",
	"function": {
		"name": "list_orders",
		"description": "List the user's order history (parts, shipments, service requests).",
		"parameters": {"type": "object", "properties": {}, "required": []},
	},
}

_LIST_CONTRACTS_TOOL = {
	"type": "function",
	"function": {
		"name": "list_contracts",
		"description": "List the user's active support/service contracts.",
		"parameters": {"type": "object", "properties": {}, "required": []},
	},
}


class OrdersAgent:
	def __init__(
		self,
		model: str | None = None,
		base_url: str | None = None,
		client: OrdersClient | None = None,
	):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self._orders_client = client or LocalOrdersClient()

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _format_orders(self, orders: Sequence[OrderRecord]) -> str:
		if not orders:
			return "No orders found for this user."
		return "\n".join(f"- {o['order_id']} ({o['status']}, machine {o['machine_id']}): {o['summary']}" for o in orders)

	def _format_contracts(self, contracts: Sequence[ContractRecord]) -> str:
		if not contracts:
			return "No contracts found for this user."
		return "\n".join(f"- {c['contract_id']}: {c['summary']}" for c in contracts)

	def _call_tool(self, name: str, user_id: str) -> str:
		if name == "list_orders":
			return self._format_orders(self._orders_client.list_orders(user_id))
		if name == "list_contracts":
			return self._format_contracts(self._orders_client.list_contracts(user_id))
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
				tools=[_LIST_ORDERS_TOOL, _LIST_CONTRACTS_TOOL],
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

		raise RuntimeError(f"Orders agent exceeded {_MAX_TOOL_ROUNDS} tool-call rounds without a final answer")

	def run(self, state: GraphState) -> GraphState:
		if not state.get("agent_calls"):
			raise ValueError("No agent call was prepared by the orchestrator.")

		call = state["agent_calls"][-1]

		if call["agent_name"] != "orders_agent":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"] or state["request"]
		user_id = state["user_info"]["user_id"]
		response = self._generate_answer(request, user_id)

		call["agent_response"] = response
		state["response"] = response
		state["next_node"] = "orchestrator"

		return state
