from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.agents.manuals import make_manuals_tool
from src.agents.diagnostics import make_diagnostics_tool
from src.context import AgentContext

from src.tools import (get_company_maintenance_tickets, get_company_machines, get_machine_details)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are a technical expert on AROL company machinery. The company produces automatic machines and lines for the production of capping/closure of bottles, jars, and other containers."
	"Your goal is to understand a costumer request and provide a grounded answer, using available expert tools: diagnostics and manuals."
	"You also have access to open maintenance tickets for the machine, and you can query them to provide a more complete answer."

	"Use get_company_machines to list every machine belonging to the current user's company, including model details. "
	"Use get_machine_details for a specific machine's details (including its model) by machine_id. "
    "Use the diagnostics_agent to ask questions about the machine's live sensor readings, error states, or operational health. "
	"Use the manuals_agent to ask technical questions about the machine's operation, maintenance, or troubleshooting."
	"Use get_company_maintenance_tickets to fetch the user's company's open and past support tickets. "

	"Answer only once you have grounded evidence from the tool, using, when possible, both diagnostics data and manuals retrieved information. "
	"Keep the answer concise and practical.\n\n"

	"- If a tool returns ACCESS_DENIED_OR_UNAVAILABLE, tell the user that "
	"they cannot access technical information for the requested resource.\n"
	"- Never speculate that inaccessible technical data was cancelled, deleted, "
	"entered incorrectly or does not exist.\n"
)

def make_technical_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
	tools = [
        make_manuals_tool(llm),
        make_diagnostics_tool(llm),
		get_company_maintenance_tickets,
		get_company_machines,
		get_machine_details,
    ]

	agent = create_agent(
		model=llm,
		tools=tools,
		system_prompt=_SYSTEM_PROMPT,
		checkpointer=checkpointer,
		context_schema=AgentContext,
	)

	return agent