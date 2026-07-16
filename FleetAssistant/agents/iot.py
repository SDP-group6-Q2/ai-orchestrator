"""Class-based IoT telemetry agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

import ollama

from FleetAssistant.state import GraphState
from FleetAssistant.tools.query_telemetry import (
	LocalTelemetryClient,
	TelemetryClient,
	TelemetryReading,
)

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3

_SYSTEM_PROMPT = (
	"You are the IoT telemetry agent for FleetAssistant. "
	"Call the query_telemetry tool to fetch live sensor readings for the user's machine "
	"before responding; call it again with a different metric if you need more data. "
	"Answer only once you have grounded evidence from the tool. "
	"Keep the answer concise and practical."
)

_QUERY_TELEMETRY_TOOL = {
	"type": "function",
	"function": {
		"name": "query_telemetry",
		"description": "Query the telemetry server for live machine sensor readings.",
		"parameters": {
			"type": "object",
			"properties": {
				"metric": {
					"type": "string",
					"description": "Optional metric name to filter readings (e.g. temperature, vibration). Omit for all available metrics.",
				},
			},
			"required": [],
		},
	},
}


class IotAgent:
	def __init__(
		self,
		model: str | None = None,
		base_url: str | None = None,
		client: TelemetryClient | None = None,
	):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self._telemetry_client = client or LocalTelemetryClient()

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _format_readings(self, readings: Sequence[TelemetryReading]) -> str:
		if not readings:
			return "No telemetry readings matched that query."
		return "\n".join(f"- {reading['metric']}: {reading['value']} (at {reading['timestamp']})" for reading in readings)

	def _call_tool(self, name: str, arguments: dict, machine_id: str) -> str:
		if name != "query_telemetry":
			raise ValueError(f"Unknown tool call from model: {name!r}")
		readings = self._telemetry_client.query(machine_id, arguments.get("metric") or None)
		return self._format_readings(readings)

	def _generate_answer(self, request: str, machine_id: str) -> str:
		messages: list[dict] = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": f"Machine: {machine_id}\nRequest: {request}"},
		]
		client = self._client()

		for _ in range(_MAX_TOOL_ROUNDS):
			response = client.chat(
				model=self._model,
				messages=messages,
				tools=[_QUERY_TELEMETRY_TOOL],
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
				arguments = function.get("arguments") or {}
				logger.info("IotAgent calling tool %s(%s) for machine=%r", function["name"], arguments, machine_id)
				tool_result = self._call_tool(function["name"], arguments, machine_id)
				messages.append({"role": "tool", "content": tool_result})

		raise RuntimeError(f"IoT agent exceeded {_MAX_TOOL_ROUNDS} tool-call rounds without a final answer")

	def run(self, state: GraphState) -> GraphState:
		if not state.get("agent_calls"):
			raise ValueError("No agent call was prepared by the orchestrator.")

		call = state["agent_calls"][-1]

		if call["agent_name"] != "iot_agent":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"] or state["request"]
		machine_id = state["user_info"]["machine_id"]
		logger.info("IotAgent invoked | request=%r | machine_id=%r", request, machine_id)
		error: str | None = None
		try:
			response = self._generate_answer(request, machine_id)
		except Exception as exc:
			logger.warning("IotAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available telemetry."
			error = f"IotAgent fell back to a decline response: {exc}"
		logger.info("IotAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["response"] = response
		state["next_node"] = "orchestrator"
		state["error"] = error

		return state
