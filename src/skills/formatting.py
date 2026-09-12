"""Deterministic markdown-table rendering for technical_agent's tool results.

Renders tables from whatever tools actually got called in a turn, rather than
from a pre-guessed question category -- the real example questions in
docs/TASK.md draw on anywhere from one to three skills in no fixed
combination, so there's no single template that fits all of them.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from langchain.agents.middleware import after_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.skills.base import Skill

_MAX_ROWS = 20
_MAX_CELL_LENGTH = 200


def _format_cell(value: object) -> str:
	text = "" if value is None else str(value)
	text = text.replace("|", "\\|").replace("\n", " ").strip()
	if len(text) > _MAX_CELL_LENGTH:
		text = text[: _MAX_CELL_LENGTH - 1] + "…"
	return text


def render_table(rows: list[dict], columns: list[str] | None = None) -> str:
	"""Build a plain markdown table from a list of dict rows."""
	if not rows:
		return ""

	columns = columns or list(rows[0].keys())
	header = "| " + " | ".join(columns) + " |"
	separator = "| " + " | ".join("---" for _ in columns) + " |"
	body_rows = rows[:_MAX_ROWS]
	body = "\n".join(
		"| " + " | ".join(_format_cell(row.get(col)) for col in columns) + " |"
		for row in body_rows
	)
	table = "\n".join([header, separator, body])

	remaining = len(rows) - len(body_rows)
	if remaining > 0:
		table += f"\n\n_(+{remaining} more row{'s' if remaining != 1 else ''} not shown)_"
	return table


def render_json_tool_result(message: ToolMessage) -> str | None:
	"""Generic renderer for tools whose ToolMessage.content is JSON (a dict or list of dicts)."""
	try:
		data = json.loads(message.content)
	except (TypeError, ValueError):
		return None

	if not data:
		return None

	rows = [data] if isinstance(data, dict) else data
	if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
		return None

	return render_table(rows)


def render_tool_tables_middleware(skills: list[Skill]):
	"""Build an after_agent middleware that prefixes the final answer with tables
	rendered from this turn's tool calls -- grouped by skill, in the order `skills`
	is given (not tool-call chronological order), so presentation order is fixed
	regardless of which order the model actually called tools in.
	"""
	renderers_by_skill: list[dict[str, Callable[[ToolMessage], str | None]]] = [
		skill.tool_renderers for skill in skills
	]

	@after_agent
	def render_tool_tables(state, runtime):
		messages = state["messages"]
		if not messages or not isinstance(messages[-1], AIMessage):
			return None

		turn_tool_messages: list[ToolMessage] = []
		for message in reversed(messages[:-1]):
			if isinstance(message, HumanMessage):
				break
			if isinstance(message, ToolMessage):
				turn_tool_messages.append(message)
		turn_tool_messages.reverse()

		tables: list[str] = []
		for renderers in renderers_by_skill:
			for message in turn_tool_messages:
				renderer = renderers.get(message.name)
				if renderer is None:
					continue
				rendered = renderer(message)
				if rendered:
					tables.append(rendered)

		if not tables:
			return None

		final = messages[-1]
		new_content = "\n\n".join(tables) + "\n\n" + final.content
		return {"messages": [final.model_copy(update={"content": new_content})]}

	return render_tool_tables
