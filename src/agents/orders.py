"""Class-based orders agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
import ollama

from src.state import GraphState
from src.tools import (get_orders_info, list_contracts)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
	"You are the orders agent for FleetAssistant. "
	"Call get_orders_info to fetch the user's order and shipment history "
	"Call list_contracts to fetch the user's active support/service contracts, before responding. "
	"Answer only once you have grounded evidence from the tools. "
	"Keep the answer concise and practical."
)


class OrdersAgent:
	def __init__(self, llm: BaseChatModel):
		self._llm_with_tools = llm.bind_tools([get_orders_info, list_contracts])

	def _generate_answer(self, request: str, user_id: int) -> str:
		messages = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
			{"role": "user", "content": "My user ID is: {}".format(user_id)},
		]
		response = self._llm_with_tools.invoke(messages)
		return response.content

	def run(self, state: GraphState) -> GraphState:
		call = state["agent_calls"][-1]

		if call["agent_name"] != "orders":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"]
		user_id = state["user_info"]["user_id"]
		
		logger.info("OrdersAgent invoked | request=%r", request)

		try:
			response = self._generate_answer(request, user_id)
		except Exception as exc:
			logger.warning("OrdersAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available information."

		logger.info("OrdersAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["messages"] = [{'role': 'assistant', 'content': response}]

		return state
