"""Fleet inventory helpers used by the technical agent.

Purpose-built, parameterized queries (mirroring src/tools/quotes_tools.py's
`_for_company` pattern) instead of freeform LLM-authored SQL: each tool is
scoped to the requesting user's company via runtime.context, verified
server-side against the real `machines` table rather than trusting an
LLM-authored WHERE clause.
"""

from __future__ import annotations
import logging

from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.context import AgentContext
from src.db.db import get_db
from src.security.access import (
    ACCESS_DENIED_OR_UNAVAILABLE,
    can_access_machine_identity,
    get_user_context,
)

logger = logging.getLogger(__name__)


def _authorized_company_id(runtime: ToolRuntime[AgentContext]) -> str | None:
    """Machines/MachineModels are machine identity data -- per spec, visible to
    every visibility tier scoped to the user's own company, not just technical
    users."""
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_machine_identity(user_context):
        return None
    return user_context["companyid"]


_MACHINE_COLUMNS = """
        m.machineid,
        m.companyid,
        m.modelid,
        m.serialnumber,
        m.deliverydate,
        m.plantlocation,
        m.configurationprofile,
        m.plcfamily,
        m.softwareversion,
        mm.modelcode,
        mm.description AS model_description,
        mm.containertype,
        mm.captype,
        mm.industrysegment,
        mm.primitivediameter,
        mm.nominalheads
"""


@tool
def get_company_machines(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return every machine belonging to the current user's company, including its model details."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = f"""
        SELECT {_MACHINE_COLUMNS}
        FROM machines m
        LEFT JOIN machinemodels mm ON mm.modelid = m.modelid
        WHERE m.companyid = %s
        ORDER BY m.machineid;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company_id,))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_machine_details(machine_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return details (including model) of a machine belonging to the current user's company."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = f"""
        SELECT {_MACHINE_COLUMNS}
        FROM machines m
        LEFT JOIN machinemodels mm ON mm.modelid = m.modelid
        WHERE m.machineid = %s
          AND m.companyid = %s
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (machine_id, company_id))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)
