from __future__ import annotations

from src.db.db import get_db

ACCESS_DENIED_OR_UNAVAILABLE = "ACCESS_DENIED_OR_UNAVAILABLE"


def get_user_context(user_id: str) -> dict | None:
    """
    Return the security context for a user.

    The returned dictionary contains:
    - userid
    - companyid
    - visibility
    """

    query = """
        SELECT
            "userid",
            "companyid",
            "visibility"
        FROM users
        WHERE "userid" = %s
        LIMIT 1;
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return dict(row)


def can_access_commercial_data(user_context: dict) -> bool:
    """
    Return True if the user can access commercial information.
    """

    return user_context.get("visibility") in {
        "full",
        "commercial",
    }


def can_access_technical_data(user_context: dict) -> bool:
    """
    Return True if the user can access operational data: telemetry, alarms,
    maintenance tickets. Per the spec's access table this is narrower than
    machine identity/documentation (see can_access_machine_identity below).
    """

    return user_context.get("visibility") in {
        "full",
        "technician",
    }


def can_access_machine_identity(user_context: dict) -> bool:
    """
    Return True if the user can access machine identity and documentation:
    Machines, MachineModels, and the manuals. Per the spec, this domain is
    visible to every visibility tier -- the only check is that the user is
    real and belongs to a company at all, not which tier they hold.
    """

    return user_context.get("visibility") in {
        "full",
        "technician",
        "commercial",
    }