"""Manuals RAG agent node for FleetAssistant."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

from langchain.agents import create_agent
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

def make_manuals_agent_node(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[get_manual_excerpts],
		system_prompt=_SYSTEM_PROMPT,
	)

	# TODO: Make this a RAG instead of a LLM with tooling
	def _generate_answer(request: str) -> str:
		messages = [
			{"role": "user", "content": request},
		]
		result = agent.invoke({"messages": messages})
		return result["messages"][-1].content

	def manuals_agent_node(state: GraphState) -> GraphState:
		call = state["agent_calls"][-1]

		if call["agent_name"] != "manuals":
			raise ValueError("The agent name in the state does not match the expected agent name.")

		request = call["agent_request"]

		logger.info("ManualsAgent invoked | request=%r", request)

		try:
			response = _generate_answer(request)
		except Exception as exc:
			logger.warning("ManualsAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available manuals."

		logger.info("ManualsAgent produced answer (%d chars)", len(response))

		call["agent_response"] = response
		state["messages"] = [{'role': 'assistant', 'content': response}]

		return state

	return manuals_agent_node
