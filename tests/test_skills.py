import pytest

from src.skills import SkillError, load_skills, skills_for, tool_names_for, validate_against_tools
from src.skills.loader import parse_skill

# The tools the MCP server exposes (mcp/app/domains/*). Renaming one there must be reflected in the skills.
MCP_TOOLS = {
    "get_company_machines", "get_machine_details", "get_latest_telemetry_snapshot", "get_telemetry_summary",
    "get_telemetry_history", "get_alarm_summary", "get_alarm_history", "get_maintenance_history",
    "get_company_maintenance_tickets", "get_manual_excerpts",
    "get_company_quotes", "get_quote_details", "get_quote_revisions", "get_latest_quote_revision",
    "get_quote_lines", "get_orders_by_quote", "get_company_orders", "get_order_details", "get_order_lines",
}
VALID = "---\nname: x\ndescription: d\nvisibility: [full]\ntools:\n  - t1\n---\nDo things.\n"


def test_real_skills_cover_every_mcp_tool_exactly_once():
    skills = load_skills()
    claimed = [tool for skill in skills for tool in skill.tools]
    assert sorted(claimed) == sorted(MCP_TOOLS)  # no gaps, no duplicates
    assert validate_against_tools(skills, MCP_TOOLS) == []


@pytest.mark.parametrize("tier, count", [("full", 19), ("technician", 10), ("commercial", 12), (None, 0), ("admin", 0)])
def test_tools_per_tier(tier, count):
    assert len(tool_names_for(load_skills(), tier)) == count


def test_tier_boundaries():
    skills = load_skills()
    technician = tool_names_for(skills, "technician")
    commercial = tool_names_for(skills, "commercial")
    assert "get_company_quotes" not in technician and "get_latest_telemetry_snapshot" in technician
    assert "get_latest_telemetry_snapshot" not in commercial and "get_company_quotes" in commercial
    # machine identity and manuals are visible to every tier
    assert {"get_company_machines", "get_machine_details", "get_manual_excerpts"} <= technician & commercial


def test_skills_for_returns_skill_objects_in_name_order():
    assert [s.name for s in skills_for(load_skills(), "commercial")] == ["fleet", "manuals", "orders", "quotes"]


def test_parse_valid_skill():
    skill = parse_skill(VALID)
    assert (skill.name, skill.tools, skill.instructions) == ("x", ("t1",), "Do things.")
    assert skill.visibility == {"full"}


@pytest.mark.parametrize(
    "text, message",
    [
        ("no frontmatter", "must start with"),
        ("---\nname: x\n", "not closed"),
        ("---\nname: x\n---\nbody", "missing description, visibility, tools"),
        (VALID.replace("[full]", "[full, admin]"), "unknown visibility"),
        (VALID.replace("Do things.", ""), "no instructions"),
        (VALID.replace("tools:\n  - t1", "tools: t1"), "must be lists"),
    ],
)
def test_malformed_skills_fail_loudly(text, message):
    with pytest.raises(SkillError, match=message):
        parse_skill(text, "bad.md")


def test_a_tool_claimed_by_two_skills_fails(tmp_path):
    (tmp_path / "a.md").write_text(VALID)
    (tmp_path / "b.md").write_text(VALID.replace("name: x", "name: y"))
    with pytest.raises(SkillError, match="claimed by both"):
        load_skills(tmp_path)


def test_a_skill_naming_a_missing_tool_fails_and_uncovered_tools_are_reported():
    skills = [parse_skill(VALID)]
    with pytest.raises(SkillError, match="t1"):
        validate_against_tools(skills, ["other"])
    assert validate_against_tools(skills, ["t1", "brand_new"]) == ["brand_new"]
