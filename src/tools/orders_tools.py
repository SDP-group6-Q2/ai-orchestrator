"""Order and contract retrieval helpers used by the orders agent."""

from __future__ import annotations

from langchain_core.tools import tool

@tool
def get_orders_info(user_id: int) -> list[dict]:
	"""Retrieve contract information for a given user."""
	# Mock implementation; replace with actual data retrieval logic
	return [
		{"order_id": "ORD123", "summary": "Order for machine parts", "user_id": user_id},
		{"order_id": "ORD124", "summary": "Order for maintenance services", "user_id": user_id},
	]

@tool
def list_contracts(user_id: int) -> list[dict]:
	"""List the user's active support/service contracts."""
	# Mock implementation; replace with actual data retrieval logic
	return [
		{"contract_id": "CON123", "summary": "Support contract for machine parts", "user_id": user_id},
		{"contract_id": "CON124", "summary": "Service contract for maintenance", "user_id": user_id},
	]