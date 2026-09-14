"""Service ticket retrieval helpers used by the technical agent.

Purpose-built, parameterized queries instead of freeform LLM-authored SQL --
tickets are scoped to the requesting user's company by joining through the
`machines` table, verified server-side via runtime.context rather than
trusting an LLM-authored WHERE clause.
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
from src.tools.pagination import cap_rows
from src.tools.serialization import json_safe_row

logger = logging.getLogger(__name__)

_MAX_ROWS = 100


def _authorized_company_id(runtime: ToolRuntime[AgentContext]) -> str | None:
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_technical_data(user_context):
        return None
    return user_context["companyid"]


@tool
def get_company_maintenance_tickets(
    runtime: ToolRuntime[AgentContext],
    since: str | None = None,
    until: str | None = None,
) -> dict | str:
    """Return maintenance tickets for machines belonging to the current user's company,
    newest first. Optionally restrict to a time range with `since`/`until` (matched
    against the ticket's createdDate). Capped at the most recent tickets."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    conditions: list[str] = []
    params: list[str] = []
    if since is not None:
        conditions.append("mt.createddate >= %s")
        params.append(since)
    if until is not None:
        conditions.append("mt.createddate <= %s")
        params.append(until)
    where_clause = " AND ".join(["m.companyid = %s", *conditions])

    query = f"""
        SELECT
            mt.ticketid,
            mt.machineid,
            mt.alarmid,
            mt.tickettype,
            mt.ticketstatus,
            mt.priority,
            mt.createddate,
            mt.ownerrole
        FROM maintenancetickets mt
        JOIN machines m ON m.machineid = mt.machineid
        WHERE {where_clause}
        ORDER BY mt.createddate DESC
        LIMIT %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [company_id, *params, _MAX_ROWS + 1])
            rows = [json_safe_row(dict(row)) for row in cursor.fetchall()]

    return cap_rows(rows, _MAX_ROWS, "createddate")
