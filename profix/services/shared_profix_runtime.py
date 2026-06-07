import os
from pathlib import Path

from profix.services.steam import find_steam_paths


def is_prefix_initialized(root: Path) -> bool:
    """
    Checks if a given directory looks like an initialized Proton prefix by checking for the presence of system.reg and drive_c.
    """
    return (root / "pfx" / "system.reg").exists() and (root / "pfx" / "drive_c").exists()


def get_steam_client_install_path() -> Path:
    """Pick a Steam client install path for Proton runtime environment variables."""
    steam_paths = find_steam_paths()
    if not steam_paths:
        raise RuntimeError("No Steam installations found for STEAM_COMPAT_CLIENT_INSTALL_PATH.")
    return steam_paths[0]


def build_proton_env(shared_root: Path, proton_path: Path) -> dict[str, str]:
    """Build env vars needed to run processes through Proton."""
    env = os.environ.copy()
    env["STEAM_COMPAT_DATA_PATH"] = str(shared_root)
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(get_steam_client_install_path())
    env["STEAM_COMPAT_TOOL_PATHS"] = str(proton_path.parent)
    return env


def ensure_vortex_shortcut_script() -> Path:
    """Create a small launcher script that calls 'profix launch vortex'."""
    launcher_dir = Path.home() / ".local" / "share" / "profix" / "bin"
    launcher_path = launcher_dir / "profix-launch-vortex"
    launcher_dir.mkdir(parents=True, exist_ok=True)

    script_content = "#!/usr/bin/env bash\nexec profix launch vortex \"$@\"\n"
    if not launcher_path.exists() or launcher_path.read_text(encoding="utf-8") != script_content:
        launcher_path.write_text(script_content, encoding="utf-8")
        launcher_path.chmod(0o755)

    return launcher_path