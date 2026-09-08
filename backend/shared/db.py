"""
Shared DB connection — Supabase Postgres, direct connection (PRD v5,
"Database connection method").

Provides both:
- `get_connection()`: Context manager / direct connection for backend modules.
- `get_db()`: FastAPI dependency yielding connection.
- `init_db()`: Initializer executing schema.sql.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "backend" / ".env")


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add it to the project .env file."
        )
    return url


def get_connection():
    """
    Returns a connection with dictionary-like row access.
    Prefers psycopg (v3) with dict_row, falls back to psycopg2 RealDictCursor.
    """
    url = get_database_url()
    try:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(url, row_factory=dict_row)
    except ImportError:
        import psycopg2
        import psycopg2.extras
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def get_db():
    """FastAPI dependency — yields a connection, closes it after the request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Run once at startup: creates all tables if they don't exist yet."""
    try:
        url = get_database_url()
    except RuntimeError:
        print("[db] DATABASE_URL not set; skipping init_db()")
        return

    schema_path = BASE_DIR / "backend" / "models" / "schema.sql"
    schema = schema_path.read_text()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()
