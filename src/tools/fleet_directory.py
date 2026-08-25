"""Real machine / company / user identity relationships from the Project-Q2-Database dataset.

Hardcoded from data/AROL_Q2_synthetic_fleet_dataset.xlsx (Machines, Users sheets)
rather than read at runtime, matching how the other tool modules hardcode their
mock data. This is the real fleet, not mock data -- it exists so tools can resolve
between id spaces (machineId, companyId, userId, serialNumber) that are all
distinct in the dataset. Access-control (visibility) enforcement using this data
belongs in an upstream identity/visibility-check step, which does not exist yet.
"""

from __future__ import annotations

MACHINE_TO_COMPANY: dict[str, str] = {
    "MCH-0001": "CMP-001",
    "MCH-0002": "CMP-001",
    "MCH-0003": "CMP-001",
    "MCH-0004": "CMP-003",
    "MCH-0005": "CMP-003",
    "MCH-0006": "CMP-004",
    "MCH-0007": "CMP-002",
    "MCH-0008": "CMP-002",
}

MACHINE_TO_SERIAL: dict[str, str] = {
    "MCH-0001": "15610",
    "MCH-0002": "17203",
    "MCH-0003": "17579",
    "MCH-0004": "17478",
    "MCH-0005": "A4344",
    "MCH-0006": "A2064",
    "MCH-0007": "A2055",
    "MCH-0008": "A2132",
}

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


def company_for_machine(machine_id: str) -> str | None:
    return MACHINE_TO_COMPANY.get(machine_id)


def company_for_user(user_id: str) -> str | None:
    return USER_TO_COMPANY.get(user_id)


def user_can_access_machine(user_id: str, machine_id: str) -> bool:
    """Tenant boundary only (companyId match) -- does not check visibility tier."""
    user_company = company_for_user(user_id)
    machine_company = company_for_machine(machine_id)
    return user_company is not None and user_company == machine_company
