"""Manuals RAG specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from src.tools import get_manual_excerpts

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the manuals RAG agent for FleetAssistant. "
	"Call the get_manual_excerpts tool to ground your answer in actual machine manual content "
	"before responding; call it again with a refined query if the excerpts you got back "
	"are not enough. "
	"Answer the user question with citations from the manual."
	"If no manual content is relevant, say you cannot answer the question based on the available manuals."
)

def make_manuals_tool(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[get_manual_excerpts],
		system_prompt=_SYSTEM_PROMPT,
	)

	@tool
	def manuals_agent(request: str, machine_id: str) -> str:
		"""Ask the manuals specialist about documentation, procedures, or error-code meanings for a specific machine. Always pass the machine_id from the current conversation context."""
		logger.info("ManualsAgent invoked | request=%r machine_id=%r", request, machine_id)

		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		try:
			result = agent.invoke({"messages": messages})
			response = result["messages"][-1].content
		except Exception:
			logger.warning("ManualsAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available manuals."

		logger.info("ManualsAgent produced answer (%d chars)", len(response))
		return response

	return manuals_agent
