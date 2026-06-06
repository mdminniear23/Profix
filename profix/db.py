import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".local/share/profix/profix.db"
SQL_DIR = Path(__file__).parent / "sql"

def read_sql(filename):
    """
    Read the contents of an SQL file from the sql directory.
    """
    return (SQL_DIR / filename).read_text(encoding="utf-8")

def get_connection():
    """
    Get a connection to the SQLite database, ensuring that the parent directory exists.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """
    Initialize the database schema by executing the SQL script that creates the necessary tables and indexes.
    """
    with get_connection() as conn:
        conn.executescript(read_sql("schema.sql"))

def save_game(app_id, name, install_path, manifest_path, prefix_path):
    """
    Save a game to the database.
    """
    with get_connection() as conn:
        conn.execute(
            read_sql("save_game.sql"),
            (app_id, name, install_path, manifest_path, prefix_path),
        )

def get_games():
    """
    Retrieve all games from the database.
    """
    with get_connection() as conn:
        return conn.execute(read_sql("get_games.sql")).fetchall()

def get_games_for_sync():
    """
    Retrieve game rows needed for shared profix symlink sync.
    """
    query = """
    SELECT app_id, name, install_path, manifest_path
    FROM games
    ORDER BY name
    """
    with get_connection() as conn:
        return conn.execute(query).fetchall()

def set_game_prefix_path(app_id, prefix_path):
    """
    Update the prefix path for a specific game.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE games SET prefix_path = ?, last_seen_at = CURRENT_TIMESTAMP WHERE app_id = ?",
            (prefix_path, app_id),
        )