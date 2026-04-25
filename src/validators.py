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


def normalize_youtube_url(url: str, allow_playlist: bool = False) -> str:
    """
    Normalize YouTube URL to standard format: https://www.youtube.com/watch?v=ID

    Accepts various formats:
    - https://www.youtube.com/watch?v=ID
    - https://www.youtube.com/watch?v=ID&t=30s
    - https://www.youtube.com/watch?v=ID&list=...
    - https://youtu.be/ID
    - https://youtube.com/shorts/ID

    Keeps playlist parameters (&list=) only if allow_playlist is True.
    Always removes index and other unnecessary parameters.
    Returns normalized URL or original URL if extraction fails.
    """
    if not url:
        return url

    url = url.strip()

    # Extract list parameter if present and allowed
    list_param = ""
    if allow_playlist:
        list_match = re.search(r'&list=([^&]+)', url)
        if list_match:
            list_param = f"&list={list_match.group(1)}"

    # Patterns to extract video ID
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",  # watch?v=ID
        r"youtu\.be/([a-zA-Z0-9_-]{11})",              # youtu.be/ID
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",    # shorts/ID
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",     # embed/ID
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",         # v/ID
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            normalized = f"https://www.youtube.com/watch?v={video_id}"
            if list_param:
                normalized += list_param
            return normalized

    # If no pattern matches, return original URL
    return url


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