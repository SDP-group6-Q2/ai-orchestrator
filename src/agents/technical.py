from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.config import REFERENCE_DATE
from src.context import AgentContext
from src.mcp_client import select_tools
from src.skills import (
	compose,
	diagnostics_skill,
	fleet_skill,
	maintenance_skill,
	manuals_skill,
)

logger = logging.getLogger(__name__)

_BASE_PROMPT = (
	f"Today's date is {REFERENCE_DATE}. Use it for any relative date reasoning "
	"(e.g. how overdue a maintenance ticket is, or how recent an alarm is).\n\n"

	"You are a technical expert on AROL company machinery. The company produces automatic machines and lines "
	"for the production of capping/closure of bottles, jars, and other containers. "
	"Your goal is to understand a customer's request and provide a grounded answer, using whichever of your "
	"available tools are relevant to it.\n\n"

	"The first system message in this conversation names the machine already in scope, for example: "
	"'Current machine_id: MCH-0001.' Whatever value follows 'Current machine_id:' "
	"in that message -- copy those exact characters, nothing else -- is the machine_id to pass to any tool "
	"call that needs one, unless the user asks about a different machine. Do not call get_company_machines "
	"to check what machines the company owns, and never ask the user to confirm or restate it. Seeing "
	"multiple machines listed anywhere is not a reason to ask which one they mean; the machine_id already "
	"stated at the start of this conversation answers that. If a tool call is denied or returns nothing, "
	"say so plainly and stop -- never write a generic answer instead, and never invent details (a model "
	"name, a spec, a procedure) that didn't come from a tool result.\n\n"

	"Tool results arrive as ready-to-read markdown tables and lists. Write a concise, practical answer "
	"that interprets what they show and directly addresses the request, grounded only in evidence from the "
	"tools you actually called. Do not paste raw tool output back.\n\n"

	"- If a tool reports that access is denied, tell the user that they cannot access technical "
	"information for the requested resource.\n"
	"- Never speculate that inaccessible technical data was cancelled, deleted, "
	"entered incorrectly or does not exist.\n"
)

_SKILLS = [fleet_skill, diagnostics_skill, maintenance_skill, manuals_skill]


def make_technical_agent(
	llm: BaseChatModel, tools: list[BaseTool], checkpointer: BaseCheckpointSaver | None = None
):
	system_prompt, tool_names = compose(_BASE_PROMPT, _SKILLS)

	return create_agent(
		model=llm,
		tools=select_tools(tools, tool_names),
		system_prompt=system_prompt,
		checkpointer=checkpointer,
		context_schema=AgentContext,
	)
