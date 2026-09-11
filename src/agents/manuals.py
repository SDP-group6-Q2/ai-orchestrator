"""Manuals RAG specialist tool for FleetAssistant.

No LLM in this path: the retrieval stage must receive the user's question
exactly as asked, so manuals_agent calls get_manual_excerpts_for_company directly
with the stripped request instead of routing it through an LLM tool-calling loop
(which would let the model rewrite/shorten the query before it reaches retrieval).
It also authorizes the machine itself (real user + visibility tier + machine-to-
company ownership, via authorized_company_for_machine) before retrieval runs,
rather than relying on get_manual_excerpts' own ToolRuntime injection -- which
only fires when the tool is invoked through an agent's tool-calling loop, not on
a direct call like this one.

Some callers (e.g. run_specialist_in_terminal.py, when replaying multi-turn
history to specialists that *do* have an LLM to parse it back out) wrap the
question in a "Here is the conversation so far: ... Now answer the user's new
message: <question>" transcript. manuals_agent has no LLM to unwrap that, so
it recovers the bare question itself rather than trusting every caller to
know it must never be wrapped.
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.context import AgentContext
from src.security.access import ACCESS_DENIED_OR_UNAVAILABLE
from src.tools.manuals_tools import authorized_company_for_machine, get_manual_excerpts_for_company

logger = logging.getLogger(__name__)

_HISTORY_WRAPPER_MARKER = "Now answer the user's new message: "


def _extract_query(request: str) -> str:
	"""Recover the actual question from a possibly history-wrapped request."""
	marker_index = request.rfind(_HISTORY_WRAPPER_MARKER)
	if marker_index == -1:
		return request.strip()
	return request[marker_index + len(_HISTORY_WRAPPER_MARKER):].strip()


def make_manuals_tool(llm: BaseChatModel):
	@tool
	def manuals_agent(request: str, machine_id: str, runtime: ToolRuntime[AgentContext]) -> str:
		"""Ask the manuals specialist about documentation, procedures, or error-code meanings for a specific machine. Always pass the machine_id from the current conversation context."""
		query = _extract_query(request)
		logger.info("ManualsAgent invoked | query=%r machine_id=%r", query, machine_id)

		company_id = authorized_company_for_machine(runtime.context.user_id, machine_id)
		if company_id is None:
			logger.warning("ManualsAgent denied | user_id=%r machine_id=%r", runtime.context.user_id, machine_id)
			return ACCESS_DENIED_OR_UNAVAILABLE

		response = get_manual_excerpts_for_company(query, company_id, machine_id)

		logger.info("ManualsAgent produced answer (%d chars)", len(response))
		return response

	return manuals_agent
