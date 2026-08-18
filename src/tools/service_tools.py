"""Service ticket and history retrieval helpers used by the service agent."""

from __future__ import annotations
import logging

from langchain_core.tools import tool
import duckdb
import pandas as pd

from src.tools.db import get_db

logger = logging.getLogger(__name__)


def create_service_tables():
    tickets_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="MaintenanceTickets")

    with get_db() as con:
        con.sql("CREATE OR REPLACE TABLE tickets AS SELECT * FROM tickets_df")


@tool
def get_service_tables_descriptors():
    """Return the table descriptors for the service tickets database."""
    with get_db() as con:
        telemetry_descriptors = con.sql("DESCRIBE tickets").df().to_dict(orient="records")

    return {
        "tickets": telemetry_descriptors
    }

@tool
def query_service_tickets(sql_query) -> list[dict]:
    """Using an SQL statement, query service tickets."""

    logger.info("Querying service tickets with SQL: %s", sql_query)

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


# TODO: Implement a function to open a new service ticket for a given machine with a description. This function should insert a new record into the tickets table with the current timestamp, machine ID, status as 'open', and the provided description.
@tool
def open_new_ticket(machine_id: int, description: str) -> str:
	"""Open a new service ticket for a given machine with a description."""
     
	logger.info("Opening new service ticket for machine %d with description: %s", machine_id, description)
	try:
		with get_db() as con:
			con.execute(
				"""
				INSERT INTO tickets (date, machine_id, status, client_reported_description, technician_notes)
				VALUES (CURRENT_TIMESTAMP, ?, 'open', ?, '');
				""",
				[machine_id, description],
			)
	except duckdb.Error as e:
		logger.warning("Failed to open service ticket for machine %d: %s", machine_id, e)
		return f"Error: could not open service ticket for machine {machine_id}: {e}"

	return f"New service ticket opened for machine {machine_id} with description: '{description}'"