from types import SimpleNamespace

import pytest
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from src.context import AgentContext
from src.mcp_client import MissingToolsError, add_user_token, select_tools


def _request(token: str | None, headers=None) -> MCPToolCallRequest:
    context = AgentContext(machine_id="MCH-0001", visibility="full", token=token) if token is not None else None
    return MCPToolCallRequest(
        name="get_company_machines", args={}, server_name="arol", headers=headers, runtime=SimpleNamespace(context=context)
    )


async def test_interceptor_adds_the_users_bearer_token():
    seen = {}

    async def handler(request):
        seen["headers"] = request.headers
        return "ok"

    assert await add_user_token(_request("abc.def", headers={"X-Trace": "1"}), handler) == "ok"
    assert seen["headers"] == {"X-Trace": "1", "Authorization": "Bearer abc.def"}


@pytest.mark.parametrize("token", [None, ""])
async def test_interceptor_refuses_to_call_without_a_token(token):
    async def handler(request):
        raise AssertionError("must not reach the MCP server")

    result = await add_user_token(_request(token), handler)
    assert result.isError and "Not authenticated" in result.content[0].text


def test_token_is_not_in_the_context_repr():
    assert "secret-token" not in repr(AgentContext(machine_id="M", visibility="full", token="secret-token"))


def _tools(*names):
    return [StructuredTool.from_function(lambda: "x", name=name, description=name) for name in names]


def test_select_tools_keeps_the_requested_order():
    selected = select_tools(_tools("b", "a", "c"), ["a", "b"])
    assert [t.name for t in selected] == ["a", "b"]


def test_select_tools_fails_loudly_on_a_missing_tool():
    with pytest.raises(MissingToolsError, match="get_manual_excerpts"):
        select_tools(_tools("a"), ["a", "get_manual_excerpts"])
