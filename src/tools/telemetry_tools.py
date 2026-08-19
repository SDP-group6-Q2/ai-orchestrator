"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations
import logging

from langchain_core.tools import tool
import psycopg2
import sqlparse

from src.db.db import get_db

logger = logging.getLogger(__name__)

@tool
def get_telemetry_tables_descriptors():
    """Return the table descriptors for the telemetry readings database."""
    with get_db() as con:
        with con.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("telemetrysnapshots",),
            )
            telemetry_descriptors = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("alarms",),
            )
            alarms_descriptors = [dict(row) for row in cursor.fetchall()]

    return {
        "telemetrysnapshots": telemetry_descriptors,
        "alarms": alarms_descriptors
    }

@tool
def query_telemetry_readings(sql_query) -> list[dict]:
    """Using an SQL statement, query telemetry readings for a given machine and optional metric."""

    # 1. Prevent empty strings or multi-statement injections (e.g., "SELECT 1; DROP TABLE users;")
    statements = [s for s in sqlparse.parse(sql_query) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        return [{"error": "Invalid Query: Exactly one SQL statement is allowed."}]

    # 2. Check the statement type explicitly
    statement = statements[0]
    if statement.get_type() != "SELECT":
        return [{"error": f"Security Alert: Disallowed operation type '{statement.get_type()}'. Only SELECT queries are permitted."}]

    # 3. Safe to execute if it passes the checks
    try:
        with get_db() as con:
            with con.cursor() as cursor:
                cursor.execute(sql_query)
                result = [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as e:
        logger.warning("Query execution failed for %r: %s", sql_query, e)
        return [{"error": f"Query execution failed: {e}"}]

    return result
