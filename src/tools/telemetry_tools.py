"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations

from langchain_core.tools import tool
import duckdb

TELEMETRY_READINGS_DDL = """
    CREATE TABLE IF NOT EXISTS telemetry_readings (
        machine_id INTEGER,
        sensor1_reading DOUBLE,
        sensor2_reading DOUBLE,
        timestamp TIMESTAMP
    );
    COMMENT ON COLUMN telemetry_readings.machine_id IS 'The ID of the machine associated with the telemetry reading';
    COMMENT ON COLUMN telemetry_readings.sensor1_reading IS 'The reading from sensor 1';
    COMMENT ON COLUMN telemetry_readings.sensor2_reading IS 'The reading from sensor 2';
    COMMENT ON COLUMN telemetry_readings.timestamp IS 'The date and time when the reading was recorded';
"""

MOCK_READINGS = """
    TRUNCATE TABLE telemetry_readings;
    INSERT INTO telemetry_readings (machine_id, sensor1_reading, sensor2_reading, timestamp) VALUES
        (1, 10.5, 20.1, '2024-06-01 10:00:00'),
        (1, 11.0, 19.8, '2024-06-01 10:05:00'),
        (2, 9.8, 21.0, '2024-06-01 10:00:00'),
        (2, 10.2, 20.5, '2024-06-01 10:05:00');
"""

con = duckdb.connect("mock_data.db")
con.sql(TELEMETRY_READINGS_DDL)
con.sql(MOCK_READINGS)

@tool
def get_telemetry_tables_descriptors():
    """Return the table descriptors for the telemetry readings database."""
    return {
        "telemetry_readings": TELEMETRY_READINGS_DDL
    }

@tool
def query_telemetry_readings(sql_query) -> list[dict]:
    """Using an SQL statement, query telemetry readings for a given machine and optional metric."""

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

    # 3. Safe to execute if it passes the checks
    return con.sql(sql_query).df().to_dict(orient="records")
