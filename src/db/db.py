import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_credentials():
    if not all([os.getenv("ASSISTANT_DB"), os.getenv("POSTGRES_USER"), os.getenv("POSTGRES_PASSWORD"), os.getenv("POSTGRES_HOST"), os.getenv("POSTGRES_PORT")]):
        raise ValueError("Database credentials are not fully set in environment variables.")

    """Return the database credentials from environment variables."""
    return {
        "dbname": os.getenv("ASSISTANT_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
    }

def get_db() -> psycopg2.extensions.connection:
    """Return a new connection to the assistant Postgres database."""

    credentials = get_credentials()

    return psycopg2.connect(
        dbname=credentials["dbname"],
        user=credentials["user"],
        password=credentials["password"],
        host=credentials["host"],
        port=credentials["port"],
        cursor_factory=RealDictCursor,
    )
