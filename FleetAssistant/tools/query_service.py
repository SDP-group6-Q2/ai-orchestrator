"""Service ticket and history retrieval helpers used by the service agent."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ServiceTicket(TypedDict):
    ticket_id: str
    machine_id: str
    status: str
    summary: str


class ServiceVisit(TypedDict):
    visit_id: str
    machine_id: str
    date: str
    summary: str


class ServiceClient(Protocol):
    """Backend that answers service ticket and history queries for a client.

    LocalServiceClient is an in-memory placeholder; a future customer
    service/ticketing system client can implement this same interface so
    ServiceAgent never changes when the backend does.
    """

    def list_tickets(self, user_id: str) -> list[ServiceTicket]: ...

    def list_service_history(self, user_id: str) -> list[ServiceVisit]: ...


_TICKET_LOG: dict[str, list[ServiceTicket]] = {
	"user-01": [
		{
			"ticket_id": "TCK-501",
			"machine_id": "machine-01",
			"status": "open",
			"summary": "Reported abnormal vibration on the main belt.",
		},
		{
			"ticket_id": "TCK-498",
			"machine_id": "machine-01",
			"status": "closed",
			"summary": "E204 door sensor fault, resolved by replacing the interlock switch.",
		},
	],
	"user-02": [
		{
			"ticket_id": "TCK-512",
			"machine_id": "machine-02",
			"status": "open",
			"summary": "Requested onsite inspection for temperature readings drift.",
		},
	],
}

_VISIT_LOG: dict[str, list[ServiceVisit]] = {
	"user-01": [
		{
			"visit_id": "VST-220",
			"machine_id": "machine-01",
			"date": "2026-05-10",
			"summary": "Routine maintenance visit, lubrication and belt inspection.",
		},
	],
	"user-02": [
		{
			"visit_id": "VST-231",
			"machine_id": "machine-02",
			"date": "2026-06-20",
			"summary": "Emergency callout for uptime alarms, controller reset performed.",
		},
	],
}


class LocalServiceClient:
	"""Placeholder backend returning canned service tickets and visit history."""

	def list_tickets(self, user_id: str) -> list[ServiceTicket]:
		return _TICKET_LOG.get(user_id, [])

	def list_service_history(self, user_id: str) -> list[ServiceVisit]:
		return _VISIT_LOG.get(user_id, [])
