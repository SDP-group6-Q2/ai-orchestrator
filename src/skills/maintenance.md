---
name: maintenance
description: "The current user's company open and past maintenance and support tickets."
visibility: [full, technician]
tools:
  - get_company_maintenance_tickets
---
Vocabulary: ticket type is one of Remote troubleshooting, On-site service, Spare parts request, Scheduled maintenance, Overhaul, Size change assistance. Status is one of Open, In progress, Waiting for parts (all three are open work) and Resolved, Closed (done). Priority is Critical, High, Medium or Low. Owner is Line Operator, Maintenance Man, Plant Maintenance Manager or AROL Technical Service.

For "what is open / overdue": keep the tickets that are not Resolved or Closed, order them by priority then age, and reason about age against today's date. A ticket with no alarm did not originate from an alarm, which is normal.

Results are paged and say when more exist: continue with the cursor or narrow the dates before concluding. For one machine's tickets together with the alarm that triggered each, use get_maintenance_history (diagnostics).
