"""Class-based IoT telemetry agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from langchain.chat_models import BaseChatModel

from src.state import GraphState
from src.tools import query_telemetry_readings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the IoT telemetry agent for FleetAssistant. "
	"Call the query_telemetry_readings tool with an SQL query to fetch live sensor readings for the user's machine "
	"before responding; call it again with a different query if you need more data. "
	"Answer only once you have grounded evidence from the tool. "
	"If no telemetry data is relevant, say you cannot answer the question based on the available readings. "
	"Keep the answer concise and practical."
)

class IotAgent:
	def __init__(self, llm: BaseChatModel):
		self._llm_with_tools = llm.bind_tools([query_telemetry_readings])

	# TODO: Evaluate truthfulness of the answer executing same SQL queries and comparing the results with the answer
	def _generate_answer(self, request: str, machine_id: int) -> str:
		messages = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		response = self._llm_with_tools.invoke(messages)
		return response.content

	def run(self, state: GraphState) -> GraphState:
		call = state["agent_calls"][-1]

		if call["agent_name"] != "telemetry":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"]
		
		logger.info("IotAgent invoked | request=%r", request)

		try:
			response = self._generate_answer(request)
		except Exception as exc:
			logger.warning("IotAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available telemetry."

		logger.info("IotAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["messages"] = [{'role': 'assistant', 'content': response}]

		return state

