"""Quotes skill: quotations and their revision history."""

from __future__ import annotations

from src.skills.base import Skill
from src.tools.quotes_tools import (
    get_quote_details,
    get_quote_revisions,
    get_quote_lines,
    get_company_quotes,
    get_latest_quote_revision,
)

quotes_skill = Skill(
    name="quotes",
    description="Quotations, revision history, and quote line items for the current company.",
    instructions=(
        "Use get_quote_details for general information about a specific quote.\n"
        "Use get_quote_revisions for the complete revision history of a quote.\n"
        "Use get_latest_quote_revision when only the current/latest revision is needed.\n"
        "Use get_quote_lines for machines, descriptions and prices contained in a specific quote revision.\n"
        "Use get_company_quotes to retrieve quotes associated with the current company.\n\n"
        "A quote can have multiple revisions. The revision with the highest revisionNumber is the latest "
        "revision. revisionStatus represents the lifecycle state of a revision. When comparing quote "
        "revisions, always consider revisionNumber, revisionStatus, discountRate and changeSummary. Quote "
        "lines belong to a revision through quoteRevisionId. QuoteLines.price is already net of "
        "discountRate -- never apply the discount twice."
    ),
    tools=[
        get_quote_details,
        get_quote_revisions,
        get_quote_lines,
        get_company_quotes,
        get_latest_quote_revision,
    ],
)
