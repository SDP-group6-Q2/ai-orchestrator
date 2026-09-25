"""Run-scoped identity passed into the agent via LangGraph's `context` mechanism.

Unlike the agent's message state, this is never checkpointed and is not LLM-visible or LLM-modifiable: it is
resolved once per call from a trusted caller (`assistant.run`) and read by the tier middleware (which decides
which tools the model sees) and by the MCP client's interceptor (which attaches `token` to every tool call).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    machine_id: str | None  # None when the question is not about a specific machine
    visibility: str  # the user's tier: "full" | "technician" | "commercial" (used by the graph's gate)
    token: str = field(repr=False)  # the end user's JWT, forwarded to the MCP server; never logged
