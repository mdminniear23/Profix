from pathlib import Path
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent / "data" / "default.yml"


def load_default_config():
    """Load the default configuration from the YAML file and return it as a dictionary."""
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_steam_paths():
    """Get the list of Steam installation paths from the configuration, expanding user directories."""
    config = load_default_config()
    raw_paths = config.get("steam_paths", [])
    return [Path(path).expanduser() for path in raw_paths]


def _shared():
    """Get the shared profix configuration section as a dictionary."""
    config = load_default_config()
    return config.get("shared_profix", {}) or {}


def get_shared_profix_root() -> Path:
    """Get the root directory for shared profix data from the configuration, expanding user directories."""
    raw = _shared().get("root", "~/.local/share/profix/shared")
    return Path(raw).expanduser()


def get_shared_profix_games_dir() -> str:
    """Get the relative path to the games directory within the shared profix root from the configuration."""
    return _shared().get("games_dir", "drive_c/Games")


def get_shared_profix_link_name_template() -> str:
    """Get the template for naming game links from the configuration."""
    return _shared().get("link_name_template", "{name} [{app_id}]")


def get_shared_profix_proton_path() -> Path | None:
    """Get the path to the Proton executable from the configuration, expanding user directories. Returns None if not set."""
    raw = _shared().get("proton_path")
    if not raw:
        return None
    return Path(raw).expanduser()


def get_shared_profix_auto_init() -> bool:
    """Get the auto_init setting from the configuration, which indicates whether to automatically initialize the database. Defaults to True if not set."""
    return bool(_shared().get("auto_init", True))