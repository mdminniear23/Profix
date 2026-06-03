import argparse

from profix.db import init_db, save_game
from profix.steam import find_steam_paths, find_app_manifests, parse_acf_manifest

def scan(args):
    """
    Scan for Steam installations and games, 
    optionally showing manifest paths and saving results to the database.
    """
    print("Scanning Steam folders...")

    # If not in dry run mode, initialize the database to ensure the schema is set up
    if not args.dry_run:
        init_db()

    # Find Steam installations based on configured paths in profix/config.py
    steam_paths = find_steam_paths()

    if not steam_paths:
        print("No Steam installations found.")
        return

    for path in steam_paths:
        print(f"Found Steam: {path}")

    # Find appmanifest files for installed games in each Steam installation
    manifests = find_app_manifests()

    if not manifests:
        print("No installed games found.")
        return

    print("\nInstalled Steam apps:")

    # Loop through each manifest and display information about the installed games
    for manifest in manifests:
        game = parse_acf_manifest(manifest)

        # Extract relevant information from the manifest, using defaults if keys are missing
        app_id = game.get("appid")
        name = game.get("name", "Unknown")
        install_path = None
        manifest_path = str(manifest)
        prefix_path = None

        # If the manifest contains an install directory, construct the full path to the installed game
        if not args.dry_run:
            save_game(
                app_id=app_id,
                name=name,
                install_path=install_path,
                manifest_path=manifest_path,
                prefix_path=prefix_path,
            )

        # Display the game information, optionally showing the manifest path if the --manifest-paths flag is set
        if args.manifest_paths:
            print(f"- {name} ({app_id})")
            print(f"  Manifest: {manifest_path}")
        else:
            print(f"- {name} ({app_id})")

    # After processing all manifests, display a summary of the results, indicating how many games were found and whether they were saved to the database (if not in dry run mode)
    if args.dry_run:
        print(f"\nDry run complete. Found {len(manifests)} Steam apps. Nothing saved.")
    else:
        print(f"\nSaved {len(manifests)} Steam apps to database.")

def init_database(args):
    """
    Initialize the database schema
    """
    init_db()
    print("Database initialized.")

# Main function to parse CLI arguments and dispatch commands
def main():
    parser = argparse.ArgumentParser(
        prog="profix",
        description="Proton prefix manager for Linux Steam installations."
    )

    # Define subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scan command to find Steam installations and games
    scan_parser = subparsers.add_parser("scan", help="Scan for Steam installations and games")
    # Optional argument to show manifest paths for each game
    scan_parser.add_argument(
        "--manifest-paths",
        action="store_true",
        help="Show the path to each Steam appmanifest file"
    )
    # Optional argument for dry run mode (scan without saving to database)
    scan_parser.add_argument(
        "--dry-run",
        "--dryrun",
        action="store_true",
        help="Scan without saving results to the database"
    )
    # Set the default function to call for the scan command
    scan_parser.set_defaults(func=scan)

    # Init-db command to set up the database schema
    db_parser = subparsers.add_parser("init-db", help="Initialize the Profix database")
    # Set the default function to call for the init-db command
    db_parser.set_defaults(func=init_database)

    # Parse arguments and call the appropriate function
    args = parser.parse_args()
    # Call the function associated with the chosen subcommand
    args.func(args)

if __name__ == "__main__":
    main()