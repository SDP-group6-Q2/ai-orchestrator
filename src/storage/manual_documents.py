"""Signed-URL access to the raw manual PDFs, for rendering in the frontend.

Separate from src.tools.manuals_tools' RAG retrieval path (which returns text
excerpts to the LLM) -- this returns a link to the whole file, for a PDF
viewer. The access check is the same one RAG retrieval uses
(authorized_company_for_machine): a real user + real machine ownership,
checked in Postgres, before Supabase is ever asked for anything. Supabase
itself never sees who is asking -- it only ever receives a request for one
specific object key, already pre-authorized by the caller.
"""

from __future__ import annotations

from src.db.db import get_db
from src.storage.supabase_client import create_signed_url
from src.tools.manuals_tools import authorized_company_for_machine


def get_manual_url(user_id: str, machine_id: str) -> str | None:
    """Return a short-lived signed URL for machine_id's manual PDF, or None if
    the caller isn't authorized for that machine or no manual is on file."""
    company_id = authorized_company_for_machine(user_id, machine_id)
    if company_id is None:
        return None

    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT storage_path FROM machines WHERE machineid = %s;",
                (machine_id,),
            )
            row = cursor.fetchone()

    if row is None or row["storage_path"] is None:
        return None

    return create_signed_url(row["storage_path"])
