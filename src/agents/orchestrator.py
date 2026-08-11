"""Class-based orchestrator for the FleetAssistant graph."""

from __future__ import annotations

import json
import logging
import os

from langchain.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Literal


from src.state import GraphState

logger = logging.getLogger(__name__)

_MAX_AGENT_STEPS = 3

_SYSTEM_PROMPT = (
	"You are the orchestrator node for an agentic AI workflow owned by the company AROL, that produces industrial capping machines for their clients."
	"The goal is to provide informed answers to client questions about their machines, using internal documentation and tools."
	"Your goal, as orchestrator, is to decide which agent node to call next, and what request to send to that agent, acquiring enough information to answer the user request."
	"Decide which agent to call next based on the user request and the previous agent requests and responses. "
	"Choose manuals_agent for questions about documentation, procedures or error-code meanings. "
	"Choose iot_agent for questions that need live telemetry or sensor readings from the machine. "
	"Choose orders_agent for questions about order history, shipments or support/service contracts. "
	"Choose service_agent for questions about customer service tickets or past service visits. "
	"If no agent option is appropriate, decide finish."
	"When choosing an agent, write agent request to be as specific as possible. "
)

class AgentRequest(BaseModel):
	agent: Literal['telemetry', 'manuals', 'orders', 'service', 'finish'] = Field(..., description="The next step of workflow, classified into one of the available agents.")
	agent_request: str = Field(..., description="The request to send to the next agent.")

class FleetOrchestrator:
	def __init__(self, llm: BaseChatModel):
		self.structured_llm = llm.with_structured_output(AgentRequest, method="function_calling")

	def _build_history(self, state: GraphState) -> str:
		history = {
			"user_info": state["user_info"],
			"messages": state["messages"],
			"agent_calls": state["agent_calls"],
		}
		return json.dumps(history, indent=2)

	def _decide_next_step(self, state: GraphState):
		if len(state["agent_calls"]) >= _MAX_AGENT_STEPS:
			return {"agent": "finish", "agent_request": ""}

		try:
			response = self.structured_llm.invoke([
				{'role': 'system', 'content': _SYSTEM_PROMPT},
				{'role': 'user', 'content': self._build_history(state)}
			])

			return {"agent": response.agent, "agent_request": response.agent_request}

		except Exception as exc:
			logger.warning("Orchestrator LLM planning failed.", exc_info=True)
			return {"agent": "finish", "agent_request": ""}

	def run(self, state: GraphState) -> GraphState:
		decision = self._decide_next_step(state)

		logger.info(
			"Orchestrator step %d -> %s | request=%r ",
			len(state.get("agent_calls", [])) + 1,
			decision["agent"],
			decision["agent_request"]
		)

		state["next_node"] = decision["agent"]
		state["agent_calls"] = state["agent_calls"] + [{
			"agent_name": decision["agent"],
			"agent_request": decision["agent_request"],
			"agent_response": "",
		}]


		return state
