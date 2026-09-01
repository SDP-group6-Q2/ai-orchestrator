from __future__ import annotations

from src.db.db import get_db


def get_user_context(user_id: str) -> dict | None:
    """
    Return the security context for a user.

    The returned dictionary contains:
    - userId
    - companyId
    - visibility
    """

    query = """
        SELECT
            "userId",
            "companyId",
            "visibility"
        FROM users
        WHERE "userId" = %s
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