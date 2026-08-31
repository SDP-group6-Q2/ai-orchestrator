from __future__ import annotations
import logging

from langchain_core.tools import tool
import psycopg2
import sqlparse

from src.db.db import get_db

logger = logging.getLogger(__name__)


@tool
def get_orders_descriptors():
    """Return the table descriptors for the orders database."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("orders",),
            )
            orders_descriptors = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
                """,
                ("orderlines",),
            )
            orderlines_descriptors = [dict(row) for row in cursor.fetchall()]

            return {
                "orders": orders_descriptors,
                "orderlines": orderlines_descriptors
            }

@tool
def query_orders(sql_query) -> list[dict]:
    """Based on orders tables descriptors, using an SQL statement, query orders."""

    logger.info("Querying orders with SQL: %s", sql_query)

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



@tool
def get_order_details(order_id: str):
    """Return the details and current status of an order."""

    query = """
        SELECT
            "orderId",
            "quoteId",
            "companyId",
            "orderStatus",
            "orderDate",
            "expectedDeliveryDate",
            "shipmentStatus",
            "currency",
            "notes"
        FROM orders
        WHERE "orderId" = %s
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()


@tool
def get_order_lines(order_id: str):
    """Return fulfillment information for the lines of an order."""

    query = """
        SELECT
            "orderLineId",
            "orderId",
            "fulfillmentStatus"
        FROM orderlines
        WHERE "orderId" = %s
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()