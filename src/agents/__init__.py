"""FleetAssistant agents: a supervisor and its specialist tools."""

from src.agents.diagnostics import make_diagnostics_tool
from src.agents.manuals import make_manuals_tool
from src.agents.orders import make_orders_tool
from src.agents.technical import make_technical_tool
from src.agents.supervisor import make_supervisor_agent

__all__ = [
    "make_diagnostics_tool",
    "make_manuals_tool",
    "make_orders_tool",
    "make_technical_tool",
    "make_supervisor_agent",
]
