"""Interactive terminal runner for a single specialist agent, bypassing the supervisor.

Usage (from the project root):
    python -m src.run_specialist_in_terminal manuals --question "What does error E204 mean?"
    python -m src.run_specialist_in_terminal iot --machine-id 1
    python -m src.run_specialist_in_terminal orders --user-id u1
    python -m src.run_specialist_in_terminal service --machine-id 1
"""

from __future__ import annotations

import argparse
import logging

from langchain_ollama import ChatOllama

from src.agents import make_iot_tool, make_manuals_tool, make_orders_tool, make_service_tool

logger = logging.getLogger(__name__)

_SPECIALISTS = {
    "manuals": {"factory": make_manuals_tool, "needs_user_id": False, "needs_machine_id": False},
    "iot": {"factory": make_iot_tool, "needs_user_id": False, "needs_machine_id": True},
    "orders": {"factory": make_orders_tool, "needs_user_id": True, "needs_machine_id": False},
    "service": {"factory": make_service_tool, "needs_user_id": False, "needs_machine_id": True},
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single FleetAssistant specialist locally, without the supervisor.")
    parser.add_argument("specialist", choices=sorted(_SPECIALISTS), help="Which specialist agent to call.")
    parser.add_argument("--question", help="Single request to send, then exit. Omit to start an interactive session.")
    parser.add_argument("--user-id", default=1, type=int, help="User id to pass, for specialists that need it (orders).")
    parser.add_argument("--machine-id", default=1, type=int, help="Machine id to pass, for specialists that need it (iot, service).")
    parser.add_argument("--model", default="gpt-oss:20b-cloud", help="Ollama model name.")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama server base URL.")
    return parser.parse_args()


def _build_tool(specialist: str, llm: ChatOllama):
    spec = _SPECIALISTS[specialist]
    return spec["factory"](llm), spec


def _build_request(history: list[tuple[str, str]], question: str) -> str:
    if not history:
        return question

    transcript = "\n".join(f"User: {q}\nAssistant: {a}" for q, a in history)
    return (
        "Here is the conversation so far:\n"
        f"{transcript}\n\n"
        f"Now answer the user's new message: {question}"
    )


def _call_specialist(tool, spec: dict, request: str, user_id: str, machine_id: int) -> str:
    tool_input = {"request": request}
    if spec["needs_user_id"]:
        tool_input["user_id"] = user_id
    if spec["needs_machine_id"]:
        tool_input["machine_id"] = machine_id
    return tool.invoke(tool_input)


def _run_once(tool, spec: dict, history: list[tuple[str, str]], question: str, user_id: str, machine_id: int) -> None:
    request = _build_request(history, question)
    response = _call_specialist(tool, spec, request, user_id, machine_id)
    history.append((question, response))
    print(f"\n{response}\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args()

    llm = ChatOllama(model=args.model, base_url=args.base_url)
    tool, spec = _build_tool(args.specialist, llm)
    history: list[tuple[str, str]] = []

    if args.question:
        _run_once(tool, spec, history, args.question, args.user_id, args.machine_id)
        return

    print(f"FleetAssistant '{args.specialist}' specialist local session. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            request = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not request:
            continue
        if request.lower() in {"exit", "quit"}:
            break

        _run_once(tool, spec, history, request, args.user_id, args.machine_id)


if __name__ == "__main__":
    main()
