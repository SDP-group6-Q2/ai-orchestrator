# ai-orchestrator

The AI orchestration layer connecting the AROL Customer Platform backend to the specialized AI agents (Manuals, IoT, Orders, Service). It is a LangGraph workflow that loops an orchestrator over agent nodes until it has enough grounded evidence to answer.

## How to run it

1. Install and start [Ollama](https://ollama.com/download), then pull a model that supports tool calling and JSON-schema output (e.g. `llama3.1`, or `llama3.1:cloud` / `gpt-oss:20b-cloud` if using Ollama's cloud tier):
   ```bash
   ollama pull llama3.1
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # Windows Git Bash
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run Assistant:
   ```bash
   python -m src.run_in_terminal
   ```

## Architecture

```
POST /orchestrate
      |
      v
 FleetAssistant.run(message, user_id, machine_id)
      |
      v
 orchestrator ⇄ manuals_agent | iot_agent | orders_agent | service_agent   (loops until enough evidence)
      |
      v
 synthetizer
      |
      v
 response returned to backend
```

## FleetAssistant

`FleetAssistant` is the class-based LangGraph flow the API above delegates to: an `orchestrator` node loops over `manuals_agent` / `iot_agent` / `orders_agent` / `service_agent` (each grounds its answer via an Ollama tool-calling loop against a swappable backend — local placeholders today, real services/MCP later) until it routes to `synthetizer` for the final answer.

To try it directly from a terminal instead of through the FastAPI service:

INFO-level logs print each orchestrator routing decision and agent tool call as they happen; use `--verbose` to also print the final plan and any recorded error.

## Status

`manuals_agent`, `iot_agent`, `orders_agent` and `service_agent` are wired end-to-end against local placeholder backends (in-memory manual corpus, telemetry log, order/contract log, ticket log) so the orchestration logic and tool-calling pattern can be validated before the real backends (RAG, MCP tool calls, ERP/CRM/IoT integrations) are implemented.
