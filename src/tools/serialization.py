"""JSON-safety helpers for tool return values built from raw DB rows.

psycopg2 rows carry datetime/Decimal values that json.dumps can't serialize --
without this, LangChain's tool-output formatting silently falls back to a
Python repr (str(dict)) instead of JSON, which is both uglier for the model
to read and impossible to reliably json.loads() back into structured data.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _json_safe_value(value: Any) -> Any:
	if isinstance(value, (datetime, date)):
		return value.isoformat()
	if isinstance(value, Decimal):
		return float(value)
	return value


def json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
	return {key: _json_safe_value(value) for key, value in row.items()}
