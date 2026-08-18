"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations
import logging

from langchain_core.tools import tool
import duckdb
import pandas as pd

from src.tools.db import get_db

logger = logging.getLogger(__name__)


def create_telemetry_tables():
    telemetry_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="TelemetrySnapshots")
    alarms_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="Alarms")

    with get_db() as con:
        con.sql("CREATE OR REPLACE TABLE telemetry_readings AS SELECT * FROM telemetry_df")
        con.sql("CREATE OR REPLACE TABLE alarms AS SELECT * FROM alarms_df")

@tool
def get_telemetry_tables_descriptors():
    """Return the table descriptors for the telemetry readings database."""
    with get_db() as con:
        telemetry_descriptors = con.sql("DESCRIBE telemetry_readings").df().to_dict(orient="records")
        alarms_descriptors = con.sql("DESCRIBE alarms").df().to_dict(orient="records")

    return {
        "telemetry_readings": telemetry_descriptors,
        "alarms": alarms_descriptors
    }

@tool
def query_telemetry_readings(sql_query) -> list[dict]:
    """Using an SQL statement, query telemetry readings for a given machine and optional metric."""

    with get_db() as con:
        try:
            statements = con.extract_statements(sql_query)
        except Exception as e:
            logger.warning("Invalid SQL query %r: %s", sql_query, e)
            return [{"error": f"Invalid SQL query: {e}"}]

        # 1. Prevent empty strings or multi-statement injections (e.g., "SELECT 1; DROP TABLE users;")
        if len(statements) != 1:
            return [{"error": "Invalid Query: Exactly one SQL statement is allowed."}]

        # 2. Check the statement type explicitly
        # DuckDB StatementTypes include: SELECT, INSERT, ALTER, DROP, etc.
        statement = statements[0]
        if statement.type != duckdb.StatementType.SELECT:
            return [{"error": f"Security Alert: Disallowed operation type '{statement.type.name}'. Only SELECT queries are permitted."}]

        # 3. Safe to execute if it passes the checks
        try:
            result = con.sql(sql_query).df().to_dict(orient="records")
        except duckdb.Error as e:
            logger.warning("Query execution failed for %r: %s", sql_query, e)
            return [{"error": f"Query execution failed: {e}"}]

    return result
