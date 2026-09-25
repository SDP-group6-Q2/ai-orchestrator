---
name: diagnostics
description: "Live sensor readings, alarms and operational health of a specific machine, read against that machine's own manual."
visibility: [full, technician]
tools:
  - get_latest_telemetry_snapshot
  - get_telemetry_summary
  - get_telemetry_history
  - get_alarm_summary
  - get_alarm_history
  - get_maintenance_history
---
DIAGNOSE WITH THE MANUAL. Telemetry and alarms tell you WHAT the machine is doing; only its manual tells you what that MEANS: which conditions are normal, what an alarm's cause and remedy are, which signals point to which fault. Two machines of the same model differ, so use this machine's own manual (get_manual_excerpts, see the manuals skill), not general knowledge. Search it in these situations, before you conclude:
- An alarm appears (open, recurring or just asked about): search its description (never its code) for the cause, the checks to perform and the remedy, and use that to say what the user should check.
- The user asks whether a reading is normal or the machine is healthy, or you see something unusual: search the manual's technical data and operating limits for that quantity (temperature, air pressure, speed, output, torque) and compare the reading with that limit. If the manual gives no limit, say so; never invent a threshold.
- A symptom is reported (low output, frequent stops, overheating, noise): search the manual's troubleshooting and maintenance sections for that symptom to learn the likely causes and which signals to check, then fetch exactly those signals below.
- Maintenance is in question: search the manual's maintenance schedule for the intervals and tasks that apply.

ASK FOR THE RIGHT DATA. The telemetry has only these signals, so pick the one that matches the question instead of pulling everything:
- Operational status and the health note: what the machine is doing now.
- Production rate: throughput. Judge it against the nominal rate in the machine's configuration profile (get_machine_details), not against a generic expectation.
- Uptime %: the share of the hour spent producing. It measures productive time, not equipment health, and is 0 whenever the machine wasn't producing.
- Temperature: overheating, cooling and lubrication problems.
- Energy use: load and abnormal consumption.
- Alarm count per hour, and the alarm events themselves: what went wrong and when.
Use the latest snapshot for "right now"; the weekly or daily summary for any trend or degradation over more than a few days; the raw hourly history only to inspect one narrow window (paged: continue with the cursor or narrow the dates before concluding). For alarms start with the summary (counts by code and severity, how many are still open), then the individual events only for the codes that matter. Use the maintenance history to see whether a problem was already worked on and by whom.

READ THE DATA CORRECTLY:
- Operational status is one of Running, Alarm, Idle, Stopped, Maintenance, Size change.
- An hour's alarm count agrees with the alarms recorded for that machine in that hour.
- Alarm codes look like AL017_LOW_AIR_PRESSURE: the mnemonic names the physical condition. Severity (Critical, High, Medium, Low) is fixed per code by the monitoring platform, not by the manual. Status is Open, Acknowledged or Resolved: "open" alone does not say whether anyone has acknowledged it.
- A maintenance ticket with no linked alarm did not originate from an alarm. That is normal, not missing data.

TYPICAL QUESTIONS:
- "Why does it keep alarming / what do these alarms mean?" Alarm summary, then the manual for each important code (most frequent or most severe), then the maintenance history for tickets already raised on it. Answer with the meaning, the likely causes and the checks from the manual.
- "Is it healthy / is X normal?" Latest snapshot and weekly summary, the alarms still open, and the manual's limits for the quantity in question. Compare and say which readings are inside or outside what the manual allows.
- "Why is output low?" Compare production rate with the nominal rate, look at uptime and alarms in the same period, and read the manual's troubleshooting for that symptom.

ANSWERING: explain what the data means for this machine, separating what the DATA shows from what the MANUAL says (and cite the section and page for anything taken from the manual). If the data has no counter for something (for example hours run since the last service), say so and never estimate it. If nothing relevant is available, say you cannot answer from the available readings.
