"""Skill definitions shared across assistant agents."""

from src.skills.base import Skill, compose
from src.skills.diagnostics import diagnostics_skill
from src.skills.fleet import fleet_skill
from src.skills.maintenance import maintenance_skill
from src.skills.manuals import manuals_skill
from src.skills.orders import orders_skill
from src.skills.quotes import quotes_skill

__all__ = [
    "Skill",
    "compose",
    "diagnostics_skill",
    "fleet_skill",
    "maintenance_skill",
    "manuals_skill",
    "orders_skill",
    "quotes_skill",
]
