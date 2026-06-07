from pathlib import Path
import shutil
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def installer_filename_from_url(url: str) -> str:
    """Build a cache filename from the installer URL."""
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or "vortex-setup.exe"


def _pick_release_asset_download_url(assets: list[dict], requested_filename: str) -> str | None:
    """Pick the best asset URL from a GitHub release assets list."""
    requested_lower = requested_filename.lower()

    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name == requested_lower:
            return asset.get("browser_download_url")

    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if requested_lower in name:
            return asset.get("browser_download_url")

    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe") and "vortex" in name and "setup" in name:
            return asset.get("browser_download_url")

    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith(".exe"):
            return asset.get("browser_download_url")

    return None


def resolve_installer_url(url: str) -> str:
    """
    Resolve installer URLs that point to GitHub latest/download pseudo-paths.

    This avoids 404s when the actual asset is versioned (e.g., vortex-setup-2.0.2.exe).
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host not in {"github.com", "www.github.com"}:
        return url

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 6:
        return url

    owner, repo = parts[0], parts[1]
    if parts[2:5] != ["releases", "latest", "download"]:
        return url

    requested_filename = parts[5]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    request = Request(
        api_url,
        headers={
            "User-Agent": "profix",
            "Accept": "application/vnd.github+json",
        },
    )

    try:
        with urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return url

    assets = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(assets, list):
        return url

    selected = _pick_release_asset_download_url(assets, requested_filename)
    return selected or url


def get_vortex_installer_cache_dir(shared_root: Path) -> Path:
    """Return the cache directory used for Vortex installers."""
    return shared_root / "installers"


def download_installer(url: str, destination: Path) -> None:
    """Download installer content to the destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "profix"})
    try:
        with urlopen(request) as response, destination.open("wb") as file_obj:
            shutil.copyfileobj(response, file_obj)
    except HTTPError as exc:
        raise RuntimeError(f"Download failed ({exc.code}) for URL: {url}") from exc


def find_vortex_executable(shared_root: Path) -> Path | None:
    """Find Vortex.exe inside the shared profix drive_c tree."""
    drive_c = shared_root / "pfx" / "drive_c"

    candidates = [
        drive_c / "Program Files" / "Black Tree Gaming Ltd" / "Vortex" / "Vortex.exe",
        drive_c / "Program Files (x86)" / "Black Tree Gaming Ltd" / "Vortex" / "Vortex.exe",
        drive_c
        / "users"
        / "steamuser"
        / "AppData"
        / "Local"
        / "Programs"
        / "Vortex"
        / "Vortex.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    if not drive_c.exists():
        return None

    for candidate in drive_c.rglob("Vortex.exe"):
        if candidate.is_file():
            return candidate

    return None
