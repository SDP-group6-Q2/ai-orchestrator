"""Order and contract retrieval helpers used by the orders agent."""

from __future__ import annotations

from typing import Protocol, TypedDict


class OrderRecord(TypedDict):
    order_id: str
    machine_id: str
    status: str
    summary: str


class ContractRecord(TypedDict):
    contract_id: str
    summary: str


class OrdersClient(Protocol):
    """Backend that answers order and contract queries for a client.

    LocalOrdersClient is an in-memory placeholder; a future orders/CRM
    server client can implement this same interface so OrdersAgent never
    changes when the backend does.
    """

    def list_orders(self, user_id: str) -> list[OrderRecord]: ...

    def list_contracts(self, user_id: str) -> list[ContractRecord]: ...


_ORDER_LOG: dict[str, list[OrderRecord]] = {
	"user-01": [
		{
			"order_id": "ORD-1001",
			"machine_id": "machine-01",
			"status": "delivered",
			"summary": "Replacement belt kit, delivered 2026-06-02.",
		},
		{
			"order_id": "ORD-1002",
			"machine_id": "machine-01",
			"status": "pending",
			"summary": "Sensor calibration kit, awaiting shipment.",
		},
	],
	"user-02": [
		{
			"order_id": "ORD-2001",
			"machine_id": "machine-02",
			"status": "delivered",
			"summary": "Annual service contract renewal parts.",
		},
	],
}

_CONTRACT_LOG: dict[str, list[ContractRecord]] = {
	"user-01": [
		{"contract_id": "CT-01", "summary": "Gold support plan, 24/7 response, expires 2027-01-01."},
	],
	"user-02": [
		{"contract_id": "CT-02", "summary": "Standard support plan, business hours only, expires 2026-09-15."},
	],
}


class LocalOrdersClient:
	"""Placeholder backend returning canned order and contract records."""

	def list_orders(self, user_id: str) -> list[OrderRecord]:
		return _ORDER_LOG.get(user_id, [])

	def list_contracts(self, user_id: str) -> list[ContractRecord]:
		return _CONTRACT_LOG.get(user_id, [])
