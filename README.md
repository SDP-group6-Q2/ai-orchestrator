# ai-orchestrator

The AI orchestration layer meant to connect the AROL Customer Platform backend to a set of specialized AI agents. It's a LangGraph graph that routes each request (via an LLM classifier) to a `technical_agent` — grounded in machine manuals (RAG), live telemetry, fleet data, and service tickets — or a `commercial_agent` (currently a stub). See [Documentation](docs/README.md) for the current architecture and what's real vs. mocked/stubbed today.

## How to run it

1. Install and start [Ollama](https://ollama.com/download), then pull a model that supports tool calling (e.g. `llama3.1`, or `llama3.1:cloud` / `gpt-oss:20b-cloud` if using Ollama's cloud tier):
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
4. Start a [PostgreSQL](https://www.postgresql.org/download/) server, then copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   | Variable | Description | Default |
   | --- | --- | --- |
   | `POSTGRES_USER` | Postgres username | `your_username` |
   | `POSTGRES_PASSWORD` | Postgres password | `your_password` |
   | `POSTGRES_HOST` | Postgres host | `localhost` |
   | `POSTGRES_PORT` | Postgres port | `5432` |
   | `ASSISTANT_DB` | Database name to create/use for the assistant | `assistant` |
5. Create the database, load the fleet dataset (`data/AROL_Q2_synthetic_fleet_dataset.xlsx`), and index any manual PDFs found under `data/manuals/`:
   ```bash
   python -m src.db.startup
   ```
6. Run Assistant:
   ```bash
   python -m src.run_in_terminal
   ```

## How it works

Refer to [Documentation](docs/README.md)