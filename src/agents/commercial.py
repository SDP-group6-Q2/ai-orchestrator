from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.config import REFERENCE_DATE
from src.context import AgentContext
from src.security.access import (
    ACCESS_DENIED_OR_UNAVAILABLE,
    can_access_commercial_data,
    get_user_context,
)

from src.tools.orders_tools import (
    get_company_orders_secure,
    get_order_details_for_company,
    get_order_lines_for_company,
    get_orders_by_quote_for_company,
)

from src.tools.quotes_tools import (
    get_company_quotes_secure,
    get_latest_quote_revision_for_company,
    get_quote_details_for_company,
    get_quote_lines_for_company,
    get_quote_revisions_for_company,
)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    f"Today's date is {REFERENCE_DATE}. Use it for any relative date reasoning "
    "(e.g. whether a quote is still valid, or how recent an order is).\n\n"

    "You are the commercial support agent for AROL capping machines. "
    "You answer questions about quotations, quote revisions, orders, "
    "order status, shipment status, fulfillment and the commercial "
    "relationship with a customer.\n\n"

    "Always use the available commercial tools to retrieve evidence "
    "before answering questions about commercial data.\n\n"

    "ACCESS CONTROL:\n"
    "- You can access commercial data only for the current user's company.\n"
    "- Never claim to have access to commercial data from another company.\n"
    "- If requested data is not returned by the tools, do not infer or invent it.\n\n"

    "QUOTES:\n"
    "- Use get_quote_details for general information about a specific quote.\n"
    "- Use get_quote_revisions for the complete revision history of a quote.\n"
    "- Use get_latest_quote_revision when only the current/latest revision is needed.\n"
    "- Use get_quote_lines for machines, descriptions and prices contained "
    "in a specific quote revision.\n"
    "- Use get_company_quotes to retrieve quotes associated with the current company.\n"
    "- A quote can have multiple revisions.\n"
    "- The revision with the highest revisionNumber is the latest revision.\n"
    "- revisionStatus represents the lifecycle state of a revision.\n"
    "- When comparing quote revisions, always consider revisionNumber, "
    "revisionStatus, discountRate and changeSummary.\n"
    "- Quote lines belong to a revision through quoteRevisionId.\n"
    "- QuoteLines.price is already net of discountRate. Never apply the "
    "discount twice.\n\n"

    "ORDERS:\n"
    "- Use get_order_details for information about a specific order, including "
    "orderStatus, shipmentStatus, dates and originating quote.\n"
    "- Use get_order_lines for fulfillment information about an order.\n"
    "- Use get_orders_by_quote to find orders generated from a quote.\n"
    "- Use get_company_orders to retrieve orders associated with the current company.\n"
    "- Orders reference their originating quote through quoteId.\n"
    "- Order lines contain fulfillment status only. They do not contain "
    "item descriptions, quantities or prices.\n"
    "- If the user asks about the commercial contents or price of an order, "
    "retrieve the associated quote, its relevant revision and its quote lines.\n\n"

    "Never invent commercial information. "
    "Answer only using information returned by the tools. "
    "If the tools do not provide enough information, explicitly say that "
    "the available commercial data is insufficient.\n\n"

    "RESPONSE FORMAT:\n"
    "- Write responses for a customer-facing chat interface.\n"
    "- Use clean Markdown suitable for frontend rendering.\n"
    "- Prefer short headings and bullet points over tables.\n"
    "- Do not expose tool calls, tool names, internal reasoning, SQL, logs, "
    "function metadata or internal source references.\n"
    "- Do not include technical citations or assistant/function call traces.\n"
    "- Keep answers concise, readable and practical.\n\n"

    "- If a tool returns ACCESS_DENIED_OR_UNAVAILABLE, tell the user that "
    "they cannot access commercial information for the requested resource.\n"
    "- Never speculate that an inaccessible resource was cancelled, deleted, "
    "entered incorrectly or does not exist.\n"

    "Example response style:\n"
    "### Order ORD-XXXX\n"
    "- **Status:** Closed\n"
    "- **Shipment status:** Installed\n"
    "- **Originating quote:** QTE-XXXX\n"
    "- **Approved revision:** QREV-XXXX\n\n"
    "**Commercial changes**\n"
    "- First change\n"
    "- Second change\n"
)


def _authorized_company_id(runtime: ToolRuntime[AgentContext]) -> str | None:
    """Resolve the calling user's company from trusted run context, re-checked on every call.

    `runtime.context` comes from `graph.invoke(..., context=...)`, set by FleetAssistant
    from the authenticated request -- never from LLM-controlled tool arguments -- so a
    prompt-injected or hallucinated company id can never reach the `_for_company` queries.
    """
    user_context = get_user_context(runtime.context.user_id)
    if user_context is None or not can_access_commercial_data(user_context):
        return None
    return user_context["companyid"]


@tool
def get_quote_details(quote_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return details of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_quote_details_for_company(quote_id, company_id)


@tool
def get_quote_revisions(quote_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return revisions of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_quote_revisions_for_company(quote_id, company_id)


@tool
def get_quote_lines(quote_revision_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return quote lines accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_quote_lines_for_company(quote_revision_id, company_id)


@tool
def get_company_quotes(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return quotes belonging to the current user's company."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_company_quotes_secure(company_id)


@tool
def get_latest_quote_revision(quote_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return the latest revision of a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_latest_quote_revision_for_company(quote_id, company_id)


@tool
def get_order_details(order_id: str, runtime: ToolRuntime[AgentContext]) -> dict | str | None:
    """Return details of an order accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_order_details_for_company(order_id, company_id)


@tool
def get_order_lines(order_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return fulfillment lines for an order accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_order_lines_for_company(order_id, company_id)


@tool
def get_orders_by_quote(quote_id: str, runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return orders created from a quote accessible to the current user."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_orders_by_quote_for_company(quote_id, company_id)


@tool
def get_company_orders(runtime: ToolRuntime[AgentContext]) -> list[dict] | str:
    """Return orders belonging to the current user's company."""
    company_id = _authorized_company_id(runtime)
    if company_id is None:
        return ACCESS_DENIED_OR_UNAVAILABLE
    return get_company_orders_secure(company_id)


_TOOLS = [
    get_quote_details,
    get_quote_revisions,
    get_quote_lines,
    get_company_quotes,
    get_latest_quote_revision,
    get_order_details,
    get_order_lines,
    get_orders_by_quote,
    get_company_orders,
]


def make_commercial_agent(
    llm: BaseChatModel,
    checkpointer: BaseCheckpointSaver | None = None,
):
    return create_agent(
        model=llm,
        tools=_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )
