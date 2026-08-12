"""Service specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

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


def make_service_tool(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[get_service_tables_descriptors, query_service_tickets, open_new_ticket],
		system_prompt=_SYSTEM_PROMPT,
	)

	@tool
	def service_agent(request: str, machine_id: int) -> str:
		"""Ask the customer service specialist about support tickets or past service visits for a specific machine, or to open a new ticket. Always pass the machine_id from the current conversation context."""
		logger.info("ServiceAgent invoked | request=%r machine_id=%r", request, machine_id)

		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		try:
			result = agent.invoke({"messages": messages})
			response = result["messages"][-1].content
		except Exception:
			logger.warning("ServiceAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available tickets."

		logger.info("ServiceAgent produced answer (%d chars)", len(response))
		return response

	return service_agent
