from pathlib import Path


def _normalize_windows_path(windows_path):
    """
    Convert a Windows-style C: path into a safe path relative to drive_c.
    """
    normalized = windows_path.replace("\\", "/")

    if not normalized.lower().startswith("c:/"):
        raise ValueError("Windows paths must start with C:/")

    parts = [part for part in normalized[3:].split("/") if part]

    if any(part == ".." for part in parts):
        raise ValueError("Windows paths must stay inside drive_c")

    return Path(*parts)


def _ensure_symlink(link_path, target_path):
    """
    Create a symlink if it does not exist, allowing idempotent re-runs.
    """
    if link_path.is_symlink():
        current_target = link_path.readlink()
        expected_target = target_path

        if not expected_target.is_absolute():
            expected_target = link_path.parent / expected_target

        if link_path.resolve() == expected_target.resolve():
            return False
        raise FileExistsError(
            f"Symlink {link_path} points to {current_target}, expected {expected_target}"
        )

    if link_path.exists():
        raise FileExistsError(f"{link_path} already exists")

    link_path.symlink_to(target_path)
    return True


def parse_link_spec(link_spec):
    """
    Parse a link spec in the form WINDOWS_PATH=TARGET_PATH.
    """
    windows_path, separator, target_path = link_spec.partition("=")
    windows_path = windows_path.strip()
    target_path = target_path.strip()

    if not separator or not windows_path or not target_path:
        raise ValueError("Link specs must use the format WINDOWS_PATH=TARGET_PATH")

    return windows_path, Path(target_path).expanduser()


def create_proton_prefix(prefix_path, link_specs):
    """
    Create a minimal Proton/Wine-style prefix and populate Windows-path symlinks.
    """
    prefix_path = Path(prefix_path).expanduser()
    drive_c_path = prefix_path / "drive_c"
    dosdevices_path = prefix_path / "dosdevices"

    drive_c_path.mkdir(parents=True, exist_ok=True)
    dosdevices_path.mkdir(exist_ok=True)

    _ensure_symlink(dosdevices_path / "c:", Path("../drive_c"))
    _ensure_symlink(dosdevices_path / "z:", Path("/"))

    created_links = []

    for link_spec in link_specs:
        windows_path, target_path = parse_link_spec(link_spec)

        if not target_path.exists():
            raise FileNotFoundError(f"Target path does not exist: {target_path}")

        link_path = drive_c_path / _normalize_windows_path(windows_path)
        link_path.parent.mkdir(parents=True, exist_ok=True)

        resolved_target_path = target_path.resolve()
        if _ensure_symlink(link_path, resolved_target_path):
            created_links.append((windows_path, link_path, resolved_target_path))

    return created_links
