"""Manuals RAG specialist tool for FleetAssistant.

No LLM in this path: the retrieval stage must receive the user's question
exactly as asked, so manuals_agent calls get_manual_excerpts directly with the
stripped request instead of routing it through an LLM tool-calling loop (which
would let the model rewrite/shorten the query before it reaches retrieval).
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from src.tools import get_manual_excerpts

logger = logging.getLogger(__name__)


def make_manuals_tool(llm: BaseChatModel):
	@tool
	def manuals_agent(request: str, machine_id: str) -> str:
		"""Ask the manuals specialist about documentation, procedures, or error-code meanings for a specific machine. Always pass the machine_id from the current conversation context."""
		query = request.strip()
		logger.info("ManualsAgent invoked | query=%r machine_id=%r", query, machine_id)

		response = get_manual_excerpts.invoke({"query": query, "machine_id": machine_id})

		logger.info("ManualsAgent produced answer (%d chars)", len(response))
		return response

	return manuals_agent
