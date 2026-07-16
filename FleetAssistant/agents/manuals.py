"""Class-based manuals agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

import ollama

from FleetAssistant.state import GraphState
from FleetAssistant.tools.retrieve_manual import (
	LocalManualRetriever,
	ManualExcerpt,
	ManualRetriever,
)

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 3

_SYSTEM_PROMPT = (
	"You are the manuals RAG agent for FleetAssistant. "
	"Call the retrieve_manual tool to ground your answer in actual machine manual content "
	"before responding; call it again with a refined query if the excerpts you got back "
	"are not enough. Answer only once you have grounded evidence from the tool. "
	"Keep the answer concise and practical."
)

_RETRIEVE_MANUAL_TOOL = {
	"type": "function",
	"function": {
		"name": "retrieve_manual",
		"description": "Retrieve machine manual excerpts relevant to a query.",
		"parameters": {
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description": "What to search the manuals for.",
				},
			},
			"required": ["query"],
		},
	},
}


class ManualsAgent:
	def __init__(
		self,
		model: str | None = None,
		base_url: str | None = None,
		retriever: ManualRetriever | None = None,
	):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self._retriever = retriever or LocalManualRetriever()

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _format_excerpts(self, excerpts: Sequence[ManualExcerpt]) -> str:
		if not excerpts:
			return "No manual excerpts matched that query."
		return "\n".join(f"- {item['source']}: {item['snippet']}" for item in excerpts)

	def _call_tool(self, name: str, arguments: dict) -> str:
		if name != "retrieve_manual":
			raise ValueError(f"Unknown tool call from model: {name!r}")
		excerpts = self._retriever.retrieve(arguments.get("query") or "")
		return self._format_excerpts(excerpts)

	def _generate_answer(self, request: str) -> str:
		messages: list[dict] = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
		]
		client = self._client()

		for _ in range(_MAX_TOOL_ROUNDS):
			response = client.chat(
				model=self._model,
				messages=messages,
				tools=[_RETRIEVE_MANUAL_TOOL],
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
				logger.info("ManualsAgent calling tool %s(%s)", function["name"], arguments)
				tool_result = self._call_tool(function["name"], arguments)
				messages.append({"role": "tool", "content": tool_result})

		raise RuntimeError(f"Manuals agent exceeded {_MAX_TOOL_ROUNDS} tool-call rounds without a final answer")

	def run(self, state: GraphState) -> GraphState:
		if not state.get("agent_calls"):
			raise ValueError("No agent call was prepared by the orchestrator.")

		call = state["agent_calls"][-1]

		if call["agent_name"] != "manuals_agent":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"] or state["request"]
		logger.info("ManualsAgent invoked | request=%r", request)
		error: str | None = None
		try:
			response = self._generate_answer(request)
		except Exception as exc:
			logger.warning("ManualsAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available manuals."
			error = f"ManualsAgent fell back to a decline response: {exc}"
		logger.info("ManualsAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["response"] = response
		state["next_node"] = "orchestrator"
		state["error"] = error

		return state
