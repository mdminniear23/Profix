# profix/steam.py
from pathlib import Path
from profix.config import get_steam_paths, get_non_game_appids, get_non_game_name_patterns

def find_steam_paths():
    """
    Find all Steam installation paths that exist on the system.
    Returns a list of Path objects pointing to the found Steam installations.
    """
    return [path for path in get_steam_paths() if path.exists()]

def find_app_manifests():
    """
    Search for Steam appmanifest .acf files in the steamapps directories of all found Steam installations.
    Returns a list of Path objects pointing to the found manifest files.
    """
    manifests = []

    for steam_path in find_steam_paths():
        steamapps_path = steam_path / "steamapps"

        if steamapps_path.exists():
            manifests.extend(steamapps_path.glob("appmanifest_*.acf"))

    return manifests

def parse_acf_manifest(manifest_path):
    """
    Parse a Steam appmanifest .acf file and return a dictionary of its contents.

    Args:
        manifest_path (Path): The path to the appmanifest .acf file.

    Returns:
        dict: A dictionary containing the key-value pairs from the manifest file.
    Note: This is a very basic parser that only handles simple key-value pairs and does not support nested structures or arrays. It is sufficient for extracting the appid and name of the game, but may not work correctly for more complex manifest files.
    """
    manifest = {}

    with manifest_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line.startswith('"'):
                continue

            parts = line.split('"')

            if len(parts) >= 4:
                key = parts[1]
                value = parts[3]
                manifest[key] = value

    return manifest

def find_proton_candidates() -> list[Path]:
    """
    Search for Proton executables in the steamapps/common directories of all found Steam installations.

    Returns:
        list[Path]: A list of Path objects pointing to the found Proton executables, sorted with Proton Experimental first and then by lexical order of the parent directory name.
    """
    candidates: list[Path] = []

    for steam_root in find_steam_paths():
        common_dir = steam_root / "steamapps" / "common"
        if not common_dir.exists():
            continue

        for entry in common_dir.iterdir():
            proton_bin = entry / "proton"
            if entry.is_dir() and proton_bin.is_file():
                candidates.append(proton_bin)

    # Prefer Proton Experimental, then lexical newest
    candidates.sort(key=lambda p: ("experimental" not in p.parent.name.lower(), p.parent.name.lower()))
    return candidates


def resolve_proton_path(configured: Path | None) -> Path:
    """
    Resolve the Proton executable path.

    Args:
        configured (Path | None): The configured Proton path from the configuration.

    Returns:
        Path: The resolved Proton executable path.

    Raises:
        FileNotFoundError: If the configured path does not exist or no Proton executable is found.
    """
    if configured:
        if configured.exists():
            return configured
        raise FileNotFoundError(f"Configured proton_path does not exist: {configured}")

    candidates = find_proton_candidates()
    if not candidates:
        raise FileNotFoundError(
            "No Proton executable found. Set shared_profix.proton_path in config."
        )
    return candidates[0]


def is_likely_game(app_id: str | None, name: str | None, installdir: str | None = None) -> bool:
    """
    Determine whether an app should be treated as a game.

    Steam appmanifest files do not reliably include a strict type field, so this
    uses configurable deny-lists for known non-game app IDs and name patterns.
    """
    normalized_app_id = str(app_id or "").strip()
    if normalized_app_id and normalized_app_id in get_non_game_appids():
        return False

    text_fields = " ".join(
        part for part in [name or "", installdir or ""] if part
    ).lower()

    for pattern in get_non_game_name_patterns():
        if pattern and pattern in text_fields:
            return False

    return True