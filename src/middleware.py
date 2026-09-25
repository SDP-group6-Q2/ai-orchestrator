"""Per-request tool and prompt selection by the user's access tier.

One agent holds every MCP tool. For each model call this middleware shows the model only the tools the user's
tier may use, and adds the matching skills' instructions to the system prompt, plus a note on what is NOT
available to this user so the model declines those requests plainly instead of guessing. A tool call for a
hidden tool (a hallucination) is vetoed here without reaching the MCP server.

This is defense-in-depth: the real enforcement is the API's, applied to every tool call with the user's own
token. The tier comes from the trusted caller (`AgentContext.visibility`), never from the model.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain_core.messages import ToolMessage

from src.skills import Skill, skills_for, tool_names_for

_UNAVAILABLE_ADVICE = (
    "this user's access tier ({tier}) does not include it. If asked about it, tell the user plainly that they "
    "don't have access to this information; never answer it from earlier messages or general knowledge."
)


def render_skills(skills: Sequence[Skill], visibility: str | None) -> str:
    """The system-prompt section for this tier: allowed skills' instructions, then what is unavailable."""
    allowed = skills_for(skills, visibility)
    blocked = [skill for skill in skills if skill not in allowed]
    sections = ["## What you can do for this user"]
    sections += [f"### {skill.name}\n{skill.instructions}" for skill in allowed]
    if not allowed:
        sections.append("No tools are available to this user.")
    if blocked:
        advice = _UNAVAILABLE_ADVICE.format(tier=visibility)
        sections.append(
            "## Not available to this user\n"
            + "\n".join(f"- {skill.description}: {advice}" for skill in blocked)
            + "\nOnly the areas listed here are off limits. Everything else, including everything under \"What you "
            "can do for this user\", IS available to this user: use your tools for it and never refuse it."
        )
    return "\n\n".join(sections)


class TierSkillsMiddleware(AgentMiddleware):
    def __init__(self, skills: Sequence[Skill]):
        super().__init__()
        self.skills = list(skills)

    @staticmethod
    def _visibility(runtime: object) -> str | None:
        return getattr(getattr(runtime, "context", None), "visibility", None)

    async def awrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable]):
        visibility = self._visibility(request.runtime)
        allowed = tool_names_for(self.skills, visibility)
        tools = [tool for tool in request.tools if getattr(tool, "name", None) in allowed]
        prompt = f"{request.system_prompt or ''}\n\n{render_skills(self.skills, visibility)}".strip()
        return await handler(request.override(tools=tools, system_prompt=prompt))

    async def awrap_tool_call(self, request, handler):
        name = request.tool_call["name"]
        if name not in tool_names_for(self.skills, self._visibility(request.runtime)):
            return ToolMessage(
                content="Access denied: this tool is not available to the current user.",
                tool_call_id=request.tool_call["id"],
                name=name,
                status="error",
            )
        return await handler(request)
