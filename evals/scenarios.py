"""Evaluation scenarios for the assistant, run against the real model through POST /chat.

Each scenario: who asks (a seeded dataset user), the question, what the answer must satisfy. `tools` is a list of
alternatives, any one of which is acceptable; `checks` names the text checks in evals/checks.py.
"""

# Seeded dataset users: (email, password, tier). The password is the first and last name, in lowercase.
USERS = {
    "full": ("elena.fabbri@valgrande.example", "elenafabbri", "full"),  # CMP-001 (EUR)
    "technician": ("matteo.bonetti@valgrande.example", "matteobonetti", "technician"),  # CMP-001
    "commercial": ("davide.ranieri@valgrande.example", "davideranieri", "commercial"),  # CMP-001
    "full_gbp": ("fiona.drummond@kilbrannan.example", "fionadrummond", "full"),  # CMP-004 (GBP records)
}

M1 = "MCH-0001"

SCENARIOS = [
    # --- technical, grounded in tools
    dict(id="fleet", user="technician", machine=None, q="What machines does my company have?", tools=[["get_company_machines"]]),
    dict(id="machine_details", user="commercial", machine=M1, q="When was this machine delivered and how is it configured?", tools=[["get_machine_details"]]),
    dict(id="snapshot", user="technician", machine=M1, q="Is my machine running right now?", tools=[["get_latest_telemetry_snapshot"]]),
    dict(id="trend", user="technician", machine=M1, q="How has this machine's uptime trended over the last month?", tools=[["get_telemetry_summary"]], forbid=["get_telemetry_history"]),
    dict(id="why_alarming", user="technician", machine=M1, q="Why does this machine keep alarming?", tools=[["get_alarm_summary"], ["get_manual_excerpts"]], checks=["cites_manual"]),
    # manual-guided diagnosis: the manual says what to look at and how to read it
    dict(id="explain_alarms", user="technician", machine="MCH-0002", q="Explain my open alarms and tell me what I should check.", tools=[["get_alarm_summary", "get_alarm_history"], ["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="temp_normal", user="technician", machine=M1, q="Is this machine's operating temperature normal?", tools=[["get_latest_telemetry_snapshot", "get_telemetry_summary"], ["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="health", user="technician", machine=M1, q="Is my machine healthy? What should I worry about?", tools=[["get_latest_telemetry_snapshot", "get_telemetry_summary"], ["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="low_output", user="technician", machine=M1, q="Its production seems lower than it should be. What could explain it?", tools=[["get_telemetry_summary", "get_latest_telemetry_snapshot"], ["get_machine_details"], ["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="open_alarms", user="technician", machine=M1, q="Do I have any open alarms on this machine?", tools=[["get_alarm_summary", "get_alarm_history"]]),
    dict(id="tickets_company", user="technician", machine=None, q="List my company's open maintenance tickets.", tools=[["get_company_maintenance_tickets"]]),
    dict(id="tickets_machine", user="technician", machine=M1, q="What recent maintenance tickets did this machine have, and were they triggered by alarms?", tools=[["get_maintenance_history"]]),
    # --- manuals: how-to questions must be answered from the manual
    dict(id="alarm_meaning", user="technician", machine=M1, q="What does a 'low air pressure' alarm mean and how do I fix it?", tools=[["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="spare_parts", user="technician", machine=M1, q="How do I order spare parts for this machine?", tools=[["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="safety", user="technician", machine=M1, q="What safety precautions must I take before maintenance?", tools=[["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="interval", user="technician", machine=M1, q="What maintenance is due every 6000 working hours?", tools=[["get_manual_excerpts"]], checks=["cites_manual"]),
    dict(id="manual_commercial", user="commercial", machine=M1, q="How do I order spare parts for this machine?", tools=[["get_manual_excerpts"]], checks=["cites_manual"]),
    # --- commercial
    dict(id="quotes", user="commercial", machine=None, q="What quotes has my company received?", tools=[["get_company_quotes"]], checks=["currency_eur"]),
    dict(id="latest_revision", user="commercial", machine=None, q="What is the latest revision of quote QTE-2025-0001 and what changed?", tools=[["get_latest_quote_revision", "get_quote_revisions"]]),
    dict(id="quote_lines", user="full", machine=None, q="What does the latest revision of quote QTE-2025-0001 include, and how much does it cost?", tools=[["get_quote_lines"]], checks=["currency_eur"]),
    dict(id="order_status", user="commercial", machine=None, q="What is the status of order ORD-2025-0001?", tools=[["get_order_details"]]),
    dict(id="quote_to_order", user="commercial", machine=None, q="Did quote QTE-2025-0001 become an order?", tools=[["get_orders_by_quote", "get_company_orders"]]),
    dict(id="cross_domain", user="full", machine=M1, q="For my company's latest quote, what does it include, and what maintenance tickets did this machine have recently?", tools=[["get_quote_lines"], ["get_maintenance_history", "get_company_maintenance_tickets"]]),
    dict(id="gbp_currency", user="full_gbp", machine=None, q="Show me the lines of the latest revision of quote QTE-2025-0002 with their prices.", tools=[["get_quote_lines"]], checks=["currency_gbp"]),
    # --- access: the wrong tier must be refused plainly, with no tools
    dict(id="refuse_quotes", user="technician", machine=M1, q="What quotes has my company received?", tools=[], expect_no_tools=True, checks=["refusal"]),
    dict(id="refuse_alarms", user="commercial", machine=M1, q="Any open alarms on this machine?", tools=[], expect_no_tools=True, checks=["refusal"]),
    # --- behaviour rules
    dict(id="english", user="technician", machine=None, q="Quali macchine ha la mia azienda?", tools=[["get_company_machines"]], checks=["english"]),
    dict(id="needs_machine", user="technician", machine=None, q="Do I have any open alarms?", tools=[], checks=["asks_or_checks_all"], skip=["no_offer"]),  # asking which machine, or checking all of them, are both fine
    dict(id="out_of_scope", user="technician", machine=M1, q="Write me a short poem about the sea.", tools=[], expect_no_tools=True, checks=["declines"]),
]

# Applied to every answer, whatever the scenario.
ALWAYS = ["ascii_ids", "no_offer"]
