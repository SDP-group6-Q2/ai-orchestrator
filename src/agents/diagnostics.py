"""diagnostics telemetry specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.context import AgentContext
from src.tools import (query_telemetry_readings, get_telemetry_tables_descriptors)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are a diagnostics agent on AROL company machinery. The company produces automatic machines and lines for the production of capping/closure of bottles, jars, and other containers. "
	"Your goal is to understand request and investigate real data from the machine to provide a grounded answer."

	"Use the get_telemetry_tables_descriptors tool to understand the structure of the telemetry data before querying it."
	"Use query_telemetry_readings as the primary data source for telemetry analysis, enabling predictive analysis, health monitoring, and autonomous diagnostics."

	"Before responding, make all relevant queries to provide growding data for a technical expert. "
	"Answer only once you have grounded evidence from the tool. "

	"If no telemetry data is relevant, say you cannot answer the question based on the available readings. "
	"Do not include technical interpretation or conclusion to presented data, only provide the data itself."
	"Keep the answer concise and practical, providing necessary data.\n\n"

	"- If a tool returns ACCESS_DENIED_OR_UNAVAILABLE, say you cannot access "
	"the requested telemetry data.\n"
	"- Never speculate that inaccessible telemetry data was cancelled, deleted, "
	"entered incorrectly or does not exist.\n"
)

def make_diagnostics_tool(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[query_telemetry_readings, get_telemetry_tables_descriptors],
		system_prompt=_SYSTEM_PROMPT,
		context_schema=AgentContext,
	)

	# TODO: Evaluate truthfulness of the answer executing same SQL queries and comparing the results with the answer
	@tool
	def diagnostics_agent(request: str, machine_id: str, runtime: ToolRuntime[AgentContext]) -> str:
		"""Ask the diagnostics telemetry specialist about live sensor readings, error states, cycle counts, or the operational health of a specific machine. Always pass the machine_id from the current conversation context."""
		logger.info("diagnosticsAgent invoked | request=%r machine_id=%r", request, machine_id)

		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		try:
			result = agent.invoke({"messages": messages}, context=runtime.context)
			response = result["messages"][-1].content
		except Exception:
			logger.warning("diagnosticsAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available telemetry."

		logger.info("diagnosticsAgent produced answer: %s", response)
		return response

	return diagnostics_agent
