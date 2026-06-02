"""
FactoryMind — data/seed_database.py

Purpose:
    Read each CSV from data/exports/ and bulk-insert its rows into the
    FactoryMind Azure SQL database via pyodbc.

Prerequisites:
    - generate_seed_data.py has already been run and data/exports/ is populated.
    - pyodbc is installed: pip install pyodbc
    - The ODBC Driver 18 for SQL Server is installed on your machine.
      Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

Connection:
    Azure SQL Server : factorymind-nickpeinitz-sql.database.windows.net
    Database         : FactoryMind  (update DB_NAME below if yours differs)
    Auth             : SQL login — set FM_SQL_USER and FM_SQL_PASSWORD as
                       environment variables so credentials are never hardcoded.

Run from project root:
    $env:FM_SQL_USER="your_username"          # PowerShell
    $env:FM_SQL_PASSWORD="your_password"
    python data/seed_database.py

Insert order matters because of FK constraints:
    Users → Equipment → Work_Orders → Parts_Usage
                      → Sensor_Events
                      → Query_Logs
"""

import os
import sys
import time
import logging
from pathlib import Path

import pandas as pd
import pyodbc


# =============================================================================
# LOGGING
# =============================================================================

# Logs go to both the console and a file so you have a record of every run.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("seed_database.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# =============================================================================
# CONNECTION CONFIGURATION
# =============================================================================

# Credentials are pulled from environment variables so they are never written
# into source code or committed to GitHub.

DB_SERVER   = "factorymind-nickpeinitz-sql.database.windows.net"
DB_NAME     = "FactoryMind"         # update if your database name differs
DB_USER     = os.environ.get("FM_SQL_USER")
DB_PASSWORD = os.environ.get("FM_SQL_PASSWORD")
DB_DRIVER   = "ODBC Driver 18 for SQL Server"

# Where generate_seed_data.py wrote the CSVs.
EXPORTS_DIR = Path(__file__).parent / "exports"

# Number of rows inserted per executemany() batch.
# 500–1000 is a sweet spot for Azure SQL — large enough to be fast,
# small enough to avoid timeouts on the free tier.
BATCH_SIZE = 500


# =============================================================================
# CONNECTION HELPER
# =============================================================================

def get_connection() -> pyodbc.Connection:
    """
    Build and return a pyodbc connection to Azure SQL.

    Raises SystemExit early if credentials are missing so the error message
    is clear rather than an obscure pyodbc exception.
    """

    if not DB_USER or not DB_PASSWORD:
        log.error(
            "Missing credentials. Set FM_SQL_USER and FM_SQL_PASSWORD "
            "as environment variables before running this script."
        )
        sys.exit(1)

    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    log.info(f"Connecting to {DB_SERVER} / {DB_NAME} ...")
    conn = pyodbc.connect(conn_str)
    conn.autocommit = False   # use explicit transactions for safety
    log.info("Connected.")
    return conn


# =============================================================================
# GENERIC BATCH INSERTER
# =============================================================================

def bulk_insert(
    conn: pyodbc.Connection,
    table: str,
    df: pd.DataFrame,
    batch_size: int = BATCH_SIZE,
) -> None:

    """
    Insert all rows from a DataFrame into the given SQL table using
    parameterised executemany() calls grouped into batches.

    Why executemany() instead of individual inserts:
    - Dramatically faster than one INSERT per row.
    - Parameterised queries prevent SQL injection.
    - Batching limits memory use and avoids Azure SQL timeout limits.

    Parameters:
        conn       : active pyodbc connection.
        table      : target SQL table name (must already exist in the schema).
        df         : DataFrame whose columns match the target table columns.
        batch_size : rows per executemany() call.
    """

    cols        = list(df.columns)
    col_list    = ", ".join(cols)
    placeholder = ", ".join(["?"] * len(cols))
    sql         = f"INSERT INTO {table} ({col_list}) VALUES ({placeholder})"

    # Replace pandas NA/NaN with None so pyodbc writes SQL NULL correctly.
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    cursor    = conn.cursor()
    total     = len(rows)
    inserted  = 0
    start     = time.time()

    try:
        for batch_start in range(0, total, batch_size):
            batch = rows[batch_start : batch_start + batch_size]
            cursor.executemany(sql, batch)
            inserted += len(batch)
            log.info(f"  {table}: {inserted}/{total} rows inserted ...")

        conn.commit()
        elapsed = time.time() - start
        log.info(f"   {table}: {total} rows committed in {elapsed:.1f}s")

    except pyodbc.Error as exc:
        conn.rollback()
        log.error(f"   {table}: insert failed — rolling back. Error: {exc}")
        raise   # re-raise so main() can report the failure and exit cleanly

    finally:
        cursor.close()


# =============================================================================
# CSV LOADER
# =============================================================================

def load_csv(filename: str) -> pd.DataFrame:
    """
    Load a CSV from data/exports/ into a DataFrame and do light cleaning.

    Cleaning steps:
    - Strip leading/trailing whitespace from column names (common CSV artifact).
    - Keep NaN values as-is — bulk_insert() will convert them to NULL.
    """
    path = EXPORTS_DIR / filename
    if not path.exists():
        log.error(f"CSV not found: {path}  — did you run generate_seed_data.py first?")
        sys.exit(1)

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    log.info(f"Loaded {filename}: {len(df)} rows, {len(df.columns)} columns")
    return df


# =============================================================================
# TABLE-SPECIFIC HELPERS
# =============================================================================

# Each helper loads its CSV, selects only the columns the SQL table expects,
# and calls bulk_insert(). Explicit column selection guards against accidental
# extra columns in the CSV causing INSERT failures.

def seed_users(conn: pyodbc.Connection) -> None:
    df = load_csv("users.csv")
    df = df[[
        "User_ID", "First_Name", "Last_Name",
        "Email", "Role", "Created_At", "Is_Active",
    ]]
    bulk_insert(conn, "Users", df)


def seed_equipment(conn: pyodbc.Connection) -> None:
    df = load_csv("equipment.csv")
    df = df[[
        "Equipment_ID", "Name", "Type", "Manufacturer",
        "Model_Number", "Serial_Number", "Location",
        "Install_Date", "Status", "BlobUrl",
    ]]
    bulk_insert(conn, "Equipment", df)


def seed_work_orders(conn: pyodbc.Connection) -> None:
    df = load_csv("work_orders.csv")
    df = df[[
        "WO_ID", "Equipment_ID", "Reported_By", "Assigned_To",
        "Failure_Type", "Priority", "Status", "Description",
        "Repair_Duration_Hrs", "Created_At", "Completed_At",
    ]]
    bulk_insert(conn, "Work_Orders", df)


def seed_parts_usage(conn: pyodbc.Connection) -> None:
    df = load_csv("parts_usage.csv")
    df = df[[
        "Part_ID", "WO_ID", "Part_Name", "Part_Number",
        "Quantity_Used", "Unit_Cost", "Total_Cost", "Recorded_At",
    ]]
    bulk_insert(conn, "Parts_Usage", df)


def seed_sensor_events(conn: pyodbc.Connection) -> None:
    df = load_csv("sensor_events.csv")
    df = df[[
        "Event_ID", "Equipment_ID", "Timestamp", "Temperature_C",
        "Vibration_Hz", "Torque_Nm", "Rotational_RPM",
        "Tool_Wear_Min", "Is_Anomaly", "Source",
    ]]
    bulk_insert(conn, "Sensor_Events", df)


def seed_query_logs(conn: pyodbc.Connection) -> None:
    df = load_csv("query_logs.csv")
    df = df[[
        "Log_ID", "User_ID", "Action", "Query_Text",
        "Execution_Ms", "Success", "Logged_At",
    ]]
    bulk_insert(conn, "Query_Logs", df)


# =============================================================================
# OPTIONAL: IDENTITY INSERT HELPER
# =============================================================================

def set_identity_insert(conn: pyodbc.Connection, table: str, on: bool) -> None:
    """
    Toggle IDENTITY_INSERT on or off for a given table.

    When to use:
    - The CSVs include explicit primary key values (e.g. User_ID, WO_ID).
    - Azure SQL will reject an INSERT that supplies a value for an IDENTITY
      column unless IDENTITY_INSERT is ON for that table.
    - Only one table can have IDENTITY_INSERT ON at a time.

    If you prefer to let Azure SQL auto-generate the primary keys and drop
    the ID columns from the CSVs, you can remove these calls entirely.
    """
    state = "ON" if on else "OFF"
    cursor = conn.cursor()
    cursor.execute(f"SET IDENTITY_INSERT {table} {state}")
    cursor.close()


# =============================================================================
# MAIN
# =============================================================================
def main() -> None:
    """
    Run the full seed pipeline in FK-safe insertion order.

    Order:
      1. Users          — no FK dependencies
      2. Equipment      — no FK dependencies
      3. Work_Orders    — FK → Equipment, FK → Users (x2)
      4. Parts_Usage    — FK → Work_Orders
      5. Sensor_Events  — FK → Equipment
      6. Query_Logs     — FK → Users
    """
    log.info("=" * 60)
    log.info("FactoryMind — Seed Database Loader v1.0")
    log.info("=" * 60)

    conn = get_connection()

    # Table → seeder function pairs in dependency order.
    # Each tuple also carries the table name for IDENTITY_INSERT toggling.
    steps = [
        ("Users",         seed_users),
        ("Equipment",     seed_equipment),
        ("Work_Orders",   seed_work_orders),
        ("Parts_Usage",   seed_parts_usage),
        ("Sensor_Events", seed_sensor_events),
        ("Query_Logs",    seed_query_logs),
    ]

    overall_start = time.time()
    failed = []

    for table_name, seeder in steps:
        log.info(f"--- Seeding {table_name} ---")
        try:
            # Enable IDENTITY_INSERT so explicit PK values from the CSV are
            # accepted. Remove these two calls if you want SQL to auto-generate
            # the primary keys instead.
            set_identity_insert(conn, table_name, on=True)
            seeder(conn)
            set_identity_insert(conn, table_name, on=False)
        except Exception as exc:
            log.error(f"Seeding {table_name} failed: {exc}")
            failed.append(table_name)
            # Attempt to turn IDENTITY_INSERT back off even after a failure
            # so the next table can still be attempted.
            try:
                set_identity_insert(conn, table_name, on=False)
            except Exception:
                pass

    conn.close()
    total_elapsed = time.time() - overall_start

    log.info("=" * 60)
    if failed:
        log.error(f"Seeding COMPLETED WITH ERRORS. Failed tables: {failed}")
        log.error("Check seed_database.log for details.")
        sys.exit(1)
    else:
        log.info(f" All tables seeded successfully in {total_elapsed:.1f}s")
        log.info("Next step: verify row counts in Azure SQL, then move to Phase 3.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()