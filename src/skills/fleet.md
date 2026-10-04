---
name: fleet
description: "The current user's company machine directory and each machine's model and configuration."
visibility: [full, technician, commercial]
tools:
  - get_company_machines
  - get_machine_details
---
Two machines of the same model are not interchangeable. What describes how one specific machine was built is its own record: the configuration profile (nominal production rate, number of heads, supply voltage, closure head type and chuck, installed options), its PLC family and its software version. Take such facts from get_machine_details and quote them as given; never assume them from the model name.

The delivery date answers "when was it delivered". A machine's manual is a separate document (see the manuals skill).
