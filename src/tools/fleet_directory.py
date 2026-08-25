"""Real machine / company / user identity relationships from the Project-Q2-Database dataset.

Machine <-> company/serial resolution (`machine_lookup`) queries the fleet
Postgres DB directly (same `machines` table `fleet_tools.py` queries). User
<-> company/visibility data below is still hardcoded from
data/AROL_Q2_synthetic_fleet_dataset.xlsx (Users sheet), matching how the other
tool modules hardcode their mock data, pending a real lookup for that side too.
Access-control (visibility) enforcement using this data belongs in an upstream
identity/visibility-check step, which does not exist yet.
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


USER_TO_COMPANY: dict[str, str] = {
    "USR-001": "CMP-001",
    "USR-002": "CMP-001",
    "USR-003": "CMP-001",
    "USR-004": "CMP-001",
    "USR-005": "CMP-001",
    "USR-006": "CMP-001",
    "USR-007": "CMP-002",
    "USR-008": "CMP-002",
    "USR-009": "CMP-002",
    "USR-010": "CMP-002",
    "USR-011": "CMP-003",
    "USR-012": "CMP-003",
    "USR-013": "CMP-003",
    "USR-014": "CMP-003",
    "USR-015": "CMP-004",
    "USR-016": "CMP-004",
    "USR-017": "CMP-004",
    "USR-018": "CMP-005",
    "USR-019": "CMP-005",
}

USER_VISIBILITY: dict[str, str] = {
    "USR-001": "full",
    "USR-002": "technician",
    "USR-003": "technician",
    "USR-004": "commercial",
    "USR-005": "full",
    "USR-006": "technician",
    "USR-007": "full",
    "USR-008": "technician",
    "USR-009": "technician",
    "USR-010": "commercial",
    "USR-011": "full",
    "USR-012": "technician",
    "USR-013": "technician",
    "USR-014": "commercial",
    "USR-015": "full",
    "USR-016": "technician",
    "USR-017": "technician",
    "USR-018": "full",
    "USR-019": "commercial",
}


def company_for_user(user_id: str) -> str | None:
    return USER_TO_COMPANY.get(user_id)


def user_can_access_machine(user_id: str, machine_id: str) -> bool:
    """Tenant boundary only (companyId match) -- does not check visibility tier."""
    user_company = company_for_user(user_id)
    machine = machine_lookup(machine_id)
    return user_company is not None and machine is not None and user_company == machine["company_id"]
