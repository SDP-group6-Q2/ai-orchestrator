"""Diagnostics skill: live telemetry, alarms, and maintenance-correlated history."""

from __future__ import annotations

from src.skills.base import Skill
from src.tools import (
    get_latest_telemetry_snapshot,
    get_telemetry_history,
    get_alarm_history,
    get_maintenance_history,
)

diagnostics_skill = Skill(
    name="diagnostics",
    description=(
        "Live sensor readings, error states, cycle counts, and operational health "
        "for a specific machine."
    ),
    instructions=(
        "Use get_latest_telemetry_snapshot for the machine's current operational status, production rate, "
        "uptime, alarm count, temperature, energy usage and health note.\n"
        "Use get_telemetry_history for trends over time or to detect performance degradation, optionally "
        "narrowed with since/until.\n"
        "Use get_alarm_history for the machine's alarms (code, severity, status), optionally narrowed with "
        "since/until.\n"
        "Use get_maintenance_history to correlate alarms with maintenance tickets raised for the machine.\n\n"
        "When answering with diagnostics data: retrieve the relevant telemetry data from the tools and "
        "provide a concise answer with the requested information. Do not provide any interpretation or "
        "conclusions about the data, only present the data itself. If no telemetry data is relevant, say "
        "you cannot answer the question based on the available readings."
    ),
    tools=[
        get_latest_telemetry_snapshot,
        get_telemetry_history,
        get_alarm_history,
        get_maintenance_history,
    ],
)
