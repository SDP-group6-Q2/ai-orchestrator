from src.agents.commercial import _SKILLS as COMMERCIAL
from src.agents.technical import _SKILLS as TECHNICAL
from src.skills import compose

# The tools the MCP server exposes (mcp/app/domains/*). Renaming one there must be reflected here.
MCP_TOOLS = {
    "get_company_machines", "get_machine_details", "get_latest_telemetry_snapshot", "get_telemetry_summary",
    "get_telemetry_history", "get_alarm_summary", "get_alarm_history", "get_maintenance_history",
    "get_company_maintenance_tickets", "get_manual_excerpts",
    "get_company_quotes", "get_quote_details", "get_quote_revisions", "get_latest_quote_revision",
    "get_quote_lines", "get_orders_by_quote", "get_company_orders", "get_order_details", "get_order_lines",
}


def test_every_tool_is_covered_by_exactly_one_agent():
    technical = compose("", TECHNICAL)[1]
    commercial = compose("", COMMERCIAL)[1]
    assert len(technical) == 10 and len(commercial) == 9
    assert not set(technical) & set(commercial)
    assert set(technical) | set(commercial) == MCP_TOOLS


def test_compose_concatenates_instructions():
    prompt, _ = compose("BASE", TECHNICAL)
    assert prompt.startswith("BASE") and "get_manual_excerpts" in prompt
