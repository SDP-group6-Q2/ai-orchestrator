"""Interactive terminal runner for a single specialist agent, bypassing the supervisor.

Usage (from the project root):

    python -m src.run_specialist_in_terminal manuals \
        --question "What does error E204 mean?" \
        --machine-id MCH-0004

    python -m src.run_specialist_in_terminal iot \
        --machine-id MCH-0004

    python -m src.run_specialist_in_terminal diagnostics \
        --machine-id MCH-0004

    python -m src.run_specialist_in_terminal orders \
        --user-id USR-011

    python -m src.run_specialist_in_terminal commercial \
        --user-id USR-011

    python -m src.run_specialist_in_terminal service \
        --machine-id MCH-0004
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

from langchain_ollama import ChatOllama

from src.agents import (
    make_commercial_agent,
    make_diagnostics_tool,
    make_iot_tool,
    make_manuals_tool,
    make_orders_tool,
    make_service_tool,
    make_technical_agent,
)

from src.tools.manuals_tools import show_last_retrieval

logger = logging.getLogger(__name__)


# Tools: plain LangChain @tool callables, invoked with a flat kwargs dict
# and returning a string directly.
# "args" lists which extra kwargs they expect.
_TOOLS = {
    "manuals": {
        "factory": make_manuals_tool,
        "args": ["machine_id"],
    },
    "iot": {
        "factory": make_iot_tool,
        "args": ["machine_id"],
    },
    "service": {
        "factory": make_service_tool,
        "args": ["machine_id"],
    },
    "orders": {
        "factory": make_orders_tool,
        "args": ["user_id"],
    },
    "diagnostics": {
        "factory": make_diagnostics_tool,
        "args": ["machine_id"],
    },
}


# Agents: compiled LangGraph agents created with create_agent.
# They are invoked with:
#
# {
#     "messages": [...]
# }
#
# and return:
#
# {
#     "messages": [...]
# }
_AGENTS = {
    "technical": {
        "factory": make_technical_agent,
    },
    "commercial": {
        "factory": make_commercial_agent,
    },
}


_SPECIALISTS = sorted(set(_TOOLS) | set(_AGENTS))


def _clean_assistant_response(text: str) -> str:
    """Remove internal sources and tool traces from user-facing responses."""

    if not text:
        return text

    # Remove everything starting from a Sources section.
    text = re.sub(
        r"\n\s*(?:#{1,6}\s*)?(?:\*\*)?Sources(?:\*\*)?\s*:?\s*\n.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Safety net: remove any leaked internal tool-call references.
    text = re.sub(
        r"【assistant\s+to=.*?】",
        "",
        text,
        flags=re.DOTALL,
    )

    return text.strip()

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a single FleetAssistant specialist locally, "
            "without the supervisor."
        )
    )

    parser.add_argument(
        "specialist",
        choices=_SPECIALISTS,
        help="Which specialist agent to call.",
    )

    parser.add_argument(
        "--question",
        help=(
            "Single request to send, then exit. "
            "Omit to start an interactive session."
        ),
    )

    parser.add_argument(
        "--user-id",
        default="USR-001",
        help="User id to pass to specialists that need it.",
    )

    parser.add_argument(
        "--machine-id",
        default="MCH-0001",
        help="Machine id to pass to specialists that need it.",
    )

    parser.add_argument(
        "--company-id",
        default="CMP-001",
        help="Company id to pass to specialists that need it.",
    )

    parser.add_argument(
        "--model",
        default="gpt-oss:20b-cloud",
        help="Ollama model name.",
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:11434",
        help="Ollama server base URL.",
    )

    parser.add_argument(
        "--show-retrieval",
        action="store_true",
        help=(
            "After each manuals call, print the retrieved chunks "
            "(pre- and post-rerank) that were sent to the LLM."
        ),
    )

    return parser.parse_args()


def _build_caller(
    specialist: str,
    llm: ChatOllama,
):
    """Build a request -> answer callable for a tool or agent specialist."""

    # -----------------------------
    # SIMPLE TOOL SPECIALISTS
    # -----------------------------
    if specialist in _TOOLS:
        spec = _TOOLS[specialist]

        tool = spec["factory"](llm)
        arg_names = spec["args"]

        def call(
            request: str,
            *,
            user_id: str,
            machine_id: str,
            company_id: str,
        ) -> str:
            tool_input = {
                "request": request,
            }

            available = {
                "user_id": user_id,
                "machine_id": machine_id,
                "company_id": company_id,
            }

            for name in arg_names:
                tool_input[name] = available[name]

            response = tool.invoke(tool_input)

            if isinstance(response, str):
                return _clean_assistant_response(response)

            return str(response)

        return call

    # -----------------------------
    # LANGGRAPH AGENT SPECIALISTS
    # -----------------------------
    if specialist in _AGENTS:

        def call(
            request: str,
            *,
            user_id: str,
            machine_id: str,
            company_id: str,
        ) -> str:

            if specialist == "commercial":
                agent = _AGENTS[specialist]["factory"](
                    llm,
                    user_id=user_id,
                )
            else:
                agent = _AGENTS[specialist]["factory"](llm)

            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": request,
                        }
                    ]
                }
            )

            # Application-level enforcement for inaccessible
            # commercial resources.
            for message in result["messages"]:
                content = getattr(
                    message,
                    "content",
                    "",
                )

                if (
                    isinstance(content, str)
                    and "ACCESS_DENIED_OR_UNAVAILABLE" in content
                ):
                    return (
                        "You don't have access to the requested "
                        "commercial information."
                    )

            answer = result["messages"][-1].content

            return _clean_assistant_response(answer)

        return call

    raise ValueError(
        f"Unknown specialist: {specialist}"
    )

def _build_request(
    history: list[tuple[str, str]],
    question: str,
) -> str:
    if not history:
        return question

    transcript = "\n".join(
        f"User: {user_message}\nAssistant: {assistant_message}"
        for user_message, assistant_message in history
    )

    return (
        "Here is the conversation so far:\n"
        f"{transcript}\n\n"
        f"Now answer the user's new message: {question}"
    )


def _run_once(
    caller,
    history: list[tuple[str, str]],
    question: str,
    user_id: str,
    machine_id: str,
    company_id: str,
    show_retrieval: bool,
) -> None:
    request = _build_request(
        history,
        question,
    )

    response = caller(
        request,
        user_id=user_id,
        machine_id=machine_id,
        company_id=company_id,
    )

    # Final sanitization before storing or displaying the response.
    response = _clean_assistant_response(response)

    history.append(
        (
            question,
            response,
        )
    )

    if show_retrieval:
        print(f"\n{show_last_retrieval()}\n")

    print(f"\n{response}\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    args = _parse_args()

    llm = ChatOllama(
        model=args.model,
        base_url=args.base_url,
    )

    caller = _build_caller(
        args.specialist,
        llm,
    )

    history: list[tuple[str, str]] = []

if args.question:
    _run_once(
        caller,
        history,
        args.question,
        args.user_id,
        args.machine_id,
        args.company_id,
        args.show_retrieval,
    )
    return

    print(
        f"FleetAssistant '{args.specialist}' specialist local session. "
        "Type 'exit' or 'quit' to stop.\n"
    )

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

_run_once(
    caller,
    history,
    request,
    args.user_id,
    args.machine_id,
    args.company_id,
    args.show_retrieval,
)


if __name__ == "__main__":
    main()