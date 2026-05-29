from pathlib import Path
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent / "data" / "default.yml"


def load_default_config():
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_steam_paths():
    config = load_default_config()
    raw_paths = config.get("steam_paths", [])

    return [Path(path).expanduser() for path in raw_paths]