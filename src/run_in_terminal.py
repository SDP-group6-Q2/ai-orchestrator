"""Interactive terminal runner for FleetAssistant.

Usage (from the project root):
    python -m local_run.run
    python -m local_run.run --user-id u1 --machine-id m1
    python -m local_run.run --question "I get error E204" --user-id u1 --machine-id m1
"""

from __future__ import annotations

import argparse
import logging

from src import FleetAssistant


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FleetAssistant locally from the terminal.")
    parser.add_argument("--question", help="Single question to ask, then exit. Omit to start an interactive session.")
    parser.add_argument("--user-id", default="local-user", help="User id to attach to the request.")
    parser.add_argument("--machine-id", default=1, type=int, help="Machine id to attach to the request.")
    parser.add_argument("--model", default="gpt-oss:20b-cloud", help="Ollama model name.")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama server base URL.")
    return parser.parse_args()



def _run_once(assistant: FleetAssistant, question: str, user_id: str, machine_id: int) -> None:
    result = assistant.ask(question, user_id=user_id, machine_id=machine_id)
    print(f"\nAssistant: {result}\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args()
    assistant = FleetAssistant(model=args.model, llama_base_url=args.base_url)

    if args.question:
        _run_once(assistant, args.question, args.user_id, args.machine_id)
        return

    print("FleetAssistant local terminal session. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        _run_once(assistant, question, args.user_id, args.machine_id)


if __name__ == "__main__":
    main()
