from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

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

	"The user_id and machine_id for the current conversation are given to you in a system message at the start of the thread. "
	"Always use that machine_id for tool calls unless the user explicitly names a different machine; never ask the user for information already provided this way. "

	"Answer only once you have grounded evidence from the tool, using, when possible, both diagnostics data and manuals retrieved information. "
	"Keep the answer concise and practical."
)

def make_technical_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
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
		checkpointer=checkpointer,
	)

	return agent