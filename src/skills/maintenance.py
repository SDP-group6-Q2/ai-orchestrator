"""Maintenance skill: the company's support/maintenance tickets."""

from __future__ import annotations

from src.skills.base import Skill
from src.skills.formatting import render_json_tool_result
from src.tools import get_company_maintenance_tickets

maintenance_skill = Skill(
    name="maintenance",
    description="The current user's company open and past maintenance/support tickets.",
    instructions=(
        "Use get_company_maintenance_tickets to fetch the user's company's open and past support tickets, "
        "optionally narrowed with since/until. It's capped to the most recent tickets and will say so if "
        "truncated -- narrow since/until using the boundary it gives you rather than assuming you've seen "
        "everything.\n\n"
        "Column meanings: ticketType is one of Remote troubleshooting, On-site service, Spare parts "
        "request, Scheduled maintenance, Overhaul, Size change assistance. ticketStatus is one of Open, "
        "In progress, Waiting for parts, Resolved, Closed. priority is one of Critical, High, Medium, Low. "
        "ownerRole is one of Line Operator, Maintenance Man, Plant Maintenance Manager, AROL Technical "
        "Service. A ticket with no alarmId did not originate from an alarm -- that's expected, not "
        "missing data."
    ),
    tools=[get_company_maintenance_tickets],
    tool_renderers={"get_company_maintenance_tickets": render_json_tool_result},
)
