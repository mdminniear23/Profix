import os
import argparse
import subprocess
from pathlib import Path

from profix.config import (
    get_shared_profix_root,
    get_shared_profix_proton_path,
    get_shared_profix_games_dir,
    get_shared_profix_link_name_template,
    get_shared_profix_auto_init,
)
from profix.db import init_db, save_game, get_games_for_sync, set_game_prefix_path
from profix.profix_sync import (
    ensure_shared_games_dir,
    render_link_name,
    reconcile_game_layout,
    remove_game_dir_entry,
)
from profix.steam import (
    find_steam_paths,
    find_app_manifests,
    parse_acf_manifest,
    resolve_proton_path,
    is_likely_game,
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


def sync_shared_profix(args):
    """
    Sync symlinks for all scanned Steam games into the shared profix games directory.
    """
    shared_root = get_shared_profix_root()
    pfx_path = shared_root / "pfx"

    if not _is_prefix_initialized(shared_root):
        if get_shared_profix_auto_init() and not args.dry_run:
            init_shared_profix(argparse.Namespace(force=False, proton_path=None))
        else:
            raise RuntimeError(
                "Shared profix is not initialized. Run 'profix init-shared-profix' first."
            )

    games_dir_rel = get_shared_profix_games_dir()
    link_template = get_shared_profix_link_name_template()
    games_dir = ensure_shared_games_dir(shared_root, games_dir_rel)

    games = get_games_for_sync()
    if not games:
        print("No games found in database. Run 'profix scan' first.")
        return

    counts = {"created": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    filtered_non_games = 0
    removed_non_games = 0
    remove_failed = 0
    non_game_dirs_to_remove = []

    print(f"Syncing {len(games)} games into: {games_dir}")

    for app_id, name, install_path, manifest_path in games:
        link_name = render_link_name(link_template, name or "Unknown", app_id or "unknown")
        game_dir = games_dir / link_name

        if not args.include_non_games and not is_likely_game(app_id, name):
            filtered_non_games += 1
            if args.remove_non_games:
                non_game_dirs_to_remove.append((name, app_id, game_dir))
            continue

        if not install_path or not manifest_path:
            counts["skipped"] += 1
            print(f"- skipped {name} ({app_id}): missing install_path or manifest_path")
            continue

        manifest_parent = Path(manifest_path).parent
        pfx_target = manifest_parent / "compatdata" / str(app_id) / "pfx"

        result = reconcile_game_layout(
            game_dir=game_dir,
            common_target=Path(install_path),
            pfx_target=pfx_target,
            force=args.force,
            dry_run=args.dry_run,
        )
        counts[result] += 1

        if result == "failed":
            print(f"- failed  {name} ({app_id}): path conflict at {game_dir}")
        elif result == "skipped":
            print(f"- skipped {name} ({app_id})")
        elif result == "created":
            if args.dry_run:
                print(f"- would-link {name} ({app_id}) with common/ and pfx/")
            else:
                print(f"- linked  {name} ({app_id}) with common/ and pfx/")

        if result in {"created", "unchanged"} and not args.dry_run:
            set_game_prefix_path(app_id, str(game_dir / "pfx"))

    if args.remove_non_games:
        for name, app_id, game_dir in non_game_dirs_to_remove:
            remove_result = remove_game_dir_entry(game_dir=game_dir, dry_run=args.dry_run)
            if remove_result == "removed":
                removed_non_games += 1
                if args.dry_run:
                    print(f"- would-remove non-game entry {name} ({app_id})")
                else:
                    print(f"- removed non-game entry {name} ({app_id})")
            elif remove_result == "failed":
                remove_failed += 1
                print(f"- failed to remove non-game entry {name} ({app_id}) at {game_dir}")

    print(
        "\nSync complete: "
        f"created={counts['created']} "
        f"unchanged={counts['unchanged']} "
        f"skipped={counts['skipped']} "
        f"failed={counts['failed']} "
        f"filtered_non_games={filtered_non_games} "
        f"removed_non_games={removed_non_games} "
        f"remove_failed={remove_failed}"
    )

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
    filtered_non_games = 0
    saved_count = 0

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

        if not args.include_non_games and not is_likely_game(app_id, name, installdir):
            filtered_non_games += 1
            continue

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
            saved_count += 1

    # After processing all manifests, display a summary of the results, indicating how many games were found and whether they were saved to the database (if not in dry run mode)
    if args.dry_run:
        print(
            f"\nDry run complete. Found {len(manifests)} Steam apps, "
            f"filtered {filtered_non_games} non-games. Nothing saved."
        )
    else:
        print(
            f"\nSaved {saved_count} Steam apps to database "
            f"(filtered {filtered_non_games} non-games)."
        )

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
    scan_parser.add_argument(
        "--include-non-games",
        action="store_true",
        help="Include compatibility tools/runtimes and other non-game apps"
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

    # Sync-shared-profix command to create/update game directory symlinks in the shared prefix
    sync_parser = subparsers.add_parser(
        "sync-shared-profix",
        help="Sync all scanned games into the shared profix as symlinks"
    )
    sync_parser.add_argument(
        "--dry-run",
        "--dryrun",
        action="store_true",
        help="Show what would be linked without making filesystem changes"
    )
    sync_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace incorrect existing links where possible"
    )
    sync_parser.add_argument(
        "--include-non-games",
        action="store_true",
        help="Also sync non-game apps such as compatibility tools"
    )
    sync_parser.add_argument(
        "--remove-non-games",
        action="store_true",
        help="Remove existing synced entries for filtered non-game apps"
    )
    sync_parser.set_defaults(func=sync_shared_profix)

    # Parse arguments and call the appropriate function
    args = parser.parse_args()
    # Call the function associated with the chosen subcommand
    args.func(args)

if __name__ == "__main__":
    main()