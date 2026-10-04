"""Skills as content: one markdown file per skill under src/skills/.

    ---
    name: quotes
    description: "Quotations, revision history, and quote line items for the current company."
    visibility: [full, commercial]      # the access tiers that may use this skill
    tools:                              # the MCP tools it covers
      - get_company_quotes
    ---
    Instructions for the model...

A skill bundles prompt instructions with the MCP tools they are about and the tiers that may use them. Loading
is strict: a malformed skill, an unknown tier, or a tool claimed by two skills is an error at startup, not a
surprise at runtime.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).parent
VISIBILITIES = frozenset({"full", "technician", "commercial"})


class SkillError(Exception):
    """A skill file is malformed, or skills and MCP tools don't line up."""


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    tools: tuple[str, ...]
    visibility: frozenset[str]


def parse_skill(text: str, source: str = "<skill>") -> Skill:
    if not text.startswith("---"):
        raise SkillError(f"{source}: a skill must start with '---' frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillError(f"{source}: frontmatter is not closed with '---'")
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as error:
        raise SkillError(f"{source}: invalid frontmatter: {error}") from error
    if not isinstance(meta, dict):
        raise SkillError(f"{source}: frontmatter must be a mapping")

    missing = [key for key in ("name", "description", "visibility", "tools") if not meta.get(key)]
    if missing:
        raise SkillError(f"{source}: missing {', '.join(missing)}")
    tiers = meta["visibility"]
    tools = meta["tools"]
    if not isinstance(tiers, list) or not isinstance(tools, list):
        raise SkillError(f"{source}: visibility and tools must be lists")
    unknown = set(tiers) - VISIBILITIES
    if unknown:
        raise SkillError(f"{source}: unknown visibility tier(s): {', '.join(sorted(map(str, unknown)))}")
    instructions = parts[2].strip()
    if not instructions:
        raise SkillError(f"{source}: no instructions")
    return Skill(str(meta["name"]), str(meta["description"]), instructions, tuple(map(str, tools)), frozenset(tiers))


def load_skills(directory: Path = SKILLS_DIR) -> list[Skill]:
    """Every *.md skill in the directory, sorted by name."""
    skills = [parse_skill(path.read_text(), path.name) for path in sorted(directory.glob("*.md"))]
    names = [skill.name for skill in skills]
    if len(set(names)) != len(names):
        raise SkillError("Two skills share a name.")
    owners: dict[str, str] = {}
    for skill in skills:
        for tool in skill.tools:
            if tool in owners:
                raise SkillError(f"Tool {tool} is claimed by both {owners[tool]} and {skill.name}.")
            owners[tool] = skill.name
    return skills


def skills_for(skills: Iterable[Skill], visibility: str | None) -> list[Skill]:
    """The skills a user of this tier may use (none for an unknown tier)."""
    return [skill for skill in skills if visibility in skill.visibility]


def tool_names_for(skills: Iterable[Skill], visibility: str | None) -> set[str]:
    return {tool for skill in skills_for(skills, visibility) for tool in skill.tools}


def validate_against_tools(skills: Iterable[Skill], available: Iterable[str]) -> list[str]:
    """Fail if a skill names a tool the MCP server doesn't have. Returns the server's tools no skill covers
    (they have no instructions, so they are not offered to the model; the caller should warn about them)."""
    available = set(available)
    covered = {tool for skill in skills for tool in skill.tools}
    missing = sorted(covered - available)
    if missing:
        raise SkillError(f"Skills name tools the MCP server doesn't have: {', '.join(missing)}")
    return sorted(available - covered)
