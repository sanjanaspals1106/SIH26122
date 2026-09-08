import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add it to the project .env file."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def init_db() -> None:
    if not DATABASE_URL:
        return

    schema_path = BASE_DIR / "backend" / "models" / "schema.sql"
    schema = schema_path.read_text()

    with get_connection() as conn:
        conn.execute(schema)
        conn.commit()
