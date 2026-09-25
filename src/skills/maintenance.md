---
name: maintenance
description: "The current user's company open and past maintenance/support tickets."
visibility: [full, technician]
tools:
  - get_company_maintenance_tickets
---
Use get_company_maintenance_tickets to fetch the user's company's open and past support tickets, optionally narrowed with since/until. Results are paged and say so when more exist -- continue with the cursor it gives or narrow since/until rather than assuming you've seen everything.

Column meanings: ticket type is one of Remote troubleshooting, On-site service, Spare parts request, Scheduled maintenance, Overhaul, Size change assistance. Status is one of Open, In progress, Waiting for parts, Resolved, Closed. Priority is one of Critical, High, Medium, Low. Owner is one of Line Operator, Maintenance Man, Plant Maintenance Manager, AROL Technical Service. A ticket with no alarm did not originate from an alarm -- that's expected, not missing data.
