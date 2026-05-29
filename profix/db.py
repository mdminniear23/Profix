import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".local/share/profix/profix.db"
SCHEMA_PATH = Path(__file__).parent / "sql" / "schema.sql"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    schema = SCHEMA_PATH.read_text()

    with get_connection() as conn:
        conn.executescript(schema)