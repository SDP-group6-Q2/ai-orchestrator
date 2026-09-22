"""Supabase Storage client for the manuals PDF bucket.

The actual PDF bytes live in Supabase Storage (bucket "manuals"), not in
Postgres -- src/db/startup.py's manual_documents table only maps a machine to
its object key (storage_path). This module is the one place that talks to
Supabase directly: callers must run their own access check (see
src.tools.manuals_tools.authorized_company_for_machine) *before* asking this
module for a signed URL -- Supabase itself has no notion of which end user is
asking, so nothing here enforces tenant/visibility rules.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_BUCKET = "manuals"
_SIGNED_URL_TTL_SECONDS = 60

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        _client = create_client(url, key)
    return _client


def create_signed_url(storage_path: str) -> str:
    """Return a short-lived signed URL for one object in the manuals bucket.

    Callers must have already authorized the request -- this function only
    knows about the object key, not who is asking for it."""
    response = _get_client().storage.from_(_BUCKET).create_signed_url(
        storage_path, _SIGNED_URL_TTL_SECONDS
    )
    return response["signedURL"]


def list_bucket_filenames() -> list[str]:
    """List every object name currently in the manuals bucket."""
    entries = _get_client().storage.from_(_BUCKET).list()
    return [entry["name"] for entry in entries]
