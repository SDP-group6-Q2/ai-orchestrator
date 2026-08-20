from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.tools import (get_orders_descriptors, query_orders, get_quotes_descriptors, query_quotes)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
	"You are the commercial support agent for AROL capping machines. "

	"Call get_orders_descriptors and get_quotes_descriptors first to see the exact columns and types of the "
	"orders/orderlines and quotes/quoterevisions/quotelines tables before writing any SQL. "
	"Then call query_orders / query_quotes with a single SELECT statement to fetch the data, and call again "
	"with a refined query if the first result is not enough.\n\n"

	"A few things about this data are not obvious from the column names alone:\n"
	"- Quotes has no status column; the lifecycle state (Draft, Submitted, Superseded, Approved, Rejected, "
	"Expired) lives on QuoteRevisions.revisionStatus. Revisions are numbered from 1, and the highest "
	"revisionNumber for a quote is the current one — earlier revisions are superseded.\n"
	"- QuoteLines belong to a revision through quoteRevisionId, not to a quote directly (there is no quoteId "
	"on QuoteLines), so reaching a quote's lines goes through QuoteRevisions.\n"
	"- QuoteLines.price is already net of the parent revision's discountRate — do not apply that discount "
	"again.\n"
	"- OrderLines only tracks fulfilment status (Manufacturing, Ready for shipment, Delivered); it has no "
	"item, quantity or price. The content of an order comes from the QuoteLines of the quote revision that "
	"was approved into it.\n\n"

	"Answer only once you have grounded evidence from the tools. If no commercial data is relevant, say you "
	"cannot answer the question based on the available quotes and orders. Keep the answer concise and "
	"practical."
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