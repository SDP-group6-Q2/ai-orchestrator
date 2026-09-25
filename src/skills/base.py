"""Skill abstraction: a named bundle of prompt instructions + the names of the MCP tools it uses.

The tools themselves are provided by the MCP server (see src/mcp_client.py); a skill only says which of them
it covers and how to use them. Composition is static: every skill passed to an agent is always active,
concatenated into one system prompt and one flat list of tool names at build time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    tool_names: tuple[str, ...]


def compose(base_prompt: str, skills: list[Skill]) -> tuple[str, list[str]]:
    """Concatenate skills' instructions onto a base prompt and flatten their tool names."""
    system_prompt = base_prompt + "\n\n" + "\n\n".join(skill.instructions for skill in skills)
    tool_names = [name for skill in skills for name in skill.tool_names]
    return system_prompt, tool_names
