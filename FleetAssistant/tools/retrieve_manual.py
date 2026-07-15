"""Manual retrieval helpers used by the manuals agent."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ManualExcerpt(TypedDict):
    source: str
    snippet: str


class ManualRetriever(Protocol):
    """Backend that turns a query into manual excerpts for the LLM to read.

    LocalManualRetriever is an in-memory placeholder; a future MCP-backed
    retriever can implement this same interface so ManualsAgent never
    changes when the retrieval source does.
    """

    def retrieve(self, query: str, *, limit: int = 3) -> list[ManualExcerpt]: ...


_MANUAL_CORPUS: list[ManualExcerpt] = [
	{
		"source": "manuals/maintenance-basics",
		"snippet": "Check the lubrication schedule, inspect belts and reset the machine only after the fault is cleared.",
	},
	{
		"source": "manuals/error-codes",
		"snippet": "E204 usually indicates a safety interlock or door sensor problem on the production line machine.",
	},
	{
		"source": "manuals/startup-guide",
		"snippet": "Power on the controller, verify the emergency stop is released, and confirm the home sequence completes.",
	},
	{
		"source": "manuals/calibration",
		"snippet": "When readings drift, run the sensor calibration routine and validate against the reference load.",
	},
]


class LocalManualRetriever:
	"""Placeholder backend that hands the LLM canned manual content.

	Leaves relevance filtering to the LLM rather than pre-ranking locally,
	matching how a real (e.g. MCP) retrieval backend would just return
	documents for the model to read.
	"""

	def retrieve(self, query: str, *, limit: int = 3) -> list[ManualExcerpt]:
		return _MANUAL_CORPUS[:limit]
