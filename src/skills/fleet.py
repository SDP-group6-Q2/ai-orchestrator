"""Fleet skill: the company's machine directory."""

from __future__ import annotations

from src.skills.base import Skill

fleet_skill = Skill(
    name="fleet",
    description="The current user's company machine directory and model details.",
    instructions=(
        "Use get_company_machines to list every machine belonging to the current user's company, with model, "
        "serial number, plant location and PLC family.\n"
        "Use get_machine_details for one machine's full details and its model: delivery date, as-built "
        "configuration profile, PLC family, software version, container and cap type. Always pass machine_id "
        "explicitly."
    ),
    tool_names=("get_company_machines", "get_machine_details"),
)
