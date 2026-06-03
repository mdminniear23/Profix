# profix/steam.py
from profix.config import get_steam_paths

def find_steam_paths():
    """
    Find all Steam installation paths that exist on the system.
    Returns a list of Path objects pointing to the found Steam installations.
    """
    return [path for path in get_steam_paths() if path.exists()]

def find_app_manifests():
    """
    Search for Steam appmanifest .acf files in the steamapps directories of all found Steam installations.
    Returns a list of Path objects pointing to the found manifest files."""
    manifests = []

    for steam_path in find_steam_paths():
        steamapps_path = steam_path / "steamapps"

        if steamapps_path.exists():
            manifests.extend(steamapps_path.glob("appmanifest_*.acf"))

    return manifests

def parse_acf_manifest(manifest_path):
    """
    Parse a Steam appmanifest .acf file and return a dictionary of its contents.
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