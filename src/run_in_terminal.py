"""Interactive terminal runner for the assistant.

The assistant needs the MCP server (its tools) and a user token. Log in through the API, or pass a token:

    python -m src.run_in_terminal --email user@example.com --password ... --api-url http://localhost:8000
    python -m src.run_in_terminal --token <jwt> --visibility technician --machine-id MCH-0001
    python -m src.run_in_terminal --email ... --password ... --question "Any open alarms?"

MCP_SERVER_URL (default http://localhost:9000/mcp) says where the MCP server is.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

import httpx

from src.assistant import ask


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the assistant locally from the terminal.")
    parser.add_argument("--question", help="Single question to ask, then exit. Omit to start an interactive session.")
    parser.add_argument("--machine-id", default="MCH-0001", help="Machine in scope for the conversation.")
    parser.add_argument("--model", default="gpt-oss:20b-cloud", help="Ollama model name.")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama server base URL.")

    auth = parser.add_argument_group("who you are (either a login, or a token and tier)")
    auth.add_argument("--email", help="Log in through the API with this email...")
    auth.add_argument("--password", help="...and this password.")
    auth.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"), help="Platform API base URL.")
    auth.add_argument("--token", default=os.getenv("AROL_TOKEN"), help="An existing JWT (or set AROL_TOKEN).")
    auth.add_argument("--visibility", default="full", choices=["full", "technician", "commercial"],
                      help="Tier to use with --token (a login reads it from the API).")
    return parser.parse_args()


def _login(args: argparse.Namespace) -> tuple[str, str]:
    """(token, visibility) for the user, through the API."""
    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        response = client.post("/auth/jwt/login", data={"username": args.email, "password": args.password})
        response.raise_for_status()
        token = response.json()["access_token"]
        me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        me.raise_for_status()
        return token, me.json().get("visibility") or "full"


def _credentials(args: argparse.Namespace) -> tuple[str, str]:
    if args.email and args.password:
        return _login(args)
    if args.token:
        return args.token, args.visibility
    raise SystemExit("Provide --email and --password, or --token (or set AROL_TOKEN).")


async def _run_once(question: str, machine_id: str, visibility: str, token: str) -> None:
    result = await ask(question, machine_id=machine_id, visibility=visibility, token=token)
    print(f"\nAssistant: {result}\n")


async def _session(args: argparse.Namespace, token: str, visibility: str) -> None:
    if args.question:
        await _run_once(args.question, args.machine_id, visibility, token)
        return

    print(f"Assistant local terminal session (tier: {visibility}). Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            question = (await asyncio.to_thread(input, "You: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break

        await _run_once(question, args.machine_id, visibility, token)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args()
    # Read when src.assistant builds its graph, lazily on the first ask.
    os.environ["LLAMA_MODEL"] = args.model
    os.environ["LLAMA_BASE_URL"] = args.base_url
    token, visibility = _credentials(args)
    asyncio.run(_session(args, token, visibility))


if __name__ == "__main__":
    main()
