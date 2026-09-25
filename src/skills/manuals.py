"""Manuals skill: search of the machine's own use-and-maintenance manual."""

from __future__ import annotations

from src.skills.base import Skill

manuals_skill = Skill(
    name="manuals",
    description=(
        "Search of a machine's own manual -- documentation, operating and maintenance procedures, "
        "troubleshooting and safety."
    ),
    instructions=(
        "Use get_manual_excerpts(machine_id, query) for questions about how the machine works, operating and "
        "maintenance procedures, maintenance intervals, causes and remedies of faults, technical data and "
        "safety. Each manual documents one specific machine, so pass that machine's id. Search one topic per "
        "call, in the user's own words; for an alarm, search its description (e.g. \"low air pressure\"), not "
        "its code.\n"
        "Answer only from the excerpts returned and cite the section and page of each one. If nothing "
        "relevant comes back, say the manual doesn't cover it -- never fill the gap with general knowledge."
    ),
    tool_names=("get_manual_excerpts",),
)
