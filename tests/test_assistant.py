import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import src.assistant as assistant


class FakeAgent:
    def __init__(self):
        self.calls = []

    async def ainvoke(self, payload, config=None, context=None):
        self.calls.append((payload, context))
        return {"messages": [*payload["messages"], AIMessage(content="the answer")]}


@pytest.fixture
def agent(monkeypatch):
    fake = FakeAgent()

    async def get_agent():
        return fake

    monkeypatch.setattr(assistant, "get_agent", get_agent)
    return fake


async def test_history_is_capped_to_the_last_messages(agent):
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(50)]
    await assistant.ask("q", "MCH-0001", "full", "tok", history=history)
    messages = agent.calls[0][0]["messages"]
    assert len(messages) == 1 + assistant.MAX_HISTORY_MESSAGES + 1  # context + window + the new question
    assert messages[1].content == "m30" and isinstance(messages[-1], HumanMessage)


async def test_traces_of_earlier_turns_go_into_the_context_message(agent):
    history = [
        {"role": "user", "content": "alarms?"},
        {"role": "assistant", "content": "AL017 is open", "trace": [{"tool": "get_alarm_summary", "args": {"machine_id": "MCH-0001"}, "summary": "AL017 open", "error": False}]},
    ]
    await assistant.ask("when was that last seen?", "MCH-0001", "technician", "tok", history=history)
    context = agent.calls[0][0]["messages"][0]
    assert isinstance(context, SystemMessage)
    assert "Current machine_id: MCH-0001" in context.content and "get_alarm_summary(machine_id='MCH-0001')" in context.content


async def test_identity_travels_in_the_context_not_the_messages(agent):
    await assistant.ask("q", "MCH-0002", "commercial", "secret-token", history=[])
    payload, context = agent.calls[0]
    assert (context.machine_id, context.visibility, context.token.get_secret_value()) == ("MCH-0002", "commercial", "secret-token")
    assert "secret-token" not in str(payload)


async def test_ask_returns_the_answer_and_this_turns_trace(agent):
    result = await assistant.ask("q", "MCH-0001", "full", "tok")
    assert result.answer == "the answer" and result.trace == []


async def test_a_question_without_a_machine_has_no_machine_in_scope(agent):
    await assistant.ask("what quotes do we have?", None, "commercial", "tok")
    payload, context = agent.calls[0]
    assert context.machine_id is None
    first = payload["messages"][0]
    assert isinstance(first, SystemMessage) and first.content.startswith("No machine is in scope")
    assert "machine_id: None" not in first.content
