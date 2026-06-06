import os
import argparse
import subprocess
from pathlib import Path

from profix.config import get_shared_profix_root, get_shared_profix_proton_path
from profix.db import init_db, save_game
from profix.steam import (
    find_steam_paths,
    find_app_manifests,
    parse_acf_manifest,
    resolve_proton_path,
)

def _is_prefix_initialized(root: Path) -> bool:
    """
    Checks if a given directory looks like an initialized Proton prefix by checking for the presence of system.reg and drive_c.
    """
    return (root / "pfx" / "system.reg").exists() and (root / "pfx" / "drive_c").exists()

def init_shared_profix(args):
    """
    Initialize the shared profix prefix by running 'proton run wineboot -u' with the appropriate environment variable set to create the prefix layout. 
    If the prefix already appears to be initialized and --force is not used, it will skip initialization to avoid overwriting existing data. 
    """
    shared_root = get_shared_profix_root()
    shared_root.mkdir(parents=True, exist_ok=True)

    if _is_prefix_initialized(shared_root) and not args.force:
        print(f"Shared profix already initialized: {shared_root / 'pfx'}")
        return

    proton_path = resolve_proton_path(args.proton_path or get_shared_profix_proton_path())

    steam_paths = find_steam_paths()
    if not steam_paths:
        raise RuntimeError("No Steam installations found for STEAM_COMPAT_CLIENT_INSTALL_PATH.")
    client_install_path = steam_paths[0]

    env = os.environ.copy()
    env["STEAM_COMPAT_DATA_PATH"] = str(shared_root)
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(client_install_path)
    env["STEAM_COMPAT_TOOL_PATHS"] = str(proton_path.parent)  # helpful for Proton runtime lookups

    subprocess.run(
        [str(proton_path), "run", "wineboot", "-u"],
        check=True,
        env=env,
    )

    if not _is_prefix_initialized(shared_root):
        raise RuntimeError("Prefix init command completed, but pfx layout was not created.")

    print(f"Initialized shared profix at: {shared_root / 'pfx'}")

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
    discovered_steam_paths = find_steam_paths()

    if not discovered_steam_paths:
        print("No Steam installations found.")
        return

    for path in discovered_steam_paths:
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
        installdir = game.get("installdir")
        if installdir:
            install_path = str((manifest.parent / "common" / installdir).resolve())

        # Display the game information, optionally showing the manifest path if the --manifest-paths flag is set
        if args.manifest_paths:
            print(f"- {name} ({app_id})")
            print(f"  Manifest: {manifest_path}")
        else:
            print(f"- {name} ({app_id})")

        # After install_path resolution, save the game to the database if not in dry run mode
        if not args.dry_run:
            save_game(
                app_id=app_id,
                name=name,
                install_path=install_path,
                manifest_path=manifest_path,
                prefix_path=None,
            )

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
    # Init-shared-profix command to initialize the shared Proton prefix
    init_shared_parser = subparsers.add_parser(
        "init-shared-profix",
        help="Initialize a single shared Proton prefix for profix"
    )
    # Optional argument to specify a custom Proton executable path for initializing the shared prefix
    init_shared_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run initialization even if the shared prefix already exists"
    )
    init_shared_parser.add_argument(
        "--proton-path",
        type=Path,
        help="Path to the Proton executable to use for initializing the shared prefix"
    )
    # Set the default function to call for the init-shared-profix command
    init_shared_parser.set_defaults(func=init_shared_profix)

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