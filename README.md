# Profix

A Linux Steam and Proton prefix manager.

## Overview

Profix scans your Steam installations for installed games, parses their app manifests, and stores the results in a local SQLite database. It is designed for Linux users running Steam games through Proton and provides a foundation for managing Proton prefix paths alongside game metadata.

## Features

- Detects Steam installations from common Linux paths (native, Flatpak, and `.steam` symlink)
- Parses Steam `appmanifest_*.acf` files to extract game names and App IDs
- Saves and updates game metadata in a local SQLite database (`~/.local/share/profix/profix.db`)
- Initializes a single shared Proton prefix for tool and mod-manager reuse
- Syncs symlinked game directories into the shared prefix so tools can use stable Windows-style paths
- Supports dry-run mode to preview scan results without writing to the database
- Optionally displays the path to each manifest file during a scan

## Requirements

- Python 3.12 or newer
- Linux (Steam on Proton)
- [PyYAML](https://pypi.org/project/PyYAML/) 6.0+

## Installation

```bash
pip install .
```

Or, for development:

```bash
pip install -e .
```

## Usage

### Scan for installed Steam games

```bash
profix scan
```

Show the manifest file path for each game:

```bash
profix scan --manifest-paths
```

Preview results without saving to the database:

```bash
profix scan --dry-run
```

### Initialize the database

Create (or reset) the database schema:

```bash
profix init-db
```

### Initialize the shared profix

Create the shared Proton prefix once:

```bash
profix init-shared-profix
```

Force re-initialization of the shared prefix:

```bash
profix init-shared-profix --force
```

Use a specific Proton executable:

```bash
profix init-shared-profix --proton-path "/path/to/steamapps/common/Proton - Experimental/proton"
```

### Sync game links into the shared profix

Preview link operations:

```bash
profix sync-shared-profix --dry-run
```

Create/update symlinks for all scanned games:

```bash
profix sync-shared-profix
```

Each game gets a directory named from `link_name_template` containing:

- `common` -> symlink to Steam `steamapps/common/<installdir>`
- `pfx` -> symlink to Steam `steamapps/compatdata/<appid>/pfx`

This gives a consistent per-game layout under the shared profix games directory.

Force replacement of incorrect existing links:

```bash
profix sync-shared-profix --force
```

## Configuration

Default Steam search paths are defined in `profix/data/default.yml`:

```yaml
steam_paths:
  - "~/.local/share/Steam"
  - "~/.steam/steam"
  - "~/.var/app/com.valvesoftware.Steam/data/Steam"
```

Profix will scan whichever of these directories actually exist on your system.

Shared profix settings are also configured in `profix/data/default.yml`:

```yaml
shared_profix:
  root: ~/.local/share/profix/shared
  games_dir: drive_c/Games
  link_name_template: "{name} [{app_id}]"
  proton_path:
  auto_init: true
```

- `root`: compat data root that will contain `pfx/`
- `games_dir`: relative path inside `pfx/` where game links are created
- `link_name_template`: template for symlink names
- `proton_path`: optional explicit Proton executable path
- `auto_init`: auto-initialize shared profix during sync if needed

## Database

Game records are stored at `~/.local/share/profix/profix.db` in a single `games` table:

| Column | Type | Description |
|---|---|---|
| `app_id` | TEXT (PK) | Steam App ID |
| `name` | TEXT | Game name |
| `install_path` | TEXT | Path to the game's install directory |
| `manifest_path` | TEXT | Path to the `appmanifest_*.acf` file |
| `prefix_path` | TEXT | Path to the Proton prefix (if set) |
| `last_seen_at` | TEXT | Timestamp of the last scan |

Records are upserted on each scan so the database always reflects the latest state.

## Project Structure

```
profix/
├── main.py        # CLI entry point
├── steam.py       # Steam path discovery and manifest parsing
├── db.py          # SQLite database helpers
├── config.py      # Configuration loader
├── data/
│   └── default.yml  # Default configuration
└── sql/
    ├── schema.sql     # Database schema
    ├── save_game.sql  # Upsert query
    └── get_games.sql  # Select query
```

## License

This project does not currently specify a license.
