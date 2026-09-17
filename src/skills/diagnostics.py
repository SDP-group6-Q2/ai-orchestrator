"""Diagnostics skill: live telemetry, alarms, and maintenance-correlated history."""

from __future__ import annotations

from src.skills.base import Skill
from src.skills.formatting import render_json_tool_result
from src.tools import (
    get_latest_telemetry_snapshot,
    get_telemetry_summary,
    get_telemetry_history,
    get_alarm_summary,
    get_alarm_history,
    get_maintenance_history,
)

diagnostics_skill = Skill(
    name="diagnostics",
    description=(
        "Live sensor readings, error states, cycle counts, and operational health "
        "for a specific machine."
    ),
    instructions=(
        "All of these tools default machine_id to the machine already in context -- only pass machine_id "
        "explicitly to ask about a different machine than the current one.\n\n"

        "Use get_latest_telemetry_snapshot for the machine's current operational status, production rate, "
        "uptime, alarm count, temperature, energy usage and health note.\n"
        "Use get_telemetry_summary for trend/pattern questions or performance-degradation analysis spanning "
        "more than a few days -- it returns per-day/week aggregates, optionally narrowed with since/until.\n"
        "Use get_telemetry_history only to inspect a specific narrow window or a small number of recent "
        "raw readings; it's capped to the most recent rows and will say so if truncated -- prefer "
        "get_telemetry_summary for anything broader.\n"
        "Use get_alarm_summary to answer \"why does this machine keep alarming\" style questions -- it "
        "returns counts grouped by alarm code and severity instead of every individual event.\n"
        "Use get_alarm_history only to inspect specific recent alarm events, optionally narrowed with "
        "since/until; it's capped to the most recent alarms.\n"
        "Use get_maintenance_history to correlate alarms with maintenance tickets raised for the machine, "
        "optionally narrowed with since/until; it's also capped to the most recent tickets.\n\n"

        "How to read these columns correctly:\n"
        "- operationalStatus is one of Running, Alarm, Idle, Stopped, Maintenance, Size change.\n"
        "- uptimePercentage is the share of that hour actually spent producing -- it measures productive "
        "time, not equipment health, and is 0 whenever the machine wasn't producing that hour. "
        "avg_uptime_percentage in get_telemetry_summary is the average of this across the bucket.\n"
        "- productionRateBph is 0 whenever the machine wasn't producing, and never exceeds that machine's "
        "own nominal rate. Nominal rate isn't on the model -- it lives in that specific machine's "
        "configurationProfile (from get_machine_details/get_company_machines), since two machines of the "
        "same model can be built and configured differently. Judge whether a reading is normal against "
        "that machine's own configuration, not a generic expectation.\n"
        "- alarmCount for a telemetry hour agrees with how many alarms exist for that machine in that hour; "
        "total_alarm_count in get_telemetry_summary sums this across the bucket.\n"
        "- Alarm codes follow ALnnn_MNEMONIC (e.g. AL017_LOW_AIR_PRESSURE): the mnemonic names the physical "
        "problem condition. severity (Critical/High/Medium/Low) is fixed per code by the monitoring "
        "platform, not the manual. alarmStatus is one of Open, Acknowledged, Resolved -- get_alarm_summary's "
        "open_count is how many of a given code/severity group are still Open.\n"
        "- To explain what an alarm means or how to resolve it, search the machine's manual using the "
        "alarm's mnemonic -- its technical, mechanical and troubleshooting sections describe the cause and "
        "remedy for that condition on that specific machine.\n"
        "- In get_maintenance_history results, a ticket with no linked alarm (alarmid/alarmcode absent) "
        "simply didn't originate from an alarm -- that's expected, not missing data.\n"
        "- If a capped tool's result says truncated, don't assume you've seen everything -- narrow "
        "since/until using the boundary it gives you, or switch to a summary tool, before concluding.\n\n"

        "Interpret this data to answer the question -- explain what it means for the machine, don't just "
        "restate the raw values (the underlying rows are already shown to the user as a table). If no "
        "relevant data is available, say you cannot answer the question based on the available readings."
    ),
    tools=[
        get_latest_telemetry_snapshot,
        get_telemetry_summary,
        get_telemetry_history,
        get_alarm_summary,
        get_alarm_history,
        get_maintenance_history,
    ],
    tool_renderers={
        "get_latest_telemetry_snapshot": render_json_tool_result,
        "get_telemetry_summary": render_json_tool_result,
        "get_telemetry_history": render_json_tool_result,
        "get_alarm_summary": render_json_tool_result,
        "get_alarm_history": render_json_tool_result,
        "get_maintenance_history": render_json_tool_result,
    },
)
