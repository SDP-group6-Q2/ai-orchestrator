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
    assert isinstance(first, SystemMessage) and first.content.startswith("No machine is in scope") and "Reply in English" in first.content
    assert "machine_id: None" not in first.content


def test_typographic_hyphens_in_ids_and_names_become_ascii():
    text = "Machine MCH‑0001 and TS‑EURO‑PK, quote QTE–2025‑0001, pick‑and‑place – a dash."
    assert assistant.normalize_answer(text) == "Machine MCH-0001 and TS-EURO-PK, quote QTE-2025-0001, pick-and-place – a dash."


def test_ordinary_punctuation_is_left_alone():
    text = "Range 10–20 - fine — really: ABC-123."
    assert assistant.normalize_answer(text) == text


async def test_a_transient_model_error_is_retried_once(agent, monkeypatch):
    import ollama

    calls = {"n": 0}
    original = agent.ainvoke

    async def flaky(payload, config=None, context=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ollama.ResponseError("Internal Server Error", 500)
        return await original(payload, config=config, context=context)

    monkeypatch.setattr(agent, "ainvoke", flaky)
    result = await assistant.ask("q", "MCH-0001", "full", "tok")
    assert calls["n"] == 2 and result.answer == "the answer"


async def test_a_persistent_or_client_error_is_not_retried_forever(agent, monkeypatch):
    import ollama
    import pytest

    calls = {"n": 0}

    async def always_500(payload, config=None, context=None):
        calls["n"] += 1
        raise ollama.ResponseError("down", 503)

    monkeypatch.setattr(agent, "ainvoke", always_500)
    with pytest.raises(ollama.ResponseError):
        await assistant.ask("q", "MCH-0001", "full", "tok")
    assert calls["n"] == 2

    async def bad_request(payload, config=None, context=None):
        calls["n"] += 1
        raise ollama.ResponseError("bad", 400)

    calls["n"] = 0
    monkeypatch.setattr(agent, "ainvoke", bad_request)
    with pytest.raises(ollama.ResponseError):
        await assistant.ask("q", "MCH-0001", "full", "tok")
    assert calls["n"] == 1


async def test_a_dropped_connection_is_retried_like_a_server_error(agent, monkeypatch):
    import ollama

    calls = {"n": 0}
    original = agent.ainvoke

    async def dropped(payload, config=None, context=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ollama.ResponseError("Internal Server Error")  # no status: the client reports -1
        return await original(payload, config=config, context=context)

    monkeypatch.setattr(agent, "ainvoke", dropped)
    result = await assistant.ask("q", "MCH-0001", "full", "tok")
    assert calls["n"] == 2 and result.answer == "the answer"


def _replying(agent, monkeypatch, *replies):
    """Make the agent end its turns with these replies, in order."""
    queue = list(replies)

    async def ainvoke(payload, config=None, context=None):
        agent.calls.append((payload, context))
        return {"messages": [*payload["messages"], AIMessage(content=queue.pop(0))]}

    monkeypatch.setattr(agent, "ainvoke", ainvoke)


@pytest.mark.parametrize("broken", ["", "  \n", '{"quote_id":"QTE-2025-0008"}', '[{"machine_id": "MCH-0001"}]'])
async def test_an_empty_or_json_reply_makes_the_model_continue_the_turn(agent, monkeypatch, broken):
    _replying(agent, monkeypatch, broken, "the real answer")
    result = await assistant.ask("q", "MCH-0001", "full", "tok")
    assert result.answer == "the real answer"
    retried = agent.calls[1][0]["messages"]
    assert retried[:-1] == agent.calls[0][0]["messages"]  # same turn, the broken reply dropped
    assert isinstance(retried[-1], SystemMessage) and "Continue" in retried[-1].content


async def test_a_second_broken_reply_gets_a_fallback_not_an_empty_answer(agent, monkeypatch):
    _replying(agent, monkeypatch, "", '{"quote_id":"QTE-2026-0009"}')
    result = await assistant.ask("q", None, "full", "tok")
    assert result.answer == assistant.FALLBACK_ANSWER and len(agent.calls) == 2


@pytest.mark.parametrize("answer", ["3", "Yes.", "true", "**3 orders**"])
async def test_short_or_scalar_answers_are_not_mistaken_for_broken_ones(agent, monkeypatch, answer):
    _replying(agent, monkeypatch, answer)
    result = await assistant.ask("q", None, "full", "tok")
    assert result.answer == answer and len(agent.calls) == 1
