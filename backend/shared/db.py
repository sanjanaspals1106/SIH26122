"""
Shared DB connection — Supabase Postgres, direct connection (PRD v5,
"Database connection method"). Every router imports get_db() or
get_connection() from here rather than opening its own connection.

The project uses psycopg2 for synchronous PostgreSQL access with a
dict-style cursor.

supabase-py is NOT used here for table access, per the doc: it's reserved
for auth only. This connects straight to Postgres with the service-role
connection string.
"""

import os
from pathlib import Path

import psycopg2
import psycopg2.extras


DATABASE_URL = os.getenv("DATABASE_URL")

SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "models" / "schema.sql"
)


def get_connection():
    """
    Create and return a PostgreSQL connection using the Supabase
    DATABASE_URL.

    Rows are returned as dictionaries.
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add it to the project .env file."
        )

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_conn():
    """
    Backwards-compatible alias for get_connection().
    """
    return get_connection()


def get_db():
    """
    FastAPI dependency — yields a database connection and closes it
    after the request.
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Run once at application startup.

    Creates all database tables defined in schema.sql if they do not
    already exist.
    """
    if not DATABASE_URL:
        print(
            "Warning: DATABASE_URL is not configured; "
            "database initialization skipped."
        )
        return

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            with open(SCHEMA_PATH, "r") as f:
                cur.execute(f.read())

        conn.commit()

    finally:
        conn.close()
