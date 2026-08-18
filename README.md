# ai-orchestrator

The AI orchestration layer connecting the AROL Customer Platform backend to the specialized AI agents (Manuals, IoT, Orders, Service). It is a LangGraph supervisor agent that calls out to specialist tools until it has enough grounded evidence to answer.

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
4. Run Assistant:
   ```bash
   python -m src.run_in_terminal
   ```

## How it works

Refer to [Documentation](docs/README.md)