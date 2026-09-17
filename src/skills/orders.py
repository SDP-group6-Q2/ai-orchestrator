"""Orders skill: confirmed orders and fulfillment status."""

from __future__ import annotations

from src.skills.base import Skill
from src.tools.orders_tools import (
    get_order_details,
    get_order_lines,
    get_orders_by_quote,
    get_company_orders,
)

orders_skill = Skill(
    name="orders",
    description="Confirmed orders, fulfillment lines, and shipment status for the current company.",
    instructions=(
        "Use get_order_details for information about a specific order, including orderStatus, "
        "shipmentStatus, dates and originating quote.\n"
        "Use get_order_lines for fulfillment information about an order.\n"
        "Use get_orders_by_quote to find orders generated from a quote.\n"
        "Use get_company_orders to retrieve orders associated with the current company.\n\n"
        "Orders reference their originating quote through quoteId. Order lines contain fulfillment "
        "status only -- they do not contain item descriptions, quantities or prices. If the user asks "
        "about the commercial contents or price of an order, retrieve the associated quote, its "
        "relevant revision and its quote lines."
    ),
    tools=[
        get_order_details,
        get_order_lines,
        get_orders_by_quote,
        get_company_orders,
    ],
)
