from __future__ import annotations
import logging

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
import psycopg2
import sqlparse

from src.context import AgentContext
from src.db.db import get_db
from src.security.access import (
    ACCESS_DENIED_OR_UNAVAILABLE,
    can_access_technical_data,
    get_user_context,
)

logger = logging.getLogger(__name__)


def _is_authorized(runtime: ToolRuntime[AgentContext]) -> bool:
    user_context = get_user_context(runtime.context.user_id)
    return user_context is not None and can_access_technical_data(user_context)


@tool
def get_fleet_descriptors(runtime: ToolRuntime[AgentContext]):
    """Return the table descriptors for the fleet database."""
    if not _is_authorized(runtime):
        return {"error": ACCESS_DENIED_OR_UNAVAILABLE}
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("machines",),
            )
            machines_descriptors = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("machinemodels",),
            )
            machinemodels_descriptors = [dict(row) for row in cursor.fetchall()]

            return {
                "machines": machines_descriptors,
                "machinemodels": machinemodels_descriptors
            }

@tool
def query_fleet(sql_query, runtime: ToolRuntime[AgentContext]) -> list[dict]:
    """Based on fleet tables descriptors, using an SQL statement, query fleet."""
    if not _is_authorized(runtime):
        return [{"error": ACCESS_DENIED_OR_UNAVAILABLE}]

    logger.info("Querying fleet with SQL: %s", sql_query)

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
