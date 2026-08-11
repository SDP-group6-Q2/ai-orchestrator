"""Class-based final synthesizer for FleetAssistant."""

from __future__ import annotations

import logging
import os

from langchain_core.language_models import BaseChatModel
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
	def __init__(self, llm: BaseChatModel):
		self._llm = llm

	def _generate_summary(self, state: GraphState) -> str:
		try:
			response = self._llm.invoke(state["messages"] + [{'role': 'system', 'content': _SYSTEM_PROMPT}])
			content = response.content
			if not content:
				raise ValueError("empty response from ollama")
			return content
		except Exception:
			logger.warning("Synthetizer LLM generation failed, using fallback summary", exc_info=True)
			return "I'm sorry, I cannot provide a grounded answer based on the available information."

	def run(self, state: GraphState) -> GraphState:
		logger.info("SynthesizerAgent invoked | %d agent call(s) in history", len(state.get("agent_calls", [])))
		response = self._generate_summary(state)
		logger.info("SynthesizerAgent produced final answer (%d chars)", len(response))
		return {"messages": [{'role': 'system', 'content': response}]}