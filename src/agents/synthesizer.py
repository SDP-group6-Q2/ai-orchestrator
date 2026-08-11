"""Class-based final synthesizer for FleetAssistant."""

from __future__ import annotations

import logging
import os

import ollama

from src.state import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the synthesizer node for an agentic AI workflow owned by the company AROL, that produces industrial capping machines for their clients."
	"The goal is to provide informed answers to client questions about their machines, using internal documentation and tools."
	"Your task is to integrate the information from the various agents and provide a final, coherent response to the user."
	"Always ensure information is grounded in the agents' outputs and is accurate, concise, and relevant to the user's request."
	"Do not mention internal steps unless they help the user."
	"If no grounded answer can be provided, state that fact clearly. You're allowed to state that you don't know the answer if the agents' outputs are insufficient."
	"You are allowed to request more information from the user if needed."
)


class SynthesizerAgent:
	def __init__(self, model: str | None = None, base_url: str | None = None):
		self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
		self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

	def _client(self) -> ollama.Client:
		return ollama.Client(host=self._base_url)

	def _build_prompt(self, state: GraphState) -> str:
		plan_lines = [f"- {step['next_node']}: {step['agent_request']} ({step['rationale']})" for step in state.get("plan", [])]
		history_lines = [
			f"- {call['agent_name']} | request: {call['agent_request']} | response: {call['agent_response']}"
			for call in state.get("agent_calls", [])
		]
		return (
			f"User request: {state['request']}\n\n"
			f"Orchestrator plan:\n{chr(10).join(plan_lines) if plan_lines else '- none'}\n\n"
			f"Agent history:\n{chr(10).join(history_lines) if history_lines else '- none'}\n\n"
			"Write the final response to the user."
		)

	def _fallback_summary(self, state: GraphState) -> str:
		for call in reversed(state.get("agent_calls", [])):
			if call.get("agent_response"):
				return call["agent_response"]
		return "I could not produce a final answer from the available agent outputs."

	def _generate_summary(self, state: GraphState) -> str:
		try:
			response = self._client().chat(
				model=self._model,
				messages=[
					{"role": "system", "content": _SYSTEM_PROMPT},
					{"role": "user", "content": self._build_prompt(state)},
				],
				options={"temperature": 0.1},
			)
			content = response["message"]["content"].strip()
			if not content:
				raise ValueError("empty response from ollama")
			return content
		except Exception:
			logger.warning("Synthetizer LLM generation failed, using fallback summary", exc_info=True)
			return self._fallback_summary(state)

	def run(self, state: GraphState) -> GraphState:
		logger.info("SynthesizerAgent invoked | %d agent call(s) in history", len(state.get("agent_calls", [])))
		state["response"] = self._generate_summary(state)
		logger.info("SynthesizerAgent produced final answer (%d chars)", len(state["response"]))
		state["next_node"] = ""
		return state