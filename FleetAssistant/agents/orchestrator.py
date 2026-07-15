"""Class-based orchestrator for the FleetAssistant graph."""

from __future__ import annotations

import json
import logging
import os

import ollama

from FleetAssistant.state import GraphState, PlanStep

logger = logging.getLogger(__name__)

_MAX_AGENT_STEPS = 3

_AGENT_NODES = ("manuals_agent", "iot_agent")
_ALL_NODES = (*_AGENT_NODES, "synthetizer")

_SYSTEM_PROMPT = (
	"You are the orchestrator for a FleetAssistant workflow. "
	"Decide the next step based on the user request, the planned steps so far, "
	"and the previous agent requests and responses. "
	"Choose manuals_agent for questions about documentation, procedures or error-code meanings. "
	"Choose iot_agent for questions that need live telemetry or sensor readings from the machine. "
	"Choose synthetizer once the current evidence is enough to answer the user. "
	"When choosing an agent, rewrite the next agent request to be as specific as possible. "
	"Return only JSON with keys next_node, agent_request, rationale."
)

_RESPONSE_SCHEMA = {
	"type": "object",
	"properties": {
		"next_node": {"type": "string", "enum": list(_ALL_NODES)},
		"agent_request": {"type": "string"},
		"rationale": {"type": "string"},
	},
	"required": ["next_node", "agent_request", "rationale"],
}


class FleetOrchestrator:
	def __init__(self, model: str | None = None, base_url: str | None = None):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _build_history(self, state: GraphState) -> str:
		lines: list[str] = [f"User request: {state['request']}"]
		for index, call in enumerate(state.get("agent_calls", []), start=1):
			lines.append(f"Step {index} agent request: {call['agent_request']}")
			if call.get("agent_response"):
				lines.append(f"Step {index} agent response: {call['agent_response']}")
		return "\n".join(lines)

	def _max_steps_decision(self) -> PlanStep:
		return {
			"next_node": "synthetizer",
			"agent_request": "",
			"rationale": "Reached the maximum number of agent turns.",
		}

	def _fallback_decision(self, state: GraphState) -> PlanStep:
		if not state.get("agent_calls"):
			return {
				"next_node": "manuals_agent",
				"agent_request": state["request"],
				"rationale": "No agent history yet, so gather manual context first.",
			}

		last_call = state["agent_calls"][-1]
		return {
			"next_node": "synthetizer" if last_call.get("agent_response") else "manuals_agent",
			"agent_request": last_call.get("agent_request") or state["request"],
			"rationale": "Fallback decision based on whether the last agent produced an answer.",
		}

	def _decide_next_step(self, state: GraphState) -> tuple[PlanStep, str | None]:
		if len(state.get("agent_calls", [])) >= _MAX_AGENT_STEPS:
			return self._max_steps_decision(), None

		try:
			response = self._client().chat(
				model=self._model,
				messages=[
					{"role": "system", "content": _SYSTEM_PROMPT},
					{"role": "user", "content": self._build_history(state)},
				],
				format=_RESPONSE_SCHEMA,
				options={"temperature": 0},
			)
			content = response["message"]["content"]
			parsed = json.loads(content)
			next_node = parsed.get("next_node")
			agent_request = parsed.get("agent_request") or state["request"]
			rationale = parsed.get("rationale") or ""
			if next_node not in _ALL_NODES:
				raise ValueError(f"unexpected next node: {next_node!r}")
			return {
				"next_node": next_node,
				"agent_request": agent_request,
				"rationale": rationale,
			}, None
		except Exception as exc:
			logger.warning("Orchestrator LLM planning failed, falling back to heuristics", exc_info=True)
			return self._fallback_decision(state), f"Orchestrator planning failed, used fallback: {exc}"

	def run(self, state: GraphState) -> GraphState:
		decision, error = self._decide_next_step(state)
		plan = list(state.get("plan", []))
		plan.append(decision)

		if decision["next_node"] in _AGENT_NODES:
			agent_calls = list(state.get("agent_calls", []))
			agent_calls.append(
				{
					"agent_name": decision["next_node"],
					"agent_request": decision["agent_request"],
					"agent_response": "",
				}
			)
			state["agent_calls"] = agent_calls
			state["current_step"] = len(agent_calls)
		else:
			state["current_step"] = len(state.get("agent_calls", []))

		state["plan"] = plan
		state["next_node"] = decision["next_node"]
		state["response"] = state.get("response", "")
		state["error"] = error
		return state
