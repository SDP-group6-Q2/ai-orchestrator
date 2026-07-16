"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations

from typing import Protocol, TypedDict


class TelemetryReading(TypedDict):
    machine_id: str
    metric: str
    value: str
    timestamp: str


class TelemetryClient(Protocol):
    """Backend that answers telemetry queries for a machine.

    LocalTelemetryClient is an in-memory placeholder; a future telemetry
    server client can implement this same interface so IotAgent never
    changes when the backend does.
    """

    def query(self, machine_id: str, metric: str | None = None) -> list[TelemetryReading]: ...


_TELEMETRY_LOG: list[TelemetryReading] = [
	{"machine_id": "machine-01", "metric": "temperature", "value": "78.4C", "timestamp": "2026-07-15T08:00:00Z"},
	{"machine_id": "machine-01", "metric": "vibration", "value": "0.02g", "timestamp": "2026-07-15T08:00:00Z"},
	{"machine_id": "machine-02", "metric": "temperature", "value": "65.1C", "timestamp": "2026-07-15T08:00:00Z"},
	{"machine_id": "machine-02", "metric": "uptime", "value": "142h", "timestamp": "2026-07-15T08:00:00Z"},
]


class LocalTelemetryClient:
	"""Placeholder backend returning canned telemetry readings for a machine."""

	def query(self, machine_id: str, metric: str | None = None) -> list[TelemetryReading]:
		readings = [reading for reading in _TELEMETRY_LOG if reading["machine_id"] == machine_id]
		if metric:
			readings = [reading for reading in readings if reading["metric"] == metric]
		return readings
