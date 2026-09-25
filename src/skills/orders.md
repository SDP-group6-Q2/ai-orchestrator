---
name: orders
description: "Confirmed orders, fulfillment lines, and shipment status for the current company."
visibility: [full, commercial]
tools:
  - get_order_details
  - get_order_lines
  - get_orders_by_quote
  - get_company_orders
---
Use get_order_details for information about a specific order, including order status, shipment status, dates and originating quote.
Use get_order_lines for fulfillment information about an order.
Use get_orders_by_quote to find orders generated from a quote.
Use get_company_orders to retrieve orders associated with the current company.

Orders reference their originating quote. Order lines contain fulfillment status only -- they do not contain item descriptions, quantities or prices. If the user asks about the commercial contents or price of an order, retrieve the originating quote, its approved revision and that revision's lines.
