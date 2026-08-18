"""Service ticket and history retrieval helpers used by the service agent."""

from __future__ import annotations
import logging

from langchain_core.tools import tool
import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def create_service_tables():
    con = duckdb.connect("mock_data.db")
    tickets_df = pd.read_excel("data/AROL_Q2_synthetic_fleet_dataset.xlsx", sheet_name="MaintenanceTickets")

    con.sql("TRUNCATE TABLE tickets;")
    con.sql("CREATE TABLE IF NOT EXISTS tickets AS SELECT * FROM tickets_df")

    con.close()


@tool 
def get_service_tables_descriptors():
    """Return the table descriptors for the service tickets database."""
    con = duckdb.connect("mock_data.db")
    telemetry_descriptors = con.sql("DESCRIBE tickets").df().to_dict(orient="records")

    con.close()

    return {
        "tickets": telemetry_descriptors
    }

@tool
def query_service_tickets(sql_query) -> list[dict]:
    """Using an SQL statement, query service tickets."""

    logger.info("Querying service tickets with SQL: %s", sql_query)

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


# TODO: Implement a function to open a new service ticket for a given machine with a description. This function should insert a new record into the tickets table with the current timestamp, machine ID, status as 'open', and the provided description.
@tool
def open_new_ticket(machine_id: int, description: str) -> str:
	"""Open a new service ticket for a given machine with a description."""
     
	logger.info("Opening new service ticket for machine %d with description: %s", machine_id, description)
	con = duckdb.connect("mock_data.db")
	con.sql(f"""
		INSERT INTO tickets (date, machine_id, status, client_reported_description, technician_notes)
		VALUES (CURRENT_TIMESTAMP, {machine_id}, 'open', '{description}', '');
	""")
	con.close()

     
	return f"New service ticket opened for machine {machine_id} with description: '{description}'"