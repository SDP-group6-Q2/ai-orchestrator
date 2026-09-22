import pandas as pd
import os

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine

from src.db.db import get_credentials
from src.storage.supabase_client import list_bucket_filenames
from src.tools.manuals_tools import index_all_manuals

def create_database(dbname, user, password, host, port):
    # Connect to the default database
    conn = psycopg2.connect(
        dbname="postgres",
        user=user,
        password=password,
        host=host,
        port=port
    )

    conn.autocommit = True  # Required for CREATE DATABASE
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (dbname,)
            )
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {};").format(
                        sql.Identifier(dbname)
                    )
                )
                print(f"Database '{dbname}' created successfully.")
            else:
                print(f"Database '{dbname}' already exists. Skipping creation.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        conn.close()

def create_manuals_tables(user, password, host, port, dbname):
    """Enable pgvector and create the manuals RAG tables (separate from the flat xlsx-sheet tables)."""
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indexed_manuals (
                    company_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    serial_number TEXT NOT NULL,
                    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (company_id, machine_id)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manual_chunks (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(384) NOT NULL
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_manual_chunks_company_machine
                ON manual_chunks (company_id, machine_id);
            """)

            # A machine has exactly one manual (per the dataset spec), so the
            # Supabase Storage object key for its PDF is a plain attribute of the
            # machine itself, not a separate mapping table. Postgres never holds
            # the file bytes, only this reference -- see sync_manual_storage_paths.
            cursor.execute("""
                ALTER TABLE machines ADD COLUMN IF NOT EXISTS storage_path TEXT;
            """)
            print("pgvector extension and manuals RAG tables ready.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


_MANUAL_FILENAME_SUFFIX = "_manual_EN.pdf"


def sync_manual_storage_paths(user, password, host, port, dbname) -> None:
    """Set machines.storage_path from what's already in the Supabase "manuals"
    bucket, matching each object's filename back to its machine via
    serialnumber -- the same join index_all_manuals() uses for the RAG chunks.

    Idempotent: re-running just re-sets the same values, so it's safe to call
    every startup even though the bucket's contents rarely change."""
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    conn.autocommit = True
    try:
        filenames = list_bucket_filenames()
        with conn.cursor() as cursor:
            for filename in filenames:
                if not filename.endswith(_MANUAL_FILENAME_SUFFIX):
                    continue
                serial_number = filename[: -len(_MANUAL_FILENAME_SUFFIX)]

                cursor.execute(
                    "UPDATE machines SET storage_path = %s WHERE serialnumber = %s;",
                    (filename, serial_number),
                )
                if cursor.rowcount == 0:
                    print(f"storage_path: {filename} has no matching machine (serial_number={serial_number!r})")
        print(f"machines.storage_path synced from {len(filenames)} bucket object(s).")
    finally:
        conn.close()


def load_from_excel(engine):
    with pd.ExcelFile("data/AROL_Q2_synthetic_fleet_dataset.xlsx") as xls:
        sheet_names = xls.sheet_names
        for sheet_name in sheet_names:
            print("Creating table for sheet:", sheet_name)
            df = pd.read_excel(xls, sheet_name=sheet_name)
            table_name = sheet_name.lower()  # Convert to lowercase for table name
            df.columns = df.columns.str.lower()  # Avoid quoted mixed-case columns Postgres folds unquoted SQL away from
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f"Data from sheet '{sheet_name}' inserted into table '{table_name}'.")

def main():
    credentials = get_credentials()
    dbname = credentials["dbname"]

    host = credentials["host"]
    port = credentials["port"]
    user = credentials["user"]
    password = credentials["password"]

    create_database(dbname, user, password, host, port)
    create_manuals_tables(user, password, host, port, dbname)

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    )

    load_from_excel(engine)

    print("Syncing machines.storage_path from the Supabase manuals bucket...")
    sync_manual_storage_paths(user, password, host, port, dbname)

    print("Indexing manuals for the fleet (this may take a while)...")
    index_all_manuals()
    print("Manuals indexed.")


if "__main__" == "__main__":
    main()