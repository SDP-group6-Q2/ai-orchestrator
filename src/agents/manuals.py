"""Class-based manuals agent for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langgraph.graph.message import add_messages, MessagesState

import ollama

from src.state import GraphState
from src.tools import get_manual_excerpts

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the manuals RAG agent for FleetAssistant. "
	"Call the retrieve_manual tool to ground your answer in actual machine manual content "
	"before responding; call it again with a refined query if the excerpts you got back "
	"are not enough. "
	"Answer the user question with citations from the manual."
	"If no manual content is relevant, say you cannot answer the question based on the available manuals."
)

class ManualsAgent:
	def __init__(self, llm: BaseChatModel):
		self._llm_with_tools = llm.bind_tools([get_manual_excerpts])

	# TODO: Make this a RAG instead of a LLM with tooling
	def _generate_answer(self, request: str) -> str:
		messages = [
			{"role": "system", "content": _SYSTEM_PROMPT},
			{"role": "user", "content": request},
		]
		response = self._llm_with_tools.invoke(messages)
		return response.content

	def run(self, state: GraphState) -> GraphState:
		call = state["agent_calls"][-1]

		if call["agent_name"] != "manuals":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"]
		
		logger.info("ManualsAgent invoked | request=%r", request)

		try:
			response = self._generate_answer(request)
		except Exception as exc:
			logger.warning("ManualsAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available manuals."

		logger.info("ManualsAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["messages"] = [{'role': 'assistant', 'content': response}]

		return state
