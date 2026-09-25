---
name: orders
description: "Confirmed orders, their fulfilment lines and shipment status for the current company."
visibility: [full, commercial]
tools:
  - get_company_orders
  - get_order_details
  - get_order_lines
  - get_orders_by_quote
---
Vocabulary: order status is Confirmed, In production, Delivered or Closed. Shipment status is In production, Ready for shipment, Delivered or Installed. A fulfilment line is Manufacturing, Ready for shipment or Delivered.

Order lines track fulfilment only: they carry no item, quantity or price. What was ordered comes from the originating quote: get the order (get_order_details) for its quote id, then that quote's approved revision and its lines (quotes skill). The order carries its own currency (EUR, or GBP for some orders): state amounts in it as recorded.

For "is it late": compare the expected delivery date with today's date, and treat Delivered, Installed and Closed as done. An order always comes from a quote, but a quote may never have become an order.
