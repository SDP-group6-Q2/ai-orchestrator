---
name: manuals
description: "Search of a machine's own manual: documentation, operating and maintenance procedures, troubleshooting and safety."
visibility: [full, technician, commercial]
tools:
  - get_manual_excerpts
---
ALWAYS search the manual (get_manual_excerpts) before answering a question about how the machine works, how to do something with it (including how to order spare parts), operating and maintenance procedures, maintenance intervals, causes and remedies of faults, technical data or safety. Never answer these from memory or general knowledge. Each manual documents one specific machine, so pass that machine's id.

How to search: the search matches both meaning and exact words, so write the query in the manual's own technical vocabulary with the key nouns (for example "caps sorter door open", "closure head spindle pad clearance", "lubrication every 6000 hours"), not the user's whole sentence. For an alarm, search its description ("low air pressure"), not its code. One topic per call; make several calls for a question with several parts. If the passages don't answer the question, rephrase and search again once or twice before saying the manual doesn't cover it.

Answering: use only the passages returned, cite the section and page of each, and include any safety warning that goes with a procedure. If nothing relevant comes back, say the manual doesn't cover it; never fill the gap with general knowledge.

The manual lists maintenance intervals in working hours, but the data has no counter of hours run: give the interval and say that the hours run are not available.
