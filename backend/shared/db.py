"""
Shared DB connection — Supabase Postgres, direct connection (PRD v5,
"Database connection method"). Every router imports get_db() from here
rather than opening its own connection.

ASSUMPTION FLAGGED FOR THE TEAM: the doc says "pick exactly one of asyncpg /
psycopg2 / SQLAlchemy Core, agreed once in team chat." This file uses
psycopg2 (sync, dict-cursor) because it's the smallest change from the
sqlite3 code this replaces. If the team agrees on asyncpg or SQLAlchemy
instead, this file needs to change for everyone, not just M2 — raise it
before merging.

supabase-py is NOT used here for table access, per the doc: it's reserved
for auth only. This connects straight to Postgres with the service-role
connection string.
"""
import os
import psycopg2
import psycopg2.extras
from pathlib import Path

DATABASE_URL = os.environ["DATABASE_URL"]  # Supabase connection string, service role
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "models" / "schema.sql"


def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    """Run once at startup: creates all tables if they don't exist yet."""
    conn = get_conn()
    with open(SCHEMA_PATH, "r") as f:
        with conn.cursor() as cur:
            cur.execute(f.read())
    conn.commit()
    conn.close()


def get_db():
    """FastAPI dependency — yields a connection, closes it after the request."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
