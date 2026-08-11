"""Manual retrieval helpers used by the manuals agent."""

from __future__ import annotations

from typing import Protocol, TypedDict

from langchain_core.tools import tool


class ManualExcerpt(TypedDict):
    source: str
    snippet: str



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

@tool 
def get_manual_excerpts(query: str) -> str:
	"""Retrieve relevant manual excerpts for a given query."""
	# For simplicity, return all excerpts that contain any word from the query
	query_words = set(query.lower().split())
	return "\n".join(
		f"- {item['source']}: {item['snippet']}"
		for item in _MANUAL_CORPUS
		if query_words.intersection(item["snippet"].lower().split())
	)