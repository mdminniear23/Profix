CREATE TABLE IF NOT EXISTS games (
    app_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    install_path TEXT,
    manifest_path TEXT NOT NULL,
    prefix_path TEXT,
    last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
);