import pandas as pd
import os

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine

from src.db.db import get_credentials

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

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    )

    load_from_excel(engine)


if "__main__" == "__main__":
    main()