"""Telemetry retrieval helpers used by the diagnostics agent.

Purpose-built, parameterized queries (mirroring src/tools/quotes_tools.py's
`_for_company` pattern) instead of freeform LLM-authored SQL: each tool takes a
machine_id and verifies, via `machine_lookup`, that the machine belongs to the
requesting user's company before querying -- tenant scoping that a freeform SQL
tool could never safely enforce, since the LLM controls the whole query shape.

get_telemetry_history/get_alarm_history/get_maintenance_history are capped
(see src/tools/pagination.cap_rows) -- an unbounded get_telemetry_history for
one machine's 30-day history measured at ~73K tokens in a single tool call,
by far the dominant cause of context overflow. get_telemetry_summary/
get_alarm_summary give the common trend/pattern question a much smaller,
aggregated alternative instead of raw rows.
"""

from __future__ import annotations
import logging
from typing import Literal

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
from src.tools.pagination import cap_rows
from src.tools.serialization import json_safe_row

logger = logging.getLogger(__name__)

_MAX_ROWS = 100


def _authorized_machine(runtime: ToolRuntime[AgentContext], machine_id: str) -> bool:
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_technical_data(user_context):
        return False
    machine = machine_lookup(machine_id)
    return machine is not None and machine["company_id"] == user_context["companyid"]


def _time_range_conditions(since: str | None, until: str | None) -> tuple[list[str], list[str]]:
    conditions: list[str] = []
    params: list[str] = []
    if since is not None:
        conditions.append('"timestamp" >= %s')
        params.append(since)
    if until is not None:
        conditions.append('"timestamp" <= %s')
        params.append(until)
    return conditions, params


@tool
def get_latest_telemetry_snapshot(machine_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return the most recent telemetry snapshot (operational status, production rate,
    uptime %, alarm count, temperature, energy usage, health note) for a machine."""
    logger.info(
        "get_latest_telemetry_snapshot called (machine_id=%s, user_id=%s)", machine_id, runtime.context.user_id
    )
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
def get_telemetry_summary(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
    bucket: Literal["day", "week"] = "day",
) -> list[dict] | str:
    """Return per-day/week telemetry aggregates (avg uptime %, avg production rate,
    total alarm count, min/max temperature, avg energy usage, snapshot count) for a
    machine. Use this for trend/pattern questions instead of get_telemetry_history --
    a 30-day month is ~30 rows here versus 720 raw hourly rows there. Optionally
    restrict to a time range with `since`/`until`."""
    logger.info(
        "get_telemetry_summary called (machine_id=%s, user_id=%s, since=%s, until=%s, bucket=%s)",
        machine_id,
        runtime.context.user_id,
        since,
        until,
        bucket,
    )
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions, params = _time_range_conditions(since, until)
    where_clause = " AND ".join(["machineid = %s", *conditions])

    query = f"""
        SELECT
            date_trunc(%s, "timestamp"::timestamp) AS bucket_start,
            AVG(uptimepercentage) AS avg_uptime_percentage,
            AVG(productionratebph) AS avg_production_rate_bph,
            SUM(alarmcount) AS total_alarm_count,
            MIN(temperaturec) AS min_temperature_c,
            MAX(temperaturec) AS max_temperature_c,
            AVG(energykwh) AS avg_energy_kwh,
            COUNT(*) AS snapshot_count
        FROM telemetrysnapshots
        WHERE {where_clause}
        GROUP BY bucket_start
        ORDER BY bucket_start ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [bucket, machine_id, *params])
            return [json_safe_row(dict(row)) for row in cursor.fetchall()]


@tool
def get_telemetry_history(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> dict | str:
    """Return telemetry snapshots for a machine ordered oldest to newest, for inspecting
    a specific window of readings. Optionally restrict to a time range with `since`/`until`
    (timestamps as they appear in the data, e.g. from a previous tool result). Capped at
    the most recent readings -- use get_telemetry_summary instead for trend/pattern
    questions spanning more than a few days."""
    logger.info(
        "get_telemetry_history called (machine_id=%s, user_id=%s, since=%s, until=%s)",
        machine_id,
        runtime.context.user_id,
        since,
        until,
    )
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions, params = _time_range_conditions(since, until)
    where_clause = " AND ".join(["machineid = %s", *conditions])

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
        WHERE {where_clause}
        ORDER BY "timestamp" DESC
        LIMIT %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [machine_id, *params, _MAX_ROWS + 1])
            rows = [json_safe_row(dict(row)) for row in cursor.fetchall()]

    capped = cap_rows(rows, _MAX_ROWS, "timestamp")
    capped["rows"] = list(reversed(capped["rows"]))
    return capped


@tool
def get_alarm_summary(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> list[dict] | str:
    """Return alarm counts grouped by code and severity for a machine (occurrence
    count, first/last seen, how many are still open). Use this to answer "why does
    this machine keep alarming" instead of listing every individual alarm event with
    get_alarm_history. Optionally restrict to a time range with `since`/`until`."""
    logger.info(
        "get_alarm_summary called (machine_id=%s, user_id=%s, since=%s, until=%s)",
        machine_id,
        runtime.context.user_id,
        since,
        until,
    )
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions, params = _time_range_conditions(since, until)
    where_clause = " AND ".join(["machineid = %s", *conditions])

    query = f"""
        SELECT
            alarmcode,
            severity,
            COUNT(*) AS occurrence_count,
            MIN("timestamp") AS first_seen,
            MAX("timestamp") AS last_seen,
            SUM(CASE WHEN alarmstatus = 'Open' THEN 1 ELSE 0 END) AS open_count
        FROM alarms
        WHERE {where_clause}
        GROUP BY alarmcode, severity
        ORDER BY occurrence_count DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [machine_id, *params])
            return [json_safe_row(dict(row)) for row in cursor.fetchall()]


@tool
def get_alarm_history(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> dict | str:
    """Return alarms for a machine ordered newest to oldest, including alarm code,
    severity and status. Optionally restrict to a time range with `since`/`until`.
    Capped at the most recent alarms -- use get_alarm_summary instead for "why does
    this keep happening" style questions."""
    logger.info(
        "get_alarm_history called (machine_id=%s, user_id=%s, since=%s, until=%s)",
        machine_id,
        runtime.context.user_id,
        since,
        until,
    )
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions, params = _time_range_conditions(since, until)
    where_clause = " AND ".join(["machineid = %s", *conditions])

    query = f"""
        SELECT
            alarmid,
            machineid,
            "timestamp",
            alarmcode,
            severity,
            alarmstatus
        FROM alarms
        WHERE {where_clause}
        ORDER BY "timestamp" DESC
        LIMIT %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [machine_id, *params, _MAX_ROWS + 1])
            rows = [json_safe_row(dict(row)) for row in cursor.fetchall()]

    return cap_rows(rows, _MAX_ROWS, "timestamp")


@tool
def get_maintenance_history(
    machine_id: str,
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> dict | str:
    """Return maintenance tickets for a machine, newest first, each joined with the
    alarm that triggered it (when there is one) -- for correlating alarms with
    maintenance history. Optionally restrict to a time range with `since`/`until`
    (matched against the ticket's createdDate). Capped at the most recent tickets."""
    logger.info(
        "get_maintenance_history called (machine_id=%s, user_id=%s, since=%s, until=%s)",
        machine_id,
        runtime.context.user_id,
        since,
        until,
    )
    if not _authorized_machine(runtime, machine_id):
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions: list[str] = []
    params: list[str] = []
    if since is not None:
        conditions.append("mt.createddate >= %s")
        params.append(since)
    if until is not None:
        conditions.append("mt.createddate <= %s")
        params.append(until)
    where_clause = " AND ".join(["mt.machineid = %s", *conditions])

    query = f"""
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
        WHERE {where_clause}
        ORDER BY mt.createddate DESC
        LIMIT %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [machine_id, *params, _MAX_ROWS + 1])
            rows = [json_safe_row(dict(row)) for row in cursor.fetchall()]

    return cap_rows(rows, _MAX_ROWS, "createddate")
