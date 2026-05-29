import argparse

from profix.db import init_db
from profix.steam import find_steam_paths, find_app_manifests, parse_acf_manifest


def scan(args):
    print("Scanning Steam folders...")

    steam_paths = find_steam_paths()

    if not steam_paths:
        print("No Steam installations found.")
        return

    for path in steam_paths:
        print(f"Found Steam: {path}")

    manifests = find_app_manifests()

    if not manifests:
        print("No installed games found.")
        return

    print("\nInstalled Steam apps:")

    for manifest in manifests:
        game = parse_acf_manifest(manifest)

        if args.manifest_paths:
            print(
                f"- {game.get('name', 'Unknown')} ({game.get('appid', 'no appid')})\n"
                f"  Manifest: {manifest}"
            )
        else:
            print(f"- {game.get('name', 'Unknown')} ({game.get('appid', 'no appid')})")

def init_database(args):
    init_db()
    print("Database initialized.")

def main():
    parser = argparse.ArgumentParser(
        prog="profix",
        description="Proton prefix manager for Linux Steam installations."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan for Steam installations and games")
    scan_parser.add_argument(
        "--manifest-paths",
        action="store_true",
        help="Show the path to each Steam appmanifest file"
    )
    scan_parser.set_defaults(func=scan)

    db_parser = subparsers.add_parser("init-db", help="Initialize the Profix database")
    db_parser.set_defaults(func=init_database)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()