from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """Check if the URL is a valid web address for yt-dlp."""
    if not url:
        return False

    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


def is_valid_folder_path(path_value: str) -> bool:
    """Check if the path is a valid folder path."""
    if not path_value:
        return False
    try:
        path = Path(path_value)
        return path.exists() and path.is_dir()
    except Exception:
        return False


def normalize_folder_path(path_value: str) -> Path:
    """Normalize and return a Path object."""
    return Path(path_value).resolve()