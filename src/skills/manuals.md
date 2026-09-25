---
name: manuals
description: "Search of a machine's own manual -- documentation, operating and maintenance procedures, troubleshooting and safety."
visibility: [full, technician, commercial]
tools:
  - get_manual_excerpts
---
ALWAYS call get_manual_excerpts(machine_id, query) before answering a question about how the machine works, how to do something with it (including how to order spare parts), operating and maintenance procedures, maintenance intervals, causes and remedies of faults, technical data or safety. Never answer these from memory or general knowledge. Each manual documents one specific machine, so pass that machine's id. Search one topic per call, in the user's own words; for an alarm, search its description (e.g. "low air pressure"), not its code.
Answer only from the excerpts returned and cite the section and page of each one. If nothing relevant comes back, say the manual doesn't cover it -- never fill the gap with general knowledge.
