import re
from pathlib import Path


def is_valid_youtube_url(url: str) -> bool:
    """Check if the URL is a valid YouTube URL."""
    if not url:
        return False
    youtube_regex = (
        r"(https?://)?(www\.)?"
        r"(youtube|youtu|youtube-nocookie)\.(com|be)/"
        r"(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
    )
    return bool(re.match(youtube_regex, url.strip()))


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