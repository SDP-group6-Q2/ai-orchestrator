"""Supervisor agent for the FleetAssistant orchestration flow.

Specialist agents (manuals, telemetry, orders, service) are exposed to the
supervisor as ordinary tools. The supervisor's own create_agent loop decides
which ones to call, in what order and how many times.

Ollama does not honor tool_choice, so nothing forces the model to call a tool
on any given turn -- left alone it can answer straight from its own knowledge,
ungrounded in any specialist's data. The `_require_tool_grounding` middleware
below closes that gap explicitly: after every model call, if the model tried
to answer without having called any specialist tool since the user's last
message, it is bounced back with a reminder instead of being allowed to
finish, up to a small retry cap.
"""

from __future__ import annotations

import logging
from typing import NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState, after_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.agents.diagnostics import make_diagnostics_tool
from src.agents.manuals import make_manuals_tool
from src.agents.orders import make_orders_tool
from src.agents.technical import make_technical_tool

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the assistant for AROL, a company that produces industrial capping machines for their clients. "
	"Answer client questions about their machines using the specialist tools available to you: "
	"manuals_agent for questions about documentation, procedures or error-code meanings; "
	"iot_agent for questions that need live telemetry or sensor readings from the machine; "
	"orders_agent for questions about order history, shipments or support/service contracts; "
	"service_agent for questions about customer service tickets or past service visits. "
	"The user's user_id and machine_id are given to you at the start of the conversation; "
	"always pass the correct id(s) when calling a specialist tool. "
	"You must always call at least one specialist tool before answering -- never answer from your "
	"own knowledge alone. Call as many specialist tools as needed, in any order, to gather grounded "
	"evidence. If no tool result is relevant to the question, say so plainly instead of guessing. "
	"Once you have enough information, answer the user directly and concisely, without mentioning "
	"internal steps or tool names."
)

_MAX_GROUNDING_REMINDERS = 2

_GROUNDING_REMINDER = (
	"You must call at least one specialist tool (manuals_agent, iot_agent, orders_agent, "
	"service_agent) before answering. Choose whichever is most relevant to the question "
	"and call it now."
)


class _SupervisorState(AgentState):
	grounding_reminders: NotRequired[int]


def _has_tool_evidence_since_last_human(messages: list) -> bool:
	"""Whether a specialist tool has already run since the user's current turn started."""
	for message in reversed(messages):
		if isinstance(message, HumanMessage):
			return False
		if isinstance(message, ToolMessage):
			return True
	return False


@after_model(can_jump_to=["model"], state_schema=_SupervisorState)
def _require_tool_grounding(state, runtime):
	last = state["messages"][-1]

	# Model called a tool this turn (or the last message isn't its own reply) -- fine, reset the counter.
	if not isinstance(last, AIMessage) or last.tool_calls:
		return {"grounding_reminders": 0}

	# Answered without ever consulting a specialist this turn -- allowed once evidence exists.
	if _has_tool_evidence_since_last_human(state["messages"]):
		return {"grounding_reminders": 0}

	reminders = state.get("grounding_reminders", 0)
	if reminders >= _MAX_GROUNDING_REMINDERS:
		logger.warning("Supervisor answered ungrounded after %d reminder(s); giving up enforcement.", reminders)
		return {"grounding_reminders": 0}

	logger.info("Supervisor answered without calling a specialist tool; bouncing back (attempt %d).", reminders + 1)
	return {
		"jump_to": "model",
		"grounding_reminders": reminders + 1,
		"messages": [HumanMessage(content=_GROUNDING_REMINDER)],
	}


def make_supervisor_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
	tools = [
		make_manuals_tool(llm),
		make_technical_tool(llm),
		make_orders_tool(llm),
		make_diagnostics_tool(llm),
	]

	return create_agent(
		model=llm,
		tools=tools,
		system_prompt=_SYSTEM_PROMPT,
		middleware=[_require_tool_grounding],
		checkpointer=checkpointer,
	)
