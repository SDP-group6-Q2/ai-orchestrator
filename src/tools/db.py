"""Shared DuckDB connection for the fleet database.

DuckDB only allows a single read-write connection to a database file at a
time. The tool modules used to open/close a fresh connection on every call,
which caused "Could not set lock on file" errors whenever two tool calls
overlapped (e.g. concurrent/parallel agent tool use). Instead we keep one
process-wide connection open and serialize access to it with a lock.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

import duckdb

DB_PATH = "mock_data.db"

_connection: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()


def _get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        _connection = duckdb.connect(DB_PATH)
    return _connection


@contextmanager
def get_db():
    """Yield the shared DuckDB connection, serialized across threads."""
    with _lock:
        yield _get_connection()
