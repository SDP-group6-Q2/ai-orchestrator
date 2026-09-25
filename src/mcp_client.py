"""Connection to the MCP server that provides the agent's tools.

Tools are built once. Each call carries the end user's own JWT (from `AgentContext.token`, set by the caller
of `assistant.run`), so the platform's access rules apply per user: this process holds no credentials and
has no data access of its own.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import CallToolResult, TextContent

from src.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)


class McpUnavailableError(Exception):
    """The MCP server could not be reached or didn't list its tools."""


class MissingToolsError(Exception):
    """An agent needs MCP tools the server doesn't offer (renamed or removed?)."""


async def add_user_token(
    request: MCPToolCallRequest, handler: Callable[[MCPToolCallRequest], Awaitable[object]]
) -> object:
    """Tool-call interceptor: send the caller's JWT as the Authorization header of the MCP request."""
    context = getattr(request.runtime, "context", None)
    token = getattr(context, "token", None)
    if not token:
        # An MCP-style error result, not an exception: the adapter turns it into tool-error text the model can
        # relay, whereas a raised exception would abort the whole request.
        return CallToolResult(
            content=[TextContent(type="text", text="Not authenticated: no user token is available for this request.")],
            isError=True,
        )
    headers = {**(request.headers or {}), "Authorization": f"Bearer {token}"}
    return await handler(request.override(headers=headers))


def _make_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {"arol": {"transport": "streamable_http", "url": MCP_SERVER_URL}},
        tool_interceptors=[add_user_token],
        handle_tool_errors=True,  # access denied / not found reach the model as text, not as a crash
    )


_tools: list[BaseTool] | None = None
_lock = asyncio.Lock()


async def load_tools() -> list[BaseTool]:
    """Every tool the MCP server offers. Loaded on first use and cached; a failed load is retried next time,
    so this process can start before the MCP server is ready."""
    global _tools
    async with _lock:
        if _tools is None:
            try:
                _tools = await _make_client().get_tools()
            except Exception as error:  # connection errors surface as (nested) exception groups
                raise McpUnavailableError(f"Could not load tools from {MCP_SERVER_URL}: {error!r}") from error
            logger.info("Loaded %d MCP tools", len(_tools))
        return _tools


def select_tools(tools: Iterable[BaseTool], names: Iterable[str]) -> list[BaseTool]:
    """The named tools, in the given order. A missing name is an error, not a silent gap."""
    by_name = {tool.name: tool for tool in tools}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise MissingToolsError(f"The MCP server has no tool(s): {', '.join(missing)}")
    return [by_name[name] for name in names]
