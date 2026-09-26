---
name: quotes
description: "Quotations, their revision history and the line items of each revision for the current company."
visibility: [full, commercial]
tools:
  - get_quotes_overview
  - get_company_quotes
  - get_quote_details
  - get_quote_revisions
  - get_latest_quote_revision
  - get_quote_lines
---
Several quotes at once: for any list, status overview, count, total or comparison across quotes (which are open, their total value, which never became an order), call get_quotes_overview once. It already gives each quote's status, latest revision, net total and orders, and the totals per status, so copy those figures instead of adding up lines yourself or looking quotes up one by one. Use the per-quote tools below only to drill into one quote.

Structure: a quote has revisions; each revision has lines. A quote has no status of its own: the status is its latest revision's (the highest revision number). Revision status is one of Draft, Submitted, Superseded (replaced by a later revision), Approved, Rejected, Expired. Quote lines belong to a revision, not to the quote, so get the revision id first (get_quote_revisions), and to compare two revisions compare their line sets and read the change summary. A line with no machine is not tied to an installed machine.

Prices: a line's price is already net of the revision's discount rate, so never apply the discount again. Each price is shown with its currency (EUR, or GBP for some quotes): quote it as shown and never assume one.

Validity and edge cases: a quote is only valid until its valid-until date, so compare it with today's date and report status and dates as recorded. A quote can have been approved after it expired, or end with a rejected final revision, or never become an order (get_orders_by_quote); say so as it is instead of smoothing it over.

To find what was quoted or paid for one machine, look through the company's quotes, their approved revisions and the lines that name that machine, and say which quotes you looked at.
