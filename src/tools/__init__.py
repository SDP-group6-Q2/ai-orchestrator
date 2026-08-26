"""FleetAssistant tools."""

from src.tools.orders_tools import (
    get_orders_info,
    list_contracts
)
from src.tools.service_tools import (
    open_new_ticket,
    query_service_tickets,
    get_service_tables_descriptors
)
from src.tools.telemetry_tools import (
    query_telemetry_readings,
    get_telemetry_tables_descriptors
)
from src.tools.manuals_tools import (
   get_manual_excerpts
)
from src.tools.fleet_tools import (
    query_fleet,
    get_fleet_descriptors
)

__all__ = [
    "get_orders_info",
    "list_contracts",
    "get_service_tables_descriptors",
    "query_service_tickets",
    "open_new_ticket",
    "query_telemetry_readings",
    "get_telemetry_tables_descriptors",
    "get_fleet_descriptors",
    "query_fleet",
    "get_manual_excerpts",
]