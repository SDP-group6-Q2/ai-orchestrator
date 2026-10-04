"""App-wide constants (global, non-request-scoped -- see src/context.py for per-request identity instead)."""

import os

# The synthetic dataset only contains telemetry/alarms/tickets through early August 2026. Pinning "today"
# inside that window lets agents reason correctly about validity/overdue/recency instead of guessing or
# defaulting to the real wall-clock date.
REFERENCE_DATE = os.getenv("REFERENCE_DATE", "2026-08-05")

# The MCP server exposing the platform's data as tools (streamable HTTP).
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:9000/mcp")
