from __future__ import annotations

import logging

import psycopg2
import sqlparse
from langchain_core.tools import tool

from src.db.db import get_db


logger = logging.getLogger(__name__)


@tool
def get_quotes_descriptors():
    """Return the table descriptors for the quotes database."""

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("quotes",),
            )
            quotes_descriptors = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("quoterevisions",),
            )
            quoterevisions_descriptors = [
                dict(row) for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("quotelines",),
            )
            quotelines_descriptors = [
                dict(row) for row in cursor.fetchall()
            ]

            return {
                "quotes": quotes_descriptors,
                "quoterevisions": quoterevisions_descriptors,
                "quotelines": quotelines_descriptors,
            }


@tool
def query_quotes(sql_query: str) -> list[dict]:
    """
    Query quote-related tables using a single read-only SELECT statement.
    """

    logger.info("Querying quotes with SQL: %s", sql_query)

    # Prevent empty queries and multiple SQL statements.
    statements = [
        statement
        for statement in sqlparse.parse(sql_query)
        if statement.token_first(skip_cm=True) is not None
    ]

    if len(statements) != 1:
        return [
            {
                "error": (
                    "Invalid Query: Exactly one SQL statement is allowed."
                )
            }
        ]

    statement = statements[0]

    # Only SELECT queries are permitted.
    if statement.get_type() != "SELECT":
        return [
            {
                "error": (
                    "Security Alert: Disallowed operation type "
                    f"'{statement.get_type()}'. "
                    "Only SELECT queries are permitted."
                )
            }
        ]

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                return [dict(row) for row in cursor.fetchall()]

    except psycopg2.Error as exc:
        logger.warning(
            "Query execution failed for %r: %s",
            sql_query,
            exc,
        )

        return [
            {
                "error": f"Query execution failed: {exc}"
            }
        ]


@tool
def get_quote_details(quote_id: str) -> dict | None:
    """
    Return the main details of a quote.

    Args:
        quote_id: Quote identifier, for example QTE-2025-0001.
    """

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
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


@tool
def get_quote_revisions(quote_id: str) -> list[dict]:
    """
    Return all revisions of a quote ordered from oldest to newest.

    Args:
        quote_id: Quote identifier, for example QTE-2025-0001.
    """

    query = """
        SELECT
            quoterevisionid AS "quoteRevisionId",
            quoteid AS "quoteId",
            revisionnumber AS "revisionNumber",
            revisionstatus AS "revisionStatus",
            issuedat AS "issuedAt",
            discountrate AS "discountRate",
            changesummary AS "changeSummary"
        FROM quoterevisions
        WHERE quoteid = %s
        ORDER BY revisionnumber ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id,))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_quote_lines(quote_revision_id: str) -> list[dict]:
    """
    Return the commercial lines belonging to a quote revision.

    Args:
        quote_revision_id: Quote revision identifier.
    """

    query = """
        SELECT
            quotelineid AS "quoteLineId",
            quoterevisionid AS "quoteRevisionId",
            machineid AS "machineId",
            price,
            description
        FROM quotelines
        WHERE quoterevisionid = %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_revision_id,))
            return [dict(row) for row in cursor.fetchall()]

@tool
def get_company_quotes(company_id: str) -> list[dict]:
    """
    Return all quotes belonging to a company.

    Args:
        company_id: Company identifier.
    """

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
def get_latest_quote_revision(quote_id: str) -> dict | None:
    """
    Return the latest revision of a quote.

    Args:
        quote_id: Quote identifier.
    """

    query = """
        SELECT
            quoterevisionid AS "quoteRevisionId",
            quoteid AS "quoteId",
            revisionnumber AS "revisionNumber",
            revisionstatus AS "revisionStatus",
            issuedat AS "issuedAt",
            discountrate AS "discountRate",
            changesummary AS "changeSummary"
        FROM quoterevisions
        WHERE quoteid = %s
        ORDER BY revisionnumber DESC
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)

def get_quote_details_for_company(
    quote_id: str,
    company_id: str,
) -> dict | None:
    """
    Return a quote only if it belongs to the specified company.
    """

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
            cursor.execute(
                query,
                (quote_id, company_id),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


def get_quote_revisions_for_company(
    quote_id: str,
    company_id: str,
) -> list[dict]:
    """
    Return quote revisions only if the quote belongs to the specified company.
    """

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
            cursor.execute(
                query,
                (quote_id, company_id),
            )

            return [dict(row) for row in cursor.fetchall()]


def get_latest_quote_revision_for_company(
    quote_id: str,
    company_id: str,
) -> dict | None:
    """
    Return the latest quote revision only if the quote belongs to the specified company.
    """

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
            cursor.execute(
                query,
                (quote_id, company_id),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


def get_quote_lines_for_company(
    quote_revision_id: str,
    company_id: str,
) -> list[dict]:
    """
    Return quote lines only if the revision belongs to a quote owned by the specified company.
    """

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
            cursor.execute(
                query,
                (quote_revision_id, company_id),
            )

            return [dict(row) for row in cursor.fetchall()]


def get_company_quotes_secure(
    company_id: str,
) -> list[dict]:
    """
    Return all quotes belonging to the specified company.
    """

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
            cursor.execute(
                query,
                (company_id,),
            )

            return [dict(row) for row in cursor.fetchall()]
