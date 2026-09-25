"""Quotes skill: quotations and their revision history."""

from __future__ import annotations

from src.skills.base import Skill

quotes_skill = Skill(
    name="quotes",
    description="Quotations, revision history, and quote line items for the current company.",
    instructions=(
        "Use get_quote_details for general information about a specific quote.\n"
        "Use get_quote_revisions for the complete revision history of a quote.\n"
        "Use get_latest_quote_revision when only the current/latest revision is needed.\n"
        "Use get_quote_lines for machines, descriptions and prices contained in a specific quote revision "
        "(pass the revision id, e.g. QREV-0002).\n"
        "Use get_company_quotes to retrieve quotes associated with the current company.\n\n"
        "A quote can have multiple revisions. The revision with the highest number is the latest revision. "
        "A quote has no status of its own: the status is the revision's lifecycle state. When comparing quote "
        "revisions, always consider revision number, status, discount rate and change summary. Quote lines "
        "belong to a revision, not to a quote. Line prices are already net of the revision's discount -- never "
        "apply the discount twice."
    ),
    tool_names=(
        "get_quote_details",
        "get_quote_revisions",
        "get_quote_lines",
        "get_company_quotes",
        "get_latest_quote_revision",
    ),
)
