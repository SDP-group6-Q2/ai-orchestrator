"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations

from langchain_core.tools import tool
import duckdb
import pandas as pd


def create_telemetry_tables():
    con = duckdb.connect("mock_data.db")
    telemetry_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="TelemetrySnapshots")
    alarms_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="Alarms")

    duckdb.sql("TRUNCATE TABLE telemetry_readings;")
    duckdb.sql("TRUNCATE TABLE alarms;")

    duckdb.sql("CREATE TABLE IF NOT EXISTS telemetry_readings AS SELECT * FROM telemetry_df")
    duckdb.sql("CREATE TABLE IF NOT EXISTS alarms AS SELECT * FROM alarms_df")

    con.close()

@tool
def get_telemetry_tables_descriptors():
    """Return the table descriptors for the telemetry readings database."""
    con = duckdb.connect("mock_data.db")
    telemetry_descriptors = con.sql("DESCRIBE telemetry_readings").df().to_dict(orient="records")
    alarms_descriptors = con.sql("DESCRIBE alarms").df().to_dict(orient="records")

    con.close()

    return {
        "telemetry_readings": telemetry_descriptors,
        "alarms": alarms_descriptors
    }

@tool
def query_telemetry_readings(sql_query) -> list[dict]:
    """Using an SQL statement, query telemetry readings for a given machine and optional metric."""

    con = duckdb.connect("mock_data.db")

    try:
        statements = con.extract_statements(sql_query)
    except Exception as e:
        raise ValueError(f"Invalid SQL query: {e}")

    # 1. Prevent empty strings or multi-statement injections (e.g., "SELECT 1; DROP TABLE users;")
    if len(statements) != 1:
        raise ValueError("Invalid Query: Exactly one SQL statement is allowed.")
    
    # 2. Check the statement type explicitly
    # DuckDB StatementTypes include: SELECT, INSERT, ALTER, DROP, etc.
    statement = statements[0]
    if statement.type != duckdb.StatementType.SELECT:
        raise ValueError(f"Security Alert: Disallowed operation type '{statement.type.name}'. Only SELECT queries are permitted.")

    result = con.sql(sql_query).df().to_dict(orient="records")

    con.close()

    # 3. Safe to execute if it passes the checks
    return result
