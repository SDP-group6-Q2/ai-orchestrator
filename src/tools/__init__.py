"""FleetAssistant tools."""

from src.tools.orders_tools import (
    get_orders_info,
    list_contracts
)
from src.tools.service_tools import (
    create_service_tables,
    open_new_ticket,
    query_service_tickets,
    get_service_tables_descriptors
)
from src.tools.telemetry_tools import (
    create_telemetry_tables,
    query_telemetry_readings,
    get_telemetry_tables_descriptors
)
from src.tools.manuals_tools import (
   get_manual_excerpts
)

__all__ = [
    "get_orders_info",
    "list_contracts",
    "create_service_tables",
    "get_service_tables_descriptors",
    "query_service_tickets",
    "open_new_ticket",
    "create_telemetry_tables",
    "query_telemetry_readings",
    "get_telemetry_tables_descriptors",
    "get_manual_excerpts",
]