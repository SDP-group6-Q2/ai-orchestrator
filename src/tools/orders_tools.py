from __future__ import annotations

import logging

import psycopg2
import sqlparse
from langchain_core.tools import tool

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
            orderlines_descriptors = [
                dict(row) for row in cursor.fetchall()
            ]

            return {
                "orders": orders_descriptors,
                "orderlines": orderlines_descriptors,
            }


@tool
def query_orders(sql_query: str) -> list[dict]:
    """
    Query order-related tables using a single read-only SELECT statement.
    """

    logger.info("Querying orders with SQL: %s", sql_query)

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
def get_order_details(order_id: str) -> dict | str:
    """Return details of an order accessible to the current user."""

    result = get_order_details_for_company(
        order_id,
        company_id,
    )

    if result is None:
        return (
            "ACCESS_DENIED_OR_UNAVAILABLE: "
            "The requested order is not available within the current user's company. "
            "Tell the user that they cannot access commercial information for this "
            "order. Do not say that the order was cancelled, entered incorrectly, "
            "deleted, or does not exist."
        )

    return result


@tool
def get_order_lines(order_id: str) -> list[dict]:
    """
    Return fulfillment information for all lines of an order.

    Args:
        order_id: Order identifier.
    """

    query = """
        SELECT
            "orderLineId",
            "orderId",
            "fulfillmentStatus"
        FROM orderlines
        WHERE "orderId" = %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (order_id,))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_orders_by_quote(quote_id: str) -> list[dict]:
    """
    Return all orders created from a specific quote.

    Args:
        quote_id: Quote identifier.
    """

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
        WHERE "quoteId" = %s
        ORDER BY "orderDate" ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id,))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_company_orders(company_id: str) -> list[dict]:
    """
    Return all orders belonging to a company.

    Args:
        company_id: Company identifier.
    """

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
        WHERE "companyId" = %s
        ORDER BY "orderDate" DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company_id,))
            return [dict(row) for row in cursor.fetchall()]


def get_order_details_for_company(
    order_id: str,
    company_id: str,
) -> dict | None:
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
          AND "companyId" = %s
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (order_id, company_id),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)

def get_order_lines_for_company(
    order_id: str,
    company_id: str,
) -> list[dict]:
    """
    Return order lines only if the order belongs to the specified company.
    """

    query = """
        SELECT
            ol."orderLineId",
            ol."orderId",
            ol."fulfillmentStatus"
        FROM orderlines ol
        JOIN orders o
            ON o."orderId" = ol."orderId"
        WHERE ol."orderId" = %s
          AND o."companyId" = %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (order_id, company_id),
            )

            return [dict(row) for row in cursor.fetchall()]


def get_orders_by_quote_for_company(
    quote_id: str,
    company_id: str,
) -> list[dict]:
    """
    Return orders for a quote only within the specified company.
    """

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
        WHERE "quoteId" = %s
          AND "companyId" = %s
        ORDER BY "orderDate" ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (quote_id, company_id),
            )

            return [dict(row) for row in cursor.fetchall()]


def get_company_orders_secure(
    company_id: str,
) -> list[dict]:
    """
    Return all orders belonging to the specified company.
    """

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
        WHERE "companyId" = %s
        ORDER BY "orderDate" DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                query,
                (company_id,),
            )

            return [dict(row) for row in cursor.fetchall()]