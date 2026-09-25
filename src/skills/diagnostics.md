---
name: diagnostics
description: "Live sensor readings, error states, cycle counts, and operational health for a specific machine."
visibility: [full, technician]
tools:
  - get_latest_telemetry_snapshot
  - get_telemetry_summary
  - get_telemetry_history
  - get_alarm_summary
  - get_alarm_history
  - get_maintenance_history
---
Every one of these tools takes a machine_id: always pass it explicitly (the machine in scope for this conversation unless the user asks about another one).

Use get_latest_telemetry_snapshot for the machine's current operational status, production rate, uptime, alarm count, temperature, energy usage and health note.
Use get_telemetry_summary for trend/pattern questions or performance-degradation analysis spanning more than a few days -- it returns per-day/week aggregates, optionally narrowed with since/until.
Use get_telemetry_history only to inspect a specific narrow window or a small number of recent raw readings; results are paged and say so when more exist -- prefer get_telemetry_summary for anything broader.
Use get_alarm_summary to answer "why does this machine keep alarming" style questions -- it returns counts grouped by alarm code and severity instead of every individual event.
Use get_alarm_history only to inspect specific recent alarm events, optionally narrowed with since/until; results are paged.
Use get_maintenance_history to correlate alarms with the maintenance tickets raised for the machine, optionally narrowed with since/until; results are paged.

How to read these results correctly:
- The operational status is one of Running, Alarm, Idle, Stopped, Maintenance, Size change.
- Uptime % is the share of that hour actually spent producing -- it measures productive time, not equipment health, and is 0 whenever the machine wasn't producing that hour.
- Production rate is 0 whenever the machine wasn't producing, and never exceeds that machine's own nominal rate. The nominal rate isn't on the model -- it lives in that specific machine's configuration profile (from get_machine_details), since two machines of the same model can be built and configured differently. Judge whether a reading is normal against that machine's own configuration, not a generic expectation.
- The alarm count of a telemetry hour agrees with how many alarms exist for that machine in that hour.
- Alarm codes follow ALnnn_MNEMONIC (e.g. AL017_LOW_AIR_PRESSURE): the mnemonic names the physical problem condition. Severity (Critical/High/Medium/Low) is fixed per code by the monitoring platform, not the manual. Alarm status is Open, Acknowledged or Resolved.
- To explain what an alarm means or how to resolve it, search the machine's manual for the alarm's description (see the manuals tool) -- its technical, mechanical and troubleshooting sections describe the cause and remedy for that condition on that specific machine.
- In maintenance history, a ticket with no linked alarm simply didn't originate from an alarm -- that's expected, not missing data.
- If a paged result says more rows exist, don't assume you've seen everything -- continue with the cursor it gives, narrow since/until, or switch to a summary tool before concluding.

Interpret this data to answer the question -- explain what it means for the machine, don't just restate raw values. If no relevant data is available, say you cannot answer the question based on the available readings.
