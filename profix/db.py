import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".local/share/profix/profix.db"
SQL_DIR = Path(__file__).parent / "sql"


def read_sql(filename):
    return (SQL_DIR / filename).read_text(encoding="utf-8")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.executescript(read_sql("schema.sql"))


def save_game(app_id, name, install_path, manifest_path, prefix_path):
    with get_connection() as conn:
        conn.execute(
            read_sql("save_game.sql"),
            (app_id, name, install_path, manifest_path, prefix_path),
        )


def get_games():
    with get_connection() as conn:
        return conn.execute(read_sql("get_games.sql")).fetchall()