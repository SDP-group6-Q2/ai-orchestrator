from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.config import REFERENCE_DATE
from src.context import AgentContext
from src.skills import (
	compose,
	diagnostics_skill,
	fleet_skill,
	maintenance_skill,
	manuals_skill,
	render_tool_tables_middleware,
)

logger = logging.getLogger(__name__)

_BASE_PROMPT = (
	f"Today's date is {REFERENCE_DATE}. Use it for any relative date reasoning "
	"(e.g. how overdue a maintenance ticket is, or how recent an alarm is).\n\n"

	"You are a technical expert on AROL company machinery. The company produces automatic machines and lines "
	"for the production of capping/closure of bottles, jars, and other containers. "
	"Your goal is to understand a customer's request and provide a grounded answer, using whichever of your "
	"available tools are relevant to it.\n\n"

	"Manual citations and retrieved data are automatically rendered as tables above your answer whenever a "
	"relevant tool call produces one -- do not re-list raw rows or citations yourself. Write a concise, "
	"practical answer that interprets what those tables show and directly addresses the request, grounded "
	"only in evidence from the tools you actually called.\n\n"

	"- If a tool returns ACCESS_DENIED_OR_UNAVAILABLE, tell the user that "
	"they cannot access technical information for the requested resource.\n"
	"- Never speculate that inaccessible technical data was cancelled, deleted, "
	"entered incorrectly or does not exist.\n"
)

_SKILLS = [fleet_skill, diagnostics_skill, maintenance_skill, manuals_skill]

# Presentation order for rendered result tables (citations first, then data),
# independent of _SKILLS' composition order and of whichever order the model
# actually calls tools in. Deliberately excludes fleet_skill -- fleet-lookup
# results never get a table.
_TABLE_SKILLS = [manuals_skill, diagnostics_skill, maintenance_skill]


def make_technical_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
	system_prompt, tools = compose(_BASE_PROMPT, _SKILLS)

	agent = create_agent(
		model=llm,
		tools=tools,
		system_prompt=system_prompt,
		checkpointer=checkpointer,
		context_schema=AgentContext,
		middleware=[render_tool_tables_middleware(_TABLE_SKILLS)],
	)

	return agent
