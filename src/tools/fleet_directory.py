"""Machine identity lookup against the real fleet Postgres DB.

Company/visibility scoping for a *user* belongs to src.security.access
(get_user_context, backed by the real `users` table) -- this module only
resolves a machine's own company/serial identity, used by tools that need to
verify a machine_id belongs to the requesting user's company (e.g.
manuals_tools.get_manual_excerpts, telemetry_tools' per-machine tools).
"""

from __future__ import annotations

from src.db.db import get_db


def machine_lookup(machine_id: str) -> dict[str, str] | None:
    """Look up a machine's company_id and serial_number from the fleet DB."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT companyid, serialnumber FROM machines WHERE machineid = %s;",
                (machine_id,),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return {"company_id": row["companyid"], "serial_number": row["serialnumber"]}
