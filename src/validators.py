import re
from pathlib import Path

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.)?(youtube\.com|youtu\.be)/",
    re.IGNORECASE,
)


def is_valid_youtube_url(url: str) -> bool:
    if not url:
        return False
    return bool(YOUTUBE_URL_RE.match(url.strip()))


def is_valid_folder_path(path_value: str) -> bool:
    path = Path(path_value).expanduser()
    return path.exists() and path.is_dir()


def normalize_folder_path(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()
