"""Shared row-capping helper for tools whose result sets can grow unbounded.

Capping must never leave the caller silently confident about incomplete data --
every capped result says so explicitly and includes a boundary timestamp to
narrow further from.
"""

from __future__ import annotations

from typing import Any


def cap_rows(rows: list[dict[str, Any]], max_rows: int, timestamp_field: str) -> dict[str, Any]:
	"""Cap a list of rows (already fetched with LIMIT max_rows + 1) to max_rows.

	`rows` is expected ordered most-recent-first; the oldest included row's
	timestamp is surfaced so a caller can narrow `until` to page further back.
	"""
	truncated = len(rows) > max_rows
	kept = rows[:max_rows]
	return {
		"rows": kept,
		"returned_count": len(kept),
		"truncated": truncated,
		"oldest_included_timestamp": kept[-1][timestamp_field] if kept else None,
	}
