"""Maintenance skill: the company's support/maintenance tickets."""

from __future__ import annotations

from src.skills.base import Skill
from src.skills.formatting import render_json_tool_result
from src.tools import get_company_maintenance_tickets

maintenance_skill = Skill(
    name="maintenance",
    description="The current user's company open and past maintenance/support tickets.",
    instructions=(
        "Use get_company_maintenance_tickets to fetch the user's company's open and past support tickets."
    ),
    tools=[get_company_maintenance_tickets],
    tool_renderers={"get_company_maintenance_tickets": render_json_tool_result},
)
