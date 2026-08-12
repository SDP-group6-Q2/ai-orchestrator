"""Orders specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from src.tools import (get_orders_info, list_contracts)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
	"You are the orders agent for FleetAssistant. "
	"Call get_orders_info to fetch the user's order and shipment history "
	"Call list_contracts to fetch the user's active support/service contracts, before responding. "
	"Answer only once you have grounded evidence from the tools. "
	"Keep the answer concise and practical."
)


def make_orders_tool(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[get_orders_info, list_contracts],
		system_prompt=_SYSTEM_PROMPT,
	)

	@tool
	def orders_agent(request: str, user_id: int) -> str:
		"""Ask the orders specialist about order history, shipments, or active support/service contracts. Always pass the user_id from the current conversation context."""
		logger.info("OrdersAgent invoked | request=%r user_id=%r", request, user_id)

		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "My user ID is: {}".format(user_id)},
		]
		try:
			result = agent.invoke({"messages": messages})
			response = result["messages"][-1].content
		except Exception:
			logger.warning("OrdersAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available information."

		logger.info("OrdersAgent produced answer (%d chars)", len(response))
		return response

	return orders_agent
