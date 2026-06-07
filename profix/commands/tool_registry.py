from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from profix.commands.handlers import install_vortex, launch_vortex


@dataclass(frozen=True)
class ArgumentSpec:
    flags: tuple[str, ...]
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class ToolCommandSpec:
    help: str
    handler: Callable[..., Any]
    argument_specs: tuple[ArgumentSpec, ...] = ()
    proton_path_help: str | None = "Path to the Proton executable to use"


INSTALL_TOOL_REGISTRY: dict[str, ToolCommandSpec] = {
    "vortex": ToolCommandSpec(
        help="Install Vortex into the shared profix",
        handler=install_vortex,
        argument_specs=(
            ArgumentSpec(
                flags=("--installer",),
                kwargs={
                    "type": Path,
                    "help": "Path to a local Vortex installer executable",
                },
            ),
            ArgumentSpec(
                flags=("--url",),
                kwargs={
                    "help": "Installer URL to download Vortex from",
                },
            ),
            ArgumentSpec(
                flags=("--force-download",),
                kwargs={
                    "action": "store_true",
                    "help": "Re-download installer even if cached copy exists",
                },
            ),
            ArgumentSpec(
                flags=("--yes",),
                kwargs={
                    "action": "store_true",
                    "help": "Skip download confirmation prompt",
                },
            ),
        ),
    ),
}


LAUNCH_TOOL_REGISTRY: dict[str, ToolCommandSpec] = {
    "vortex": ToolCommandSpec(
        help="Launch Vortex from the shared profix",
        handler=launch_vortex,
    ),
}