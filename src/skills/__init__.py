"""Skill definitions shared across FleetAssistant agents."""

from src.skills.base import Skill, compose
from src.skills.diagnostics import diagnostics_skill
from src.skills.fleet import fleet_skill
from src.skills.formatting import render_table, render_tool_tables_middleware
from src.skills.maintenance import maintenance_skill
from src.skills.manuals import manuals_agent, manuals_skill

__all__ = [
    "Skill",
    "compose",
    "diagnostics_skill",
    "fleet_skill",
    "maintenance_skill",
    "manuals_agent",
    "manuals_skill",
    "render_table",
    "render_tool_tables_middleware",
]
