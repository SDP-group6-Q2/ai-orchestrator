"""FleetAssistant tools."""

from src.tools.orders_tools import (
    get_orders_descriptors,
    query_orders,
    get_order_details,
    get_order_lines,
    get_orders_by_quote,
    get_company_orders,
)

from src.tools.quotes_tools import (
    get_quotes_descriptors,
    query_quotes,
    get_quote_details,
    get_quote_revisions,
    get_quote_lines,
    get_company_quotes,
    get_latest_quote_revision,
)

from src.tools.service_tools import (
    open_new_ticket,
    query_service_tickets,
    get_service_tables_descriptors,
)

from src.tools.telemetry_tools import (
    get_latest_telemetry_snapshot,
    get_telemetry_history,
    get_alarm_history,
    get_maintenance_history,
)

from src.tools.manuals_tools import (
    get_manual_excerpts,
)

from src.tools.fleet_tools import (
    query_fleet,
    get_fleet_descriptors,
)

__all__ = [
    # Orders - legacy / generic
    "get_orders_descriptors",
    "query_orders",
    "get_orders_info",
    "list_contracts",

    # Quotes - legacy / generic
    "get_quotes_descriptors",
    "query_quotes",

    # Commercial - structured quote tools
    "get_quote_details",
    "get_quote_revisions",
    "get_quote_lines",
    "get_company_quotes",
    "get_latest_quote_revision",

    # Commercial - structured order tools
    "get_order_details",
    "get_order_lines",
    "get_orders_by_quote",
    "get_company_orders",

    # Service
    "get_service_tables_descriptors",
    "query_service_tickets",
    "open_new_ticket",

    # Telemetry
    "get_latest_telemetry_snapshot",
    "get_telemetry_history",
    "get_alarm_history",
    "get_maintenance_history",

    # Fleet
    "get_fleet_descriptors",
    "query_fleet",

    # Manuals
    "get_manual_excerpts",
]