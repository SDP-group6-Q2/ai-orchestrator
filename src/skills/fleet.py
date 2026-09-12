"""Fleet skill: the company's machine directory."""

from __future__ import annotations

from src.skills.base import Skill
from src.tools import get_company_machines, get_machine_details

fleet_skill = Skill(
    name="fleet",
    description="The current user's company machine directory and model details.",
    instructions=(
        "Use get_company_machines to list every machine belonging to the current user's company, "
        "including model details.\n"
        "Use get_machine_details for a specific machine's details (including its model) by machine_id."
    ),
    tools=[get_company_machines, get_machine_details],
)
