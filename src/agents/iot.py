"""IoT telemetry specialist tool for FleetAssistant."""

from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain_core.tools import tool

from src.tools import (query_telemetry_readings, get_telemetry_tables_descriptors)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the IoT telemetry agent for FleetAssistant. "
	"Use the get_telemetry_tables_descriptors tool to understand the structure of the telemetry data before querying it."
	"Call the query_telemetry_readings tool with an SQL query to fetch live sensor readings for the user's machine."
	"before responding; call it again with a different query if you need more data. "
	"Answer only once you have grounded evidence from the tool. "
	"If no telemetry data is relevant, say you cannot answer the question based on the available readings. "
	"Keep the answer concise and practical."
)

def make_iot_tool(llm: BaseChatModel):
	agent = create_agent(
		model=llm,
		tools=[query_telemetry_readings, get_telemetry_tables_descriptors],
		system_prompt=_SYSTEM_PROMPT,
	)

	# TODO: Evaluate truthfulness of the answer executing same SQL queries and comparing the results with the answer
	@tool
	def iot_agent(request: str, machine_id: int) -> str:
		"""Ask the IoT telemetry specialist about live sensor readings, error states, cycle counts, or the operational health of a specific machine. Always pass the machine_id from the current conversation context."""
		logger.info("IotAgent invoked | request=%r machine_id=%r", request, machine_id)

		messages = [
			{"role": "user", "content": request},
			{"role": "user", "content": "The machine ID is: {}".format(machine_id)},
		]
		try:
			result = agent.invoke({"messages": messages})
			response = result["messages"][-1].content
		except Exception:
			logger.warning("IotAgent could not produce a grounded answer", exc_info=True)
			response = "I'm sorry, I cannot answer that question based on the available telemetry."

		logger.info("IotAgent produced answer: %s", response)
		return response

	return iot_agent
