"""Run the scenarios against the assistant and print a scoreboard.

    python -m evals.run [--repeat 2] [--only id1,id2] [--out results.json]

Talks to POST /chat of the orchestrator (ORCHESTRATOR_URL, default http://localhost:8001) with real logins on the
platform API (API_URL, default http://localhost:8000), using the seeded dataset users. It calls the real model,
so it is slow and non-deterministic: use --repeat to see how stable a result is.
"""

import argparse
import json
import os
import time

import httpx

from evals.checks import CHECKS
from evals.scenarios import ALWAYS, SCENARIOS, USERS

API_URL = os.getenv("API_URL", "http://localhost:8000")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")


def _token(user: str, cache: dict) -> str:
    if user not in cache:
        email, password, _ = USERS[user]
        response = httpx.post(f"{API_URL}/auth/jwt/login", data={"username": email, "password": password})
        response.raise_for_status()
        cache[user] = response.json()["access_token"]
    return cache[user]


def run_one(scenario: dict, tokens: dict) -> dict:
    body = {"question": scenario["q"], "visibility": USERS[scenario["user"]][2], "history": []}
    if scenario.get("machine"):
        body["machine_id"] = scenario["machine"]
    started = time.time()
    response = httpx.post(
        f"{ORCHESTRATOR_URL}/chat", json=body, timeout=200,
        headers={"Authorization": f"Bearer {_token(scenario['user'], tokens)}"},
    )
    seconds = time.time() - started
    if response.status_code != 200:
        return {"id": scenario["id"], "failures": [f"HTTP {response.status_code}"], "tools": [], "answer": response.text[:200], "seconds": seconds}
    data = response.json()
    called = [entry["tool"] for entry in data["trace"]]
    answer = data["answer"]
    return {"id": scenario["id"], "failures": evaluate(scenario, called, answer), "tools": called, "answer": answer, "seconds": seconds}


def evaluate(scenario: dict, called: list[str], answer: str) -> list[str]:
    """The reasons this answer fails the scenario (empty when it passes)."""
    failures = []
    for alternatives in scenario.get("tools", []):
        if not set(alternatives) & set(called):
            failures.append(f"expected one of {alternatives}, called {sorted(set(called)) or 'nothing'}")
    if scenario.get("expect_no_tools") and called:
        failures.append(f"should not call tools, called {sorted(set(called))}")
    for tool in scenario.get("forbid", []):
        if tool in called:
            failures.append(f"must not call {tool}")
    for name in [*[c for c in ALWAYS if c not in scenario.get("skip", [])], *scenario.get("checks", [])]:
        reason = CHECKS[name](answer)
        if reason:
            failures.append(f"{name}: {reason}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only", help="comma-separated scenario ids")
    parser.add_argument("--out", help="write full results (answers included) to this JSON file")
    parser.add_argument("--rescore", help="re-apply the current checks to the answers stored in a results JSON, without calling the model")
    args = parser.parse_args()

    chosen = [s for s in SCENARIOS if not args.only or s["id"] in args.only.split(",")]
    tokens: dict = {}
    results = []
    stored = {r["scenario"]: r["runs"] for r in json.load(open(args.rescore))} if args.rescore else {}
    for scenario in chosen:
        if args.rescore:
            runs = [{**run, "failures": evaluate(scenario, run["tools"], run["answer"])} for run in stored[scenario["id"]]]
        else:
            runs = [run_one(scenario, tokens) for _ in range(args.repeat)]
        results.append({"scenario": scenario["id"], "runs": runs})
        passed = sum(1 for r in runs if not r["failures"])
        print(f"{'PASS' if passed == len(runs) else 'FAIL'} {scenario['id']:18} {passed}/{len(runs)}  "
              f"{sum(r['seconds'] for r in runs) / len(runs):5.1f}s  tools={sorted(set(t for r in runs for t in r['tools']))}", flush=True)
        for r in runs:
            for failure in r["failures"]:
                print(f"      - {failure}", flush=True)

    total = sum(len(r["runs"]) for r in results)
    ok = sum(1 for r in results for run in r["runs"] if not run["failures"])
    print(f"\nSCORE: {ok}/{total} runs passed ({100 * ok / total:.0f}%) | scenarios fully passing: "
          f"{sum(1 for r in results if all(not x['failures'] for x in r['runs']))}/{len(results)}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
