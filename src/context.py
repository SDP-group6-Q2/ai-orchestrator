"""Run-scoped identity passed into agent graphs via LangGraph's `context` mechanism.

Unlike `GraphState`, this is never part of the checkpointed graph state and is not
LLM-visible or LLM-modifiable -- it is resolved once per `graph.invoke()` call from a
trusted caller (`FleetAssistant.run`) and read by tools via `ToolRuntime.context`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentContext:
    user_id: str
    machine_id: str | None = None
