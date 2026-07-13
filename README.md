# ai-orchestrator

The AI orchestration layer connecting the AROL Customer Platform backend to the specialized AI agents (Manuals, IoT, Orders, Troubleshooting, Service).

It exposes a single HTTP endpoint that classifies intent, routes to the right agent via a LangGraph graph, and returns the agent's answer.

## How to run it

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows Git Bash
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
   ```
4. Check it's up:
   ```bash
   curl http://127.0.0.1:8001/health
   ```
5. Send a test request:
   ```bash
   curl -X POST http://127.0.0.1:8001/orchestrate \
     -H "Content-Type: application/json" \
     -d '{
           "message": "I get an error code E204 on the machine",
           "user_id": "u1",
           "customer_id": "c1",
           "machine_id": "m1",
           "session_id": "s1"
         }'
   ```

The backend runs on port `8000`; the orchestrator runs on `8001`.

## Architecture

```
POST /orchestrate
      |
      v
 classify_intent (LLM-based intent router via Ollama, falls back to keywords)
      |
      v
 conditional routing (selected_agent)
      |
      v
 agent node (manuals | iot | orders | troubleshooting | service)
      |
      v
 response returned to backend
```

- `app/main.py` — FastAPI app, exposes `POST /orchestrate` and `GET /health`.
- `app/graph.py` — builds the LangGraph `StateGraph`: `classify_intent` node, conditional edges to one agent node, then `END`.
- `app/nodes/classify_intent.py` — router that sets `intent` / `selected_agent` via an Ollama LLM call constrained to a JSON schema; falls back to keyword matching if Ollama is unreachable or returns an invalid response.
- `app/agents/` — one module per agent (`manuals_agent.py`, `iot_agent.py`, `orders_agent.py`, `troubleshooting_agent.py`, `service_agent.py`). Currently placeholder stubs; will call out to MCP servers / RAG / tools.
- `app/state.py` — shared `OrchestratorState` passed through the graph.
- `app/schemas.py` — Pydantic request/response models for the API.
- `app/config.py` — settings (loaded from environment / `.env`).

## Shared state

Every node reads/writes a subset of this state:

| Field | Description |
|---|---|
| `message` | the user's message |
| `user_id` | end-user identifier |
| `customer_id` | AROL customer identifier |
| `machine_id` | machine the request relates to (optional) |
| `session_id` | conversation/session identifier |
| `intent` | classified intent (set by `classify_intent`) |
| `selected_agent` | agent chosen for this turn (set by `classify_intent`) |
| `answer` | final answer text (set by the selected agent) |
| `citations` | list of `{source, snippet}` supporting the answer |
| `error` | populated if something failed during orchestration |

## Status

Agents are currently placeholders that return stub answers and citations, wired end-to-end through the LangGraph router so the API contract and graph structure can be validated before the real agent logic (RAG, MCP tool calls, ERP/CRM/IoT integrations) is implemented.
