"""Service ticket and history retrieval helpers used by the service agent."""

from __future__ import annotations
import logging

from langchain_core.tools import tool
import duckdb

logger = logging.getLogger(__name__)

TICKETS_DDL = """
    CREATE TABLE  IF NOT EXISTS tickets (
        date TIMESTAMP,
        machine_id INTEGER,
		status enum('open', 'closed', 'in_progress'),
        client_reported_description VARCHAR(255),
		technician_notes VARCHAR(255)
    );
    COMMENT ON COLUMN tickets.date IS 'The date and time when the ticket was created';
    COMMENT ON COLUMN tickets.machine_id IS 'The ID of the machine associated with the ticket';
    COMMENT ON COLUMN tickets.status IS 'The current status of the ticket';
    COMMENT ON COLUMN tickets.client_reported_description IS 'A description of the issue reported by the client';
    COMMENT ON COLUMN tickets.technician_notes IS 'Notes from the technician';
"""

MOCK_TICKETS = """
    TRUNCATE TABLE tickets;
    INSERT INTO tickets (date, machine_id, status, client_reported_description, technician_notes) VALUES
		('2024-06-01 10:00:00', 1, 'open', 'Machine stopped unexpectedly.', 'Investigating.'),
		('2024-06-02 11:30:00', 2, 'closed', 'Error code E204 displayed.', 'Replaced faulty sensor.'),
		('2024-06-03 09:15:00', 1, 'in_progress', 'Unusual vibration detected.', 'Scheduled maintenance visit.'),
		('2024-06-04 14:45:00', 3, 'open', 'Machine not starting.', 'Checking power supply.'),
		('2024-06-05 08:20:00', 2, 'closed', 'Routine maintenance completed.', 'All systems normal.');
"""

con = duckdb.connect("mock_data.db")
con.sql(TICKETS_DDL)
con.sql(MOCK_TICKETS)

@tool 
def get_service_tables_descriptors():
    """Return the table descriptors for the service tickets database."""
    return {
        "tickets": TICKETS_DDL
    }

@tool
def query_service_tickets(sql_query) -> list[dict]:
    """Using an SQL statement, query service tickets."""

    logger.info("Querying service tickets with SQL: %s", sql_query)

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

@tool
def open_new_ticket(machine_id: int, description: str) -> str:
	"""Open a new service ticket for a given machine with a description."""
	logger.info("Opening new service ticket for machine %d with description: %s", machine_id, description)
	con.sql(f"""
		INSERT INTO tickets (date, machine_id, status, client_reported_description, technician_notes)
		VALUES (CURRENT_TIMESTAMP, {machine_id}, 'open', '{description}', '');
	""")
	return f"New service ticket opened for machine {machine_id} with description: '{description}'"