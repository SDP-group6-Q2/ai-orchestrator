"""Visibility tiers, per the dataset's access model.

Used only for the up-front gate in the graph (see graph.check_access), which stops the model from answering
a whole category of request for a user who may not see it. It is defense-in-depth: the real enforcement is
the API's, applied to every MCP tool call through the user's own token.
"""

from __future__ import annotations

_COMMERCIAL = {"full", "commercial"}  # quotes, orders
_TECHNICAL = {"full", "technician"}  # telemetry, alarms, maintenance tickets
_MACHINE_IDENTITY = {"full", "technician", "commercial"}  # machines, models, manuals: every tier


def can_access_commercial_data(visibility: str | None) -> bool:
    return visibility in _COMMERCIAL


def can_access_technical_data(visibility: str | None) -> bool:
    return visibility in _TECHNICAL


def can_access_machine_identity(visibility: str | None) -> bool:
    return visibility in _MACHINE_IDENTITY
