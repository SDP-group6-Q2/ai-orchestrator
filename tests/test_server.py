import ollama
import pytest
from fastapi.testclient import TestClient

import src.server as server
from src.assistant import AskResult
from src.mcp_client import McpUnavailableError

BODY = {"question": "q", "machine_id": "MCH-0001", "visibility": "technician", "history": []}
AUTH = {"Authorization": "Bearer abc.def"}
client = TestClient(server.app)


def _ask(monkeypatch, behavior):
    calls = []

    async def fake(question, machine_id, visibility, token, history=None):
        calls.append((question, machine_id, visibility, token, history))
        return behavior()

    monkeypatch.setattr(server, "ask", fake)
    return calls


def test_a_bearer_token_is_required(monkeypatch):
    _ask(monkeypatch, lambda: AskResult("x", []))
    assert client.post("/chat", json=BODY).status_code == 401
    assert client.post("/chat", json=BODY, headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.post("/chat", json=BODY, headers={"Authorization": "Bearer "}).status_code == 401


def test_answer_trace_and_forwarded_token(monkeypatch):
    trace = [{"tool": "get_company_machines", "args": {}, "summary": "| Machine |", "error": False}]
    calls = _ask(monkeypatch, lambda: AskResult("hello", trace))
    history = [{"role": "assistant", "content": "a", "trace": trace}, {"role": "user", "content": "u"}]
    response = client.post("/chat", json={**BODY, "history": history}, headers=AUTH)
    assert response.status_code == 200 and response.json() == {"answer": "hello", "trace": trace}
    _, machine_id, visibility, token, sent_history = calls[0]
    assert (machine_id, visibility, token) == ("MCH-0001", "technician", "abc.def")
    assert sent_history[0]["trace"][0]["tool"] == "get_company_machines" and "trace" not in sent_history[1]


def test_an_unknown_tier_is_rejected(monkeypatch):
    _ask(monkeypatch, lambda: AskResult("x", []))
    assert client.post("/chat", json={**BODY, "visibility": "admin"}, headers=AUTH).status_code == 422


@pytest.mark.parametrize(
    "error, status",
    [
        (McpUnavailableError("down"), 503),
        (ollama.ResponseError("Internal Server Error", 500), 502),
        (ConnectionError("no ollama"), 502),
    ],
)
def test_upstream_failures_are_mapped_not_500(monkeypatch, error, status):
    def boom():
        raise error

    _ask(monkeypatch, boom)
    assert client.post("/chat", json=BODY, headers=AUTH).status_code == status


def test_machine_id_is_optional(monkeypatch):
    calls = _ask(monkeypatch, lambda: AskResult("ok", []))
    body = {k: v for k, v in BODY.items() if k != "machine_id"}
    assert client.post("/chat", json=body, headers=AUTH).status_code == 200
    assert calls[0][1] is None
    assert client.post("/chat", json={**BODY, "machine_id": None}, headers=AUTH).status_code == 200
