"""Telemetry retrieval helpers used by the diagnostics agent.

Purpose-built, parameterized queries (mirroring src/tools/quotes_tools.py's
`_for_company` pattern) instead of freeform LLM-authored SQL: each tool takes a
machine_id and verifies, via `machine_lookup`, that the machine belongs to the
requesting user's company before querying -- tenant scoping that a freeform SQL
tool could never safely enforce, since the LLM controls the whole query shape.
"""

from __future__ import annotations
import logging

from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.context import AgentContext
from src.db.db import get_db
from src.security.access import (
    ACCESS_DENIED_OR_UNAVAILABLE,
    can_access_technical_data,
    get_user_context,
)
from src.tools.fleet_directory import machine_lookup
from src.tools.serialization import json_safe_row

logger = logging.getLogger(__name__)


def _authorized_machine(runtime: ToolRuntime[AgentContext], machine_id: str) -> bool:
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_technical_data(user_context):
        return False
    machine = machine_lookup(machine_id)
    return machine is not None and machine["company_id"] == user_context["companyid"]


@tool
def get_latest_telemetry_snapshot(machine_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return the most recent telemetry snapshot (operational status, production rate,
    uptime %, alarm count, temperature, energy usage, health note) for a machine."""
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            telemetryid,
            machineid,
            "timestamp",
            operationalstatus,
            productionratebph,
            uptimepercentage,
            alarmcount,
            temperaturec,
            energykwh,
            healthnote
        FROM telemetrysnapshots
        WHERE machineid = %s
        ORDER BY "timestamp" DESC
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (machine_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return json_safe_row(dict(row))


@tool
def get_telemetry_history(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> list[dict] | str:
    """Return telemetry snapshots for a machine ordered oldest to newest, for trend or
    performance-degradation analysis. Optionally restrict to a time range with `since`/`until`
    (timestamps as they appear in the data, e.g. from a previous tool result)."""
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions = ['machineid = %s']
    params: list[str] = [machine_id]
    if since is not None:
        conditions.append('"timestamp" >= %s')
        params.append(since)
    if until is not None:
        conditions.append('"timestamp" <= %s')
        params.append(until)

    query = f"""
        SELECT
            telemetryid,
            machineid,
            "timestamp",
            operationalstatus,
            productionratebph,
            uptimepercentage,
            alarmcount,
            temperaturec,
            energykwh,
            healthnote
        FROM telemetrysnapshots
        WHERE {' AND '.join(conditions)}
        ORDER BY "timestamp" ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return [json_safe_row(dict(row)) for row in cursor.fetchall()]


@tool
def get_alarm_history(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> list[dict] | str:
    """Return alarms for a machine ordered newest to oldest, including alarm code,
    severity and status. Optionally restrict to a time range with `since`/`until`."""
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions = ['machineid = %s']
    params: list[str] = [machine_id]
    if since is not None:
        conditions.append('"timestamp" >= %s')
        params.append(since)
    if until is not None:
        conditions.append('"timestamp" <= %s')
        params.append(until)

    query = f"""
        SELECT
            alarmid,
            machineid,
            "timestamp",
            alarmcode,
            severity,
            alarmstatus
        FROM alarms
        WHERE {' AND '.join(conditions)}
        ORDER BY "timestamp" DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return [json_safe_row(dict(row)) for row in cursor.fetchall()]


@tool
def get_maintenance_history(machine_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return maintenance tickets for a machine, newest first, each joined with the
    alarm that triggered it (when there is one) -- for correlating alarms with
    maintenance history."""
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            mt.ticketid,
            mt.machineid,
            mt.alarmid,
            mt.tickettype,
            mt.ticketstatus,
            mt.priority,
            mt.createddate,
            mt.ownerrole,
            a.alarmcode,
            a.severity,
            a.alarmstatus,
            a."timestamp" AS alarmtimestamp
        FROM maintenancetickets mt
        LEFT JOIN alarms a ON a.alarmid = mt.alarmid
        WHERE mt.machineid = %s
        ORDER BY mt.createddate DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (machine_id,))
            return [json_safe_row(dict(row)) for row in cursor.fetchall()]
