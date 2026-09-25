from dataclasses import dataclass, field, replace
from types import SimpleNamespace

from langchain_core.tools import StructuredTool

from src.context import AgentContext
from src.middleware import TierSkillsMiddleware, render_skills
from src.skills import load_skills

SKILLS = load_skills()


def _tool(name):
    return StructuredTool.from_function(lambda: "x", name=name, description=name)


ALL_TOOLS = [_tool(name) for skill in SKILLS for name in skill.tools]


@dataclass
class FakeModelRequest:
    tools: list
    system_prompt: str | None
    runtime: object
    extra: dict = field(default_factory=dict)

    def override(self, **overrides):
        return replace(self, **overrides)


def _runtime(visibility):
    return SimpleNamespace(context=AgentContext(machine_id="MCH-0001", visibility=visibility, token="t"))


async def _seen_by_model(visibility):
    captured = {}

    async def handler(request):
        captured["request"] = request
        return "response"

    middleware = TierSkillsMiddleware(SKILLS)
    assert await middleware.awrap_model_call(FakeModelRequest(ALL_TOOLS, "BASE", _runtime(visibility)), handler) == "response"
    return captured["request"]


async def test_the_model_only_sees_its_tiers_tools():
    technician = await _seen_by_model("technician")
    names = {t.name for t in technician.tools}
    assert len(names) == 10 and "get_company_quotes" not in names and "get_alarm_summary" in names
    assert len((await _seen_by_model("full")).tools) == 19
    assert len((await _seen_by_model("commercial")).tools) == 12
    assert (await _seen_by_model(None)).tools == []


async def test_prompt_has_base_allowed_skills_and_the_unavailable_note():
    prompt = (await _seen_by_model("technician")).system_prompt
    assert prompt.startswith("BASE")
    assert "Telemetry covers roughly" in prompt  # a diagnostics instruction
    assert "get_quote_revisions" not in prompt  # quotes instructions are not shown to a technician
    assert "Not available to this user" in prompt and "IS available to this user" in prompt
    assert "Quotations, their revision history" in prompt and "access tier (technician)" in prompt


def test_full_tier_has_no_unavailable_section():
    assert "Not available to this user" not in render_skills(SKILLS, "full")


def test_unknown_tier_gets_no_tools_and_everything_declined():
    text = render_skills(SKILLS, "admin")
    assert "No tools are available" in text and "Not available to this user" in text


async def test_a_hidden_tool_call_is_vetoed_without_reaching_mcp():
    async def handler(request):
        raise AssertionError("must not reach the tool")

    request = SimpleNamespace(tool_call={"name": "get_company_quotes", "id": "call-1", "args": {}}, runtime=_runtime("technician"))
    result = await TierSkillsMiddleware(SKILLS).awrap_tool_call(request, handler)
    assert result.status == "error" and result.tool_call_id == "call-1" and "Access denied" in result.content


async def test_an_allowed_tool_call_goes_through():
    async def handler(request):
        return "real result"

    request = SimpleNamespace(tool_call={"name": "get_company_quotes", "id": "call-1", "args": {}}, runtime=_runtime("commercial"))
    assert await TierSkillsMiddleware(SKILLS).awrap_tool_call(request, handler) == "real result"
