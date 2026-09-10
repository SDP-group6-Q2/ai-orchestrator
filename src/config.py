"""App-wide constants (global, non-request-scoped -- see src/context.py for
per-request identity instead)."""

import os

# The synthetic dataset (data/AROL_Q2_synthetic_fleet_dataset.xlsx) only contains
# telemetry/alarms/tickets through early August 2026. Pinning "today" inside that
# window lets agents reason correctly about validity/overdue/recency instead of
# guessing or defaulting to the real wall-clock date.
REFERENCE_DATE = os.getenv("REFERENCE_DATE", "2026-08-05")
