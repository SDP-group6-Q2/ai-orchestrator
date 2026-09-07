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
            "quoteId",
            "companyId",
            "currency",
            "createdAt",
            "validUntil",
            "description"
        FROM quotes
        WHERE "quoteId" = %s
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
            "quoteRevisionId",
            "quoteId",
            "revisionNumber",
            "revisionStatus",
            "issuedAt",
            "discountRate",
            "changeSummary"
        FROM quoterevisions
        WHERE "quoteId" = %s
        ORDER BY "revisionNumber" ASC;
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
            "quoteLineId",
            "quoteRevisionId",
            "machineId",
            "price",
            "description"
        FROM quotelines
        WHERE "quoteRevisionId" = %s;
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
            "quoteId",
            "companyId",
            "currency",
            "createdAt",
            "validUntil",
            "description"
        FROM quotes
        WHERE "companyId" = %s
        ORDER BY "createdAt" DESC;
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
            "quoteRevisionId",
            "quoteId",
            "revisionNumber",
            "revisionStatus",
            "issuedAt",
            "discountRate",
            "changeSummary"
        FROM quoterevisions
        WHERE "quoteId" = %s
        ORDER BY "revisionNumber" DESC
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
            "quoteId",
            "companyId",
            "currency",
            "createdAt",
            "validUntil",
            "description"
        FROM quotes
        WHERE "quoteId" = %s
          AND "companyId" = %s
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
            qr."quoteRevisionId",
            qr."quoteId",
            qr."revisionNumber",
            qr."revisionStatus",
            qr."issuedAt",
            qr."discountRate",
            qr."changeSummary"
        FROM quoterevisions qr
        JOIN quotes q
            ON q."quoteId" = qr."quoteId"
        WHERE qr."quoteId" = %s
          AND q."companyId" = %s
        ORDER BY qr."revisionNumber" ASC;
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
            qr."quoteRevisionId",
            qr."quoteId",
            qr."revisionNumber",
            qr."revisionStatus",
            qr."issuedAt",
            qr."discountRate",
            qr."changeSummary"
        FROM quoterevisions qr
        JOIN quotes q
            ON q."quoteId" = qr."quoteId"
        WHERE qr."quoteId" = %s
          AND q."companyId" = %s
        ORDER BY qr."revisionNumber" DESC
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
            ql."quoteLineId",
            ql."quoteRevisionId",
            ql."machineId",
            ql."price",
            ql."description"
        FROM quotelines ql
        JOIN quoterevisions qr
            ON qr."quoteRevisionId" = ql."quoteRevisionId"
        JOIN quotes q
            ON q."quoteId" = qr."quoteId"
        WHERE ql."quoteRevisionId" = %s
          AND q."companyId" = %s;
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
            "quoteId",
            "companyId",
            "currency",
            "createdAt",
            "validUntil",
            "description"
        FROM quotes
        WHERE "companyId" = %s
        ORDER BY "createdAt" DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (company_id,),
            )

            return [dict(row) for row in cursor.fetchall()]