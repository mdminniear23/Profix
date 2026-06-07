import argparse
import subprocess
from pathlib import Path

from profix.services.config import (
    get_shared_profix_root,
    get_shared_profix_proton_path,
    get_shared_profix_games_dir,
    get_shared_profix_link_name_template,
    get_shared_profix_auto_init,
    get_vortex_installer_url,
)
from profix.services.db import init_db, save_game, get_games_for_sync, set_game_prefix_path
from profix.services.profix_sync import (
    ensure_shared_games_dir,
    render_link_name,
    reconcile_game_layout,
    remove_game_dir_entry,
)
from profix.services.shared_profix_runtime import (
    is_prefix_initialized,
    build_proton_env,
    ensure_vortex_shortcut_script,
)
from profix.services.vortex import (
    installer_filename_from_url,
    get_vortex_installer_cache_dir,
    download_installer,
    find_vortex_executable,
    resolve_installer_url,
)
from profix.services.steam import (
    find_steam_paths,
    find_app_manifests,
    parse_acf_manifest,
    resolve_proton_path,
    is_likely_game,
)


def init_shared_profix(args):
    """
    Initialize the shared profix prefix by running 'proton run wineboot -u' with the appropriate environment variable set to create the prefix layout.
    If the prefix already appears to be initialized and --force is not used, it will skip initialization to avoid overwriting existing data.
    """
    shared_root = get_shared_profix_root()
    shared_root.mkdir(parents=True, exist_ok=True)

    if is_prefix_initialized(shared_root) and not args.force:
        print(f"Shared profix already initialized: {shared_root / 'pfx'}")
        return

    proton_path = resolve_proton_path(args.proton_path or get_shared_profix_proton_path())

    env = build_proton_env(shared_root, proton_path)

    subprocess.run(
        [str(proton_path), "run", "wineboot", "-u"],
        check=True,
        env=env,
    )

    if not is_prefix_initialized(shared_root):
        raise RuntimeError("Prefix init command completed, but pfx layout was not created.")

    print(f"Initialized shared profix at: {shared_root / 'pfx'}")


def install_vortex(args):
    """Install Vortex into the shared profix using Proton."""
    shared_root = get_shared_profix_root()
    shared_root.mkdir(parents=True, exist_ok=True)

    if not is_prefix_initialized(shared_root):
        if get_shared_profix_auto_init():
            print("Shared profix not initialized. Initializing first...")
            init_shared_profix(argparse.Namespace(force=False, proton_path=args.proton_path))
        else:
            raise RuntimeError(
                "Shared profix is not initialized. Run 'profix init-shared-profix' first."
            )

    proton_path = resolve_proton_path(args.proton_path or get_shared_profix_proton_path())
    env = build_proton_env(shared_root, proton_path)

    if args.installer:
        installer_path = Path(args.installer).expanduser()
        if not installer_path.is_file():
            raise FileNotFoundError(f"Installer not found: {installer_path}")
        print(f"Using local installer: {installer_path}")
    else:
        installer_url = args.url or get_vortex_installer_url()
        if not installer_url:
            raise RuntimeError(
                "No installer URL configured. Provide --url or --installer."
            )

        resolved_installer_url = resolve_installer_url(installer_url)

        cache_dir = get_vortex_installer_cache_dir(shared_root)
        installer_path = cache_dir / installer_filename_from_url(resolved_installer_url)
        needs_download = args.force_download or not installer_path.exists()

        print(f"Installer URL: {installer_url}")
        if resolved_installer_url != installer_url:
            print(f"Resolved download URL: {resolved_installer_url}")

        if needs_download:
            if not args.yes:
                answer = input("Download installer now? [y/N]: ").strip().lower()
                if answer not in {"y", "yes"}:
                    print("Installation cancelled before download.")
                    return

            print(f"Downloading installer to: {installer_path}")
            download_installer(resolved_installer_url, installer_path)
        else:
            print(f"Using cached installer: {installer_path}")

    print("Launching Vortex installer in shared profix...")
    subprocess.run(
        [str(proton_path), "run", str(installer_path)],
        check=True,
        env=env,
    )

    shortcut = ensure_vortex_shortcut_script()
    vortex_exe = find_vortex_executable(shared_root)
    if vortex_exe:
        print(f"Detected Vortex executable: {vortex_exe}")
    else:
        print("Installer finished. Could not auto-detect Vortex.exe yet.")

    print("Launch with: profix launch vortex")
    print(f"Shortcut script: {shortcut}")


def launch_vortex(args):
    """Launch Vortex from the shared profix via Proton."""
    shared_root = get_shared_profix_root()
    if not is_prefix_initialized(shared_root):
        raise RuntimeError(
            "Shared profix is not initialized. Run 'profix init-shared-profix' first."
        )

    proton_path = resolve_proton_path(args.proton_path or get_shared_profix_proton_path())
    vortex_exe = find_vortex_executable(shared_root)
    if not vortex_exe:
        raise FileNotFoundError(
            "Could not locate Vortex.exe in shared profix. Run 'profix install vortex' first."
        )

    env = build_proton_env(shared_root, proton_path)
    print(f"Launching Vortex: {vortex_exe}")
    subprocess.run([str(proton_path), "run", str(vortex_exe)], check=True, env=env)


def sync_shared_profix(args):
    """
    Sync symlinks for all scanned Steam games into the shared profix games directory.
    """
    shared_root = get_shared_profix_root()
    pfx_path = shared_root / "pfx"

    if not is_prefix_initialized(shared_root):
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