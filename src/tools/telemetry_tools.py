"""Telemetry retrieval helpers used by the IoT agent."""

from __future__ import annotations

from langchain_core.tools import tool
import duckdb

TELEMETRY_READINGS_DDL = """
    CREATE TABLE telemetry_readings (
        machine_id VARCHAR,
        sensor1_reading DOUBLE,
        sensor2_reading DOUBLE,
        timestamp TIMESTAMP
    );
"""

MOCK_READINGS = """
    INSERT INTO telemetry_readings (machine_id, sensor1_reading, sensor2_reading, timestamp) VALUES
        ('machine_1', 10.5, 20.1, '2024-06-01 10:00:00'),
        ('machine_1', 11.0, 19.8, '2024-06-01 10:05:00'),
        ('machine_2', 9.8, 21.0, '2024-06-01 10:00:00'),
        ('machine_2', 10.2, 20.5, '2024-06-01 10:05:00');
"""

con = duckdb.connect("mock_readings.db")
con.sql(TELEMETRY_READINGS_DDL)
con.sql(MOCK_READINGS)

@tool
def query_telemetry_readings(sql_query) -> list[dict]:
    f"""Using an SQL statement, query telemetry readings for a given machine and optional metric. The table description is as follows: {TELEMETRY_READINGS_DDL}"""

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
