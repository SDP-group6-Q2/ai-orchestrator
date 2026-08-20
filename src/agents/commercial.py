from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.tools import (get_orders_descriptors, query_orders, get_quotes_descriptors, query_quotes)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are a commercial support agent for AROL capping machines. "
)

def make_commercial_agent(llm: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None):
	tools = [
		get_orders_descriptors,
		query_orders,
		get_quotes_descriptors,
		query_quotes,
    ]
	
	agent = create_agent(
		model=llm,
		tools=tools,
		system_prompt=_SYSTEM_PROMPT,
		checkpointer=checkpointer,
	)

	return agent