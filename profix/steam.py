# profix/steam.py
from pathlib import Path
from profix.config import get_steam_paths


def find_steam_paths():
    return [path for path in get_steam_paths() if path.exists()]


def find_app_manifests():
    manifests = []

    for steam_path in find_steam_paths():
        steamapps_path = steam_path / "steamapps"

        if steamapps_path.exists():
            manifests.extend(steamapps_path.glob("appmanifest_*.acf"))

    return manifests

def parse_acf_manifest(manifest_path):
    game = {}

    with manifest_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line.startswith('"'):
                continue

            parts = line.split('"')

            if len(parts) >= 4:
                key = parts[1]
                value = parts[3]
                game[key] = value

    return game