"""Compact record of the tools a turn called, so the next turn can build on data already retrieved.

The backend stores it with the assistant message and sends it back in `history`. Only a short summary of each
result is kept (the first characters, one line): enough to remember what was looked at and roughly what it
showed, cheap enough not to bloat the prompt. The model is told to call the tool again for fresh or complete
data.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

MAX_ENTRIES_PER_TURN = 8
SUMMARY_CHARS = 300
CONTEXT_TURNS = 3  # how many earlier assistant turns' traces are shown to the model


class TraceEntry(TypedDict):
    tool: str
    args: dict[str, Any]
    summary: str
    error: bool


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)


def _one_line(text: str, limit: int = SUMMARY_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def extract_trace(messages: Sequence[BaseMessage]) -> list[TraceEntry]:
    """The tool calls made since the last user message, with a short summary of each result."""
    last_user = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    turn = messages[last_user + 1 :]
    results = {m.tool_call_id: m for m in turn if isinstance(m, ToolMessage)}
    trace: list[TraceEntry] = []
    for message in turn:
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls:
            result = results.get(call["id"])
            trace.append(
                TraceEntry(
                    tool=call["name"],
                    args={k: v for k, v in call["args"].items() if v is not None},
                    summary=_one_line(_text(result.content)) if result else "(no result)",
                    error=bool(result and result.status == "error"),
                )
            )
    return trace[:MAX_ENTRIES_PER_TURN]


def render_trace_context(history: Sequence[dict[str, Any]], turns: int = CONTEXT_TURNS) -> str:
    """Text for the model listing what earlier assistant turns retrieved ('' when there is nothing)."""
    traced = [turn["trace"] for turn in history if turn.get("role") == "assistant" and turn.get("trace")]
    lines = []
    for trace in traced[-turns:]:
        for entry in trace:
            args = ", ".join(f"{k}={v!r}" for k, v in entry["args"].items())
            status = " [error]" if entry.get("error") else ""
            lines.append(f"- {entry['tool']}({args}){status} -> {entry['summary']}")
    if not lines:
        return ""
    return (
        "Data you retrieved earlier in this conversation (shortened, and possibly out of date). Use it to "
        "understand follow-up questions; call the tool again if you need fresh or complete data:\n"
        + "\n".join(lines)
    )
