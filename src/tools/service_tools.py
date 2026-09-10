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

logger = logging.getLogger(__name__)


def _authorized_company_id(runtime: ToolRuntime[AgentContext]) -> str | None:
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_technical_data(user_context):
        return None
    return user_context["companyid"]


@tool
def get_company_maintenance_tickets(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return every maintenance ticket for machines belonging to the current user's company, newest first."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
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
            mt.ownerrole
        FROM maintenancetickets mt
        JOIN machines m ON m.machineid = mt.machineid
        WHERE m.companyid = %s
        ORDER BY mt.createddate DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company_id,))
            return [dict(row) for row in cursor.fetchall()]
