"""Skill abstraction: a named bundle of prompt instructions + tools.

Composition is static — every skill passed to an agent is always active,
concatenated into one system prompt and one flat tool list at build time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    tools: list[BaseTool]
    tool_renderers: dict[str, Callable[[ToolMessage], str | None]] = field(default_factory=dict)


def compose(base_prompt: str, skills: list[Skill]) -> tuple[str, list[BaseTool]]:
    """Concatenate skills' instructions onto a base prompt and flatten their tools."""
    system_prompt = base_prompt + "\n\n" + "\n\n".join(skill.instructions for skill in skills)
    tools = [tool for skill in skills for tool in skill.tools]
    return system_prompt, tools
