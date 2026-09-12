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
def get_order_details(order_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return details of an order accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            orderid AS "orderId",
            quoteid AS "quoteId",
            companyid AS "companyId",
            orderstatus AS "orderStatus",
            orderdate AS "orderDate",
            expecteddeliverydate AS "expectedDeliveryDate",
            shipmentstatus AS "shipmentStatus",
            currency,
            notes
        FROM orders
        WHERE orderid = %s
          AND companyid = %s
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (order_id, company_id))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


@tool
def get_order_lines(order_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return fulfillment lines for an order accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            ol.orderlineid AS "orderLineId",
            ol.orderid AS "orderId",
            ol.fulfillmentstatus AS "fulfillmentStatus"
        FROM orderlines ol
        JOIN orders o
            ON o.orderid = ol.orderid
        WHERE ol.orderid = %s
          AND o.companyid = %s;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (order_id, company_id))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_orders_by_quote(quote_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return orders created from a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            orderid AS "orderId",
            quoteid AS "quoteId",
            companyid AS "companyId",
            orderstatus AS "orderStatus",
            orderdate AS "orderDate",
            expecteddeliverydate AS "expectedDeliveryDate",
            shipmentstatus AS "shipmentStatus",
            currency,
            notes
        FROM orders
        WHERE quoteid = %s
          AND companyid = %s
        ORDER BY orderdate ASC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (quote_id, company_id))
            return [dict(row) for row in cursor.fetchall()]


@tool
def get_company_orders(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return orders belonging to the current user's company."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE

    query = """
        SELECT
            orderid AS "orderId",
            quoteid AS "quoteId",
            companyid AS "companyId",
            orderstatus AS "orderStatus",
            orderdate AS "orderDate",
            expecteddeliverydate AS "expectedDeliveryDate",
            shipmentstatus AS "shipmentStatus",
            currency,
            notes
        FROM orders
        WHERE companyid = %s
        ORDER BY orderdate DESC;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (company_id,))
            return [dict(row) for row in cursor.fetchall()]
