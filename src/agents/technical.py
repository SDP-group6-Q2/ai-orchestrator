"""Technical specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain_core.tools import tool
from langchain_protocol import Annotated, TypedDict
from langgraph.graph import add_messages

from src.agents.manuals import make_manuals_tool
from src.agents.diagnostics import make_diagnostics_tool

from src.tools import (query_service_tickets, get_service_tables_descriptors)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are a technical expert on AROL company machinery. The company produces automatic machines and lines for the production of capping/closure of bottles, jars, and other containers."
	"Your goal is to understand a costumer request and provide a grounded answer, using available expert tools: diagnostics and manuals."
	"You also have access to open maintenance tickets for the machine, and you can query them to provide a more complete answer."

    "Use the diagnostics_agent to ask questions about the machine's live sensor readings, error states, cycle counts, or operational health. "
	"Use the manuals_agent to ask technical questions about the machine's operation, maintenance, or troubleshooting."
	"Use the get_service_tables_descriptors tool to understand the structure of the service tickets data before querying it."
	"Use query_service_tickets to fetch the user's open and past support tickets. "
	
	"Answer only once you have grounded evidence from the tool. "
	"If no telemetry data is relevant, say you cannot answer the question based on the available readings. "
	"Keep the answer concise and practical."
)

class TechnicalGraphState(TypedDict):
    messages: Annotated[list, add_messages]

def make_technical_tool(llm: BaseChatModel):
	tools = [
        make_manuals_tool(llm),
        make_diagnostics_tool(llm),
		get_service_tables_descriptors,
		query_service_tickets,
    ]
	
	agent = create_agent(
		model=llm,
		tools=tools,
		system_prompt=_SYSTEM_PROMPT,
	)

	@tool
	def technical_agent(request: str, machine_id: str) -> str:
		"""Ask the technical specialist about live sensor readings, error states, cycle counts, or the operational health of a specific machine. Always pass the machine_id from the current conversation context."""
		logger.info("TechnicalAgent invoked | request=%r machine_id=%r", request, machine_id)

        # should pass full history
		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		try:
			result = agent.invoke({"messages": messages})
			response = result["messages"][-1].content
		except Exception:
			logger.warning("TechnicalAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available data."

		logger.info("TechnicalAgent produced answer: %s", response)
		return response

	return technical_agent
