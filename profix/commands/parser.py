import argparse
from pathlib import Path

from profix.commands.handlers import (
    scan,
    init_shared_profix,
    init_database,
    sync_shared_profix,
)
from profix.commands.tool_registry import (
    ArgumentSpec,
    ToolCommandSpec,
    INSTALL_TOOL_REGISTRY,
    LAUNCH_TOOL_REGISTRY,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="profix",
        description="Proton prefix manager for Linux Steam installations."
    )

    register_commands(parser)
    return parser


def register_commands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command", required=True)
    _register_scan_command(subparsers)
    _register_init_shared_profix_command(subparsers)
    _register_init_db_command(subparsers)
    _register_sync_shared_profix_command(subparsers)
    _register_tool_family(
        subparsers=subparsers,
        command_name="install",
        command_help="Install supported tools into the shared profix",
        target_dest="install_target",
        registry=INSTALL_TOOL_REGISTRY,
    )
    _register_tool_family(
        subparsers=subparsers,
        command_name="launch",
        command_help="Launch installed tools from the shared profix",
        target_dest="launch_target",
        registry=LAUNCH_TOOL_REGISTRY,
    )


def _register_scan_command(subparsers) -> None:
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
    scan_parser.add_argument(
        "--include-non-games",
        action="store_true",
        help="Include compatibility tools/runtimes and other non-game apps"
    )
    scan_parser.set_defaults(func=scan)


def _register_init_shared_profix_command(subparsers) -> None:
    init_shared_parser = subparsers.add_parser(
        "init-shared-profix",
        help="Initialize a single shared Proton prefix for profix"
    )
    init_shared_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run initialization even if the shared prefix already exists"
    )
    _add_proton_path_argument(
        init_shared_parser,
        "Path to the Proton executable to use for initializing the shared prefix",
    )
    init_shared_parser.set_defaults(func=init_shared_profix)


def _register_init_db_command(subparsers) -> None:
    db_parser = subparsers.add_parser("init-db", help="Initialize the Profix database")
    db_parser.set_defaults(func=init_database)


def _register_sync_shared_profix_command(subparsers) -> None:
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


def _register_tool_family(
    subparsers,
    command_name: str,
    command_help: str,
    target_dest: str,
    registry: dict[str, ToolCommandSpec],
) -> None:
    tool_family_parser = subparsers.add_parser(command_name, help=command_help)
    tool_subparsers = tool_family_parser.add_subparsers(dest=target_dest, required=True)

    for tool_name, tool_spec in registry.items():
        tool_parser = tool_subparsers.add_parser(tool_name, help=tool_spec.help)
        _add_argument_specs(tool_parser, tool_spec.argument_specs)

        if tool_spec.proton_path_help:
            _add_proton_path_argument(tool_parser, tool_spec.proton_path_help)

        tool_parser.set_defaults(func=tool_spec.handler)


def _add_argument_specs(parser: argparse.ArgumentParser, specs: tuple[ArgumentSpec, ...]) -> None:
    for spec in specs:
        parser.add_argument(*spec.flags, **spec.kwargs)


def _add_proton_path_argument(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument(
        "--proton-path",
        type=Path,
        help=help_text,
    )