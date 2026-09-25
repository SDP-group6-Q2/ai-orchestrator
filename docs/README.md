## Architecture

```
backend  ──POST /chat + user's JWT──▶  orchestrator  ──MCP tool calls + same JWT──▶  mcp-server  ──HTTP + same JWT──▶  api
                                        (one agent)                                   (tools, manuals RAG)               (data, access rules)
```

The orchestrator is stateless and has no database. The user's identity is a single JWT that travels the whole
chain, so the API's access rules (company, visibility tier) apply to every tool call exactly as they do for the
frontend.

### One agent, narrowed per request by the user's tier

```mermaid
flowchart TD
    Start([POST /chat]) --> Agent
    subgraph Agent["agent · create_agent + TierSkillsMiddleware"]
        direction TB
        MW[["per model call: show only this tier's tools,\nadd this tier's skills to the prompt,\nnote what is NOT available"]] --> Model[[model]]
        Model <-->|MCP tool calls\n(user's token)| Tools[[19 MCP tools]]
        Tools -.->|hidden tool called?\nvetoed, never reaches MCP| MW
    end
    Agent --> End([answer + trace])
```

There is no intent classifier. An earlier design routed each request to a technical or a commercial agent; the
router misclassified ordinary questions (and a misroute became a hard refusal), cost an extra LLM call per turn,
and couldn't serve questions spanning both areas. Now a single agent holds every tool and the middleware
(`src/middleware.py`) decides, per model call, what this user's tier may see:

| Tier | Machines & manuals | Telemetry, alarms, maintenance | Quotes & orders | Tools shown |
| --- | --- | --- | --- | --- |
| `full` | yes | yes | yes | 19 |
| `technician` | yes | yes | no | 10 |
| `commercial` | yes | no | yes | 12 |

- The model only sees its tier's tools, so it can't try the rest. A call for a hidden tool anyway (a
  hallucination) is vetoed by the middleware without reaching the MCP server.
- The system prompt lists what is **not** available to the user, and tells the model to decline those requests
  plainly rather than answer from earlier messages or general knowledge.
- This is defense-in-depth. The API enforces access on every tool call with the user's own token, whatever the
  model does; a request outside the user's scope is declined explicitly, never answered from other data and
  never returned as empty.
- The tier comes from the trusted caller (`AgentContext.visibility`, sent by the backend), never from the model.

### Skills are markdown files

`src/skills/*.md`: YAML frontmatter plus instructions.

```markdown
---
name: quotes
description: "Quotations, revision history, and quote line items for the current company."
visibility: [full, commercial]     # tiers that may use this skill
tools:                             # the MCP tools it covers
  - get_company_quotes
  - get_quote_revisions
---
Use get_company_quotes to ...
```

`src/skills/loader.py` validates them strictly at startup: a malformed file, an unknown tier, or a tool claimed by
two skills is an error. When the agent is built it also checks that every tool a skill names exists on the MCP
server, and warns about server tools no skill covers (they have no instructions, so the model isn't offered
them). To add a tool: add it to the MCP server, then list it in a skill. The instructions of the skills a tier may
use are injected into the prompt statically; the frontmatter leaves room for loading them on demand later.

| Skill | Tiers | MCP tools |
| --- | --- | --- |
| fleet | all | `get_company_machines`, `get_machine_details` |
| manuals | all | `get_manual_excerpts` |
| diagnostics | full, technician | `get_latest_telemetry_snapshot`, `get_telemetry_summary`, `get_telemetry_history`, `get_alarm_summary`, `get_alarm_history`, `get_maintenance_history` |
| maintenance | full, technician | `get_company_maintenance_tickets` |
| quotes | full, commercial | `get_company_quotes`, `get_quote_details`, `get_quote_revisions`, `get_latest_quote_revision`, `get_quote_lines` |
| orders | full, commercial | `get_company_orders`, `get_order_details`, `get_order_lines`, `get_orders_by_quote` |

### Tools come from the MCP server

`src/mcp_client.py` connects to the MCP server, loads its tool list once (lazily, so the orchestrator can start
before the MCP server is ready), and hands the agent the tools. The **user's token** rides in `AgentContext`
(`src/context.py`), LangGraph's hard channel: never in agent state, never visible to the model, never logged.
A tool-call interceptor adds it as the `Authorization` header of every MCP request; with no token, the call is
refused before it leaves. MCP tools return ready-to-read markdown and report errors as text (access denied, not
found, service unavailable) that the model is told to relay plainly.

### History and traces

The backend owns the conversation (users, persistence); the orchestrator remembers nothing between requests.
Each call gets a fresh checkpointer thread, and only the last 20 history messages are given to the model.

So that follow-ups can build on data already retrieved, each answer comes with a **trace**: the tool calls of
that turn, each with its arguments and a one-line summary of the result (300 characters, at most 8 per turn). The
backend stores the trace with the assistant message and sends it back in `history`; the orchestrator shows the
model the traces of the last 3 assistant turns as "data you retrieved earlier, possibly out of date; call the tool
again for fresh or complete data".

### Entry points

`src/assistant.py` exposes `ask` (returns the answer and the trace) and `run` (the full agent state). Both are
`async` and take `question, machine_id, visibility, token, history=None`.

`src/server.py` serves it over HTTP with one endpoint:

```
POST /chat        Authorization: Bearer <the end user's JWT>
{"question": "...", "machine_id": "MCH-0001", "visibility": "technician",
 "history": [{"role": "user", "content": "..."},
             {"role": "assistant", "content": "...", "trace": [{"tool": "...", "args": {}, "summary": "...", "error": false}]}]}
-> {"answer": "...", "trace": [ ... ]}
```

`401` without a bearer token, `503` if the MCP server can't be reached. There is no other authentication yet, so
the service must only be reachable from trusted services (in docker compose it is not published to the host).

`docs/TASK.md` is the original task description this project started from.
