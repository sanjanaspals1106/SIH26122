from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "sih26122.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    schema_path = BASE_DIR / "backend" / "models" / "schema.sql"

    with get_connection() as conn:
        conn.executescript(schema_path.read_text())
        conn.commit()
