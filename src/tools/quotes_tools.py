from __future__ import annotations

import logging

from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.context import AgentContext
from src.db.db import get_db
from src.security.access import (
    ACCESS_DENIED_OR_UNAVAILABLE,
    can_access_commercial_data,
    get_user_context,
)

logger = logging.getLogger(__name__)


def _authorized_company_id(runtime: ToolRuntime[AgentContext]) -> str | None:
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_commercial_data(user_context):
        return None
    return user_context["companyid"]


@tool
def get_quote_details(quote_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return details of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            quoteid AS "quoteId",
            companyid AS "companyId",
            currency,
            createdat AS "createdAt",
            validuntil AS "validUntil",
            description
        FROM quotes
        WHERE quoteid = %s
          AND companyid = %s
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id, company_id))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


@tool
def get_quote_revisions(quote_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return revisions of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            qr.quoterevisionid AS "quoteRevisionId",
            qr.quoteid AS "quoteId",
            qr.revisionnumber AS "revisionNumber",
            qr.revisionstatus AS "revisionStatus",
            qr.issuedat AS "issuedAt",
            qr.discountrate AS "discountRate",
            qr.changesummary AS "changeSummary"
        FROM quoterevisions qr
        JOIN quotes q
            ON q.quoteid = qr.quoteid
        WHERE qr.quoteid = %s
          AND q.companyid = %s
        ORDER BY qr.revisionnumber ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id, company_id))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_quote_lines(quote_revision_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return quote lines accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            ql.quotelineid AS "quoteLineId",
            ql.quoterevisionid AS "quoteRevisionId",
            ql.machineid AS "machineId",
            ql.price,
            ql.description
        FROM quotelines ql
        JOIN quoterevisions qr
            ON qr.quoterevisionid = ql.quoterevisionid
        JOIN quotes q
            ON q.quoteid = qr.quoteid
        WHERE ql.quoterevisionid = %s
          AND q.companyid = %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_revision_id, company_id))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_company_quotes(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return quotes belonging to the current user's company."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            quoteid AS "quoteId",
            companyid AS "companyId",
            currency,
            createdat AS "createdAt",
            validuntil AS "validUntil",
            description
        FROM quotes
        WHERE companyid = %s
        ORDER BY createdat DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company_id,))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_latest_quote_revision(quote_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return the latest revision of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            qr.quoterevisionid AS "quoteRevisionId",
            qr.quoteid AS "quoteId",
            qr.revisionnumber AS "revisionNumber",
            qr.revisionstatus AS "revisionStatus",
            qr.issuedat AS "issuedAt",
            qr.discountrate AS "discountRate",
            qr.changesummary AS "changeSummary"
        FROM quoterevisions qr
        JOIN quotes q
            ON q.quoteid = qr.quoteid
        WHERE qr.quoteid = %s
          AND q.companyid = %s
        ORDER BY qr.revisionnumber DESC
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id, company_id))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)
