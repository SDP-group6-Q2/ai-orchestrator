"""Run-scoped identity passed into agent graphs via LangGraph's `context` mechanism.

Unlike `GraphState`, this is never part of the checkpointed graph state and is not LLM-visible or
LLM-modifiable: it is resolved once per call from a trusted caller (`assistant.run`) and read by the
graph nodes and by the MCP client's interceptor (which attaches `token` to every tool call).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    machine_id: str
    visibility: str  # the user's tier: "full" | "technician" | "commercial" (used by the graph's gate)
    token: str = field(repr=False)  # the end user's JWT, forwarded to the MCP server; never logged
