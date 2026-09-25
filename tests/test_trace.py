from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.trace import extract_trace, render_trace_context


def _turn():
    return [
        SystemMessage(content="ctx"),
        HumanMessage(content="old question"),
        AIMessage(content="", tool_calls=[{"name": "old_tool", "args": {}, "id": "old"}]),
        ToolMessage(content="old result", tool_call_id="old", name="old_tool"),
        AIMessage(content="old answer"),
        HumanMessage(content="new question"),
        AIMessage(content="", tool_calls=[
            {"name": "get_alarm_summary", "args": {"machine_id": "MCH-0001", "since": None}, "id": "a"},
            {"name": "get_company_quotes", "args": {}, "id": "b"},
        ]),
        ToolMessage(content=[{"type": "text", "text": "| Alarm |\n| --- |\n| AL017 |"}], tool_call_id="a", name="get_alarm_summary"),
        ToolMessage(content="Access denied", tool_call_id="b", name="get_company_quotes", status="error"),
        AIMessage(content="final"),
    ]


def test_only_the_last_turns_calls_are_traced_compactly():
    trace = extract_trace(_turn())
    assert [t["tool"] for t in trace] == ["get_alarm_summary", "get_company_quotes"]
    assert trace[0]["args"] == {"machine_id": "MCH-0001"}  # None arguments dropped
    assert trace[0]["summary"] == "| Alarm | | --- | | AL017 |" and trace[0]["error"] is False
    assert trace[1]["error"] is True


def test_long_results_are_truncated_and_entries_capped():
    messages = [HumanMessage(content="q")]
    calls = [{"name": "t", "args": {}, "id": str(i)} for i in range(12)]
    messages.append(AIMessage(content="", tool_calls=calls))
    messages += [ToolMessage(content="x" * 1000, tool_call_id=str(i), name="t") for i in range(12)]
    trace = extract_trace(messages)
    assert len(trace) == 8 and all(len(t["summary"]) <= 300 for t in trace)


def test_a_turn_without_tools_has_an_empty_trace():
    assert extract_trace([HumanMessage(content="hi"), AIMessage(content="hello")]) == []


def test_render_lists_the_last_three_traced_turns_only():
    def turn(tool):
        return {"role": "assistant", "content": "a", "trace": [{"tool": tool, "args": {"machine_id": "M"}, "summary": "s", "error": False}]}

    history = [turn("t1"), {"role": "user", "content": "u"}, turn("t2"), turn("t3"), turn("t4")]
    text = render_trace_context(history)
    assert "t1(" not in text and all(f"- {t}(machine_id='M') -> s" in text for t in ("t2", "t3", "t4"))
    assert "call the tool again" in text


def test_render_is_empty_without_traces():
    assert render_trace_context([{"role": "assistant", "content": "a"}, {"role": "user", "content": "u"}]) == ""
