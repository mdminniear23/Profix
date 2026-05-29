import argparse

from profix.db import init_db, save_game
from profix.steam import find_steam_paths, find_app_manifests, parse_acf_manifest


def scan(args):
    print("Scanning Steam folders...")

    if not args.dry_run:
        init_db()

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

    # Loop

    for manifest in manifests:
        game = parse_acf_manifest(manifest)

        app_id = game.get("appid")
        name = game.get("name", "Unknown")
        install_path = None
        manifest_path = str(manifest)
        prefix_path = None

        if not args.dry_run:
            save_game(
                app_id=app_id,
                name=name,
                install_path=install_path,
                manifest_path=manifest_path,
                prefix_path=prefix_path,
            )

        if args.manifest_paths:
            print(f"- {name} ({app_id})")
            print(f"  Manifest: {manifest_path}")
        else:
            print(f"- {name} ({app_id})")

    if args.dry_run:
        print(f"\nDry run complete. Found {len(manifests)} Steam apps. Nothing saved.")
    else:
        print(f"\nSaved {len(manifests)} Steam apps to database.")

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
    scan_parser.add_argument(
        "--dry-run",
        "--dryrun",
        action="store_true",
        help="Scan without saving results to the database"
    )
    scan_parser.set_defaults(func=scan)

    db_parser = subparsers.add_parser("init-db", help="Initialize the Profix database")
    db_parser.set_defaults(func=init_database)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()