from pathlib import Path


def _sanitize_link_name(name: str) -> str:
    """Sanitize game names for safe use as symlink path segments."""
    cleaned = name.strip()
    for ch in ["/", "\\", ":", "\0"]:
        cleaned = cleaned.replace(ch, "_")
    return cleaned or "Unknown"


def render_link_name(template: str, name: str, app_id: str) -> str:
    """Render link name from template, falling back to a safe default."""
    safe_name = _sanitize_link_name(name)
    safe_app_id = str(app_id or "unknown")

    try:
        rendered = template.format(name=safe_name, app_id=safe_app_id)
    except Exception:
        rendered = f"{safe_name} [{safe_app_id}]"

    return _sanitize_link_name(rendered)


def get_games_dir(shared_root: Path, games_dir_rel: str) -> Path:
    """Return the absolute games directory inside the shared pfx."""
    return shared_root / "pfx" / Path(games_dir_rel)


def ensure_shared_games_dir(shared_root: Path, games_dir_rel: str) -> Path:
    """Ensure the shared games directory exists and return it."""
    games_dir = get_games_dir(shared_root, games_dir_rel)
    games_dir.mkdir(parents=True, exist_ok=True)
    return games_dir


def _reconcile_link(link_path: Path, target_path: Path, force: bool, dry_run: bool) -> str:
    """Reconcile one symlink target path."""
    if link_path.is_symlink():
        try:
            if link_path.resolve() == target_path.resolve():
                return "unchanged"
        except FileNotFoundError:
            try:
                if Path(link_path.readlink()) == target_path:
                    return "unchanged"
            except OSError:
                pass

        if not force:
            return "skipped"
        if not dry_run:
            link_path.unlink()

    elif link_path.exists():
        if not force:
            return "skipped"
        if not dry_run:
            if link_path.is_dir():
                return "failed"
            link_path.unlink()

    if not dry_run:
        link_path.symlink_to(target_path)
    return "created"


def reconcile_game_layout(
    game_dir: Path,
    common_target: Path,
    pfx_target: Path,
    force: bool,
    dry_run: bool,
) -> str:
    """
    Ensure game_dir has common/ and pfx/ symlinks.

    Returns one of: created, unchanged, skipped, failed.
    """
    if not common_target.exists() or not common_target.is_dir():
        return "skipped"

    if game_dir.is_symlink() or (game_dir.exists() and not game_dir.is_dir()):
        if not force:
            return "skipped"
        if not dry_run:
            if game_dir.is_symlink() or game_dir.is_file():
                game_dir.unlink()
            else:
                return "failed"

    if not dry_run:
        game_dir.mkdir(parents=True, exist_ok=True)

    common_result = _reconcile_link(game_dir / "common", common_target, force, dry_run)
    if common_result == "failed":
        return "failed"

    pfx_result = _reconcile_link(game_dir / "pfx", pfx_target, force, dry_run)
    if pfx_result == "failed":
        return "failed"

    if common_result == "unchanged" and pfx_result == "unchanged":
        return "unchanged"
    if "skipped" in {common_result, pfx_result}:
        return "skipped"
    return "created"
