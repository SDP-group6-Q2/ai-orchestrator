# ai-orchestrator

The AI layer of the AROL Customer Platform: **one LangGraph agent** that answers technical questions (machines,
telemetry, alarms, maintenance tickets, manuals) and commercial ones (quotes and orders), including questions
that span both. It holds no data of its own: its tools come from the **MCP server**, which calls the platform
API with the end user's own token, and which tools and instructions the model gets depends on the user's access
tier. See [Documentation](docs/README.md).

## Run it

Normally through docker compose, from the project root: the backend calls `POST /chat` on this service.

```bash
docker compose up -d           # db, api, mcp-server and orchestrator
```

To try it directly from a terminal (needs the MCP server and the API running, and [Ollama](https://ollama.com/download)
with a tool-calling model such as `gpt-oss:20b-cloud`):

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export MCP_SERVER_URL=http://localhost:9000/mcp
python -m src.run_in_terminal --email user@example.com --password '...' --api-url http://localhost:8000 \
    --machine-id MCH-0001
```

| Variable | Description | Default |
| --- | --- | --- |
| `MCP_SERVER_URL` | The MCP server's streamable-HTTP endpoint | `http://localhost:9000/mcp` |
| `LLAMA_MODEL` / `LLAMA_BASE_URL` | Ollama model and server | `gpt-oss:20b-cloud` / `http://localhost:11434` |
| `REFERENCE_DATE` | "Today" the agents reason relative dates from, pinned inside the dataset's date window | `2026-08-05` |

Tests: `pip install -r requirements-dev.txt && pytest`.
