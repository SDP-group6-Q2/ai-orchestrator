"""FleetAssistant tools."""

from src.tools.orders_tools import (
    get_order_details,
    get_order_lines,
    get_orders_by_quote,
    get_company_orders,
)

from src.tools.quotes_tools import (
    get_quote_details,
    get_quote_revisions,
    get_quote_lines,
    get_company_quotes,
    get_latest_quote_revision,
)

from src.tools.service_tools import (
    get_company_maintenance_tickets,
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
    get_company_machines,
    get_machine_details,
)

__all__ = [
    # Commercial - quotes
    "get_quote_details",
    "get_quote_revisions",
    "get_quote_lines",
    "get_company_quotes",
    "get_latest_quote_revision",

    # Commercial - orders
    "get_order_details",
    "get_order_lines",
    "get_orders_by_quote",
    "get_company_orders",

    # Service
    "get_company_maintenance_tickets",

    # Telemetry
    "get_latest_telemetry_snapshot",
    "get_telemetry_history",
    "get_alarm_history",
    "get_maintenance_history",

    # Fleet
    "get_company_machines",
    "get_machine_details",

    # Manuals
    "get_manual_excerpts",
]
