SELECT
    app_id,
    name,
    install_path,
    manifest_path,
    prefix_path,
    last_seen_at
FROM games
ORDER BY name;