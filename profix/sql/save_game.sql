INSERT INTO games (
    app_id,
    name,
    install_path,
    manifest_path,
    prefix_path,
    last_seen_at
)
VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(app_id) DO UPDATE SET
    name = excluded.name,
    install_path = excluded.install_path,
    manifest_path = excluded.manifest_path,
    prefix_path = excluded.prefix_path,
    last_seen_at = CURRENT_TIMESTAMP;