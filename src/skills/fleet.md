---
name: fleet
description: "The current user's company machine directory and model details."
visibility: [full, technician, commercial]
tools:
  - get_company_machines
  - get_machine_details
---
Use get_company_machines to list every machine belonging to the current user's company, with model, serial number, plant location and PLC family.
Use get_machine_details for one machine's full details and its model: delivery date, as-built configuration profile, PLC family, software version, container and cap type. Always pass machine_id explicitly.
