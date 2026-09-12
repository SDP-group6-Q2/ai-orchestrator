"""Manuals RAG skill for FleetAssistant.

No LLM in this path: the retrieval stage must receive the user's question
exactly as asked, so manuals_agent calls get_manual_excerpts directly with the
stripped request instead of routing it through an LLM tool-calling loop (which
would let the model rewrite/shorten the query before it reaches retrieval).

Some callers (e.g. run_specialist_in_terminal.py, when replaying multi-turn
history to specialists that *do* have an LLM to parse it back out) wrap the
question in a "Here is the conversation so far: ... Now answer the user's new
message: <question>" transcript. manuals_agent has no LLM to unwrap that, so
it recovers the bare question itself rather than trusting every caller to
know it must never be wrapped.
"""

from __future__ import annotations

import logging

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from src.skills.base import Skill
from src.skills.formatting import render_table
from src.tools import get_manual_excerpts

logger = logging.getLogger(__name__)

_HISTORY_WRAPPER_MARKER = "Now answer the user's new message: "
_EXCERPT_PREVIEW_LENGTH = 200


def _extract_query(request: str) -> str:
	"""Recover the actual question from a possibly history-wrapped request."""
	marker_index = request.rfind(_HISTORY_WRAPPER_MARKER)
	if marker_index == -1:
		return request.strip()
	return request[marker_index + len(_HISTORY_WRAPPER_MARKER):].strip()


@tool(response_format="content_and_artifact")
def manuals_agent(request: str, machine_id: str) -> tuple[str, list[dict] | None]:
	"""Ask the manuals specialist about documentation, procedures, or error-code meanings for a specific machine. Always pass the machine_id from the current conversation context."""
	query = _extract_query(request)
	logger.info("ManualsAgent invoked | query=%r machine_id=%r", query, machine_id)

	excerpts = get_manual_excerpts.invoke({"query": query, "machine_id": machine_id})

	if isinstance(excerpts, str):
		logger.info("ManualsAgent produced answer (%d chars)", len(excerpts))
		return excerpts, None

	content = "\n".join(f"- {e['source']} (page {e['page']}): {e['content']}" for e in excerpts)
	logger.info("ManualsAgent produced answer (%d chars)", len(content))
	return content, excerpts


def _render_manuals_citations(message: ToolMessage) -> str | None:
	excerpts = message.artifact
	if not excerpts:
		return None

	rows = [
		{
			"source": e["source"],
			"page": e["page"],
			"excerpt": e["content"][:_EXCERPT_PREVIEW_LENGTH],
		}
		for e in excerpts
	]
	return render_table(rows, columns=["source", "page", "excerpt"])


manuals_skill = Skill(
	name="manuals",
	description=(
		"Retrieval-augmented (RAG) semantic search over machine manual documents "
		"-- documentation, procedures, and error-code meanings for a specific machine."
	),
	instructions=(
		"Use the manuals_agent to ask technical questions about the machine's "
		"operation, maintenance, or troubleshooting."
	),
	tools=[manuals_agent],
	tool_renderers={"manuals_agent": _render_manuals_citations},
)
