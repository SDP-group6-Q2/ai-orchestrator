"""Class-based service agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
import ollama

from src.state import GraphState
from src.tools import (open_new_ticket, query_service_tickets, get_service_tables_descriptors)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the customer service agent for FleetAssistant. "
	"Use the get_service_tables_descriptors tool to understand the structure of the service tickets data before querying it."
	"Call query_service_tickets to fetch the user's open and past support tickets. "
	"If necessary, ask the user for more information, and then call open_new_ticket to create a new support ticket, upon confirmation from user."
	"Answer only once you have grounded evidence from the tools. "
	"If no service ticket data is relevant, say you cannot answer the question based on the available tickets. "
	"Keep the answer concise and practical."
)


class ServiceAgent:
	def __init__(self, llm: BaseChatModel):
		self._llm_with_tools = llm.bind_tools([open_new_ticket, query_service_tickets, get_service_tables_descriptors])

	def _generate_answer(self, request: str, machine_id: int) -> str:
		messages = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		response = self._llm_with_tools.invoke(messages)
		logger.info("ServiceAgent generated answer): ", response)
		return response.content

	def run(self, state: GraphState) -> GraphState:
		call = state["agent_calls"][-1]

		if call["agent_name"] != "service":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"]
		machine_id = state["user_info"]["machine_id"]
		logger.info("ServiceAgent invoked | request=%r", request)

		try:
			response = self._generate_answer(request, machine_id)
		except Exception as exc:
			logger.warning("ServiceAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available tickets."

		logger.info("ServiceAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["messages"] = [{'role': 'assistant', 'content': response}]

		return state
