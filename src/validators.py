from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse


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


def normalize_youtube_url(url: str, allow_playlist: bool = False) -> str:
    """Return a clean YouTube URL for preview/download without noisy browser params."""
    if not url:
        return url

    original_url = url.strip()
    try:
        parsed = urlparse(original_url)
        host = parsed.netloc.lower().split(":")[0]
        if not _is_youtube_host(host):
            return original_url

        query = parse_qs(parsed.query)
        playlist_id = _first_query_value(query, "list")
        video_id = _extract_youtube_video_id(parsed, query, host)

        if video_id:
            normalized = f"https://www.youtube.com/watch?v={quote(video_id, safe='')}"
            if allow_playlist and playlist_id:
                normalized = f"{normalized}&list={quote(playlist_id, safe='')}"
            return normalized

        if allow_playlist and playlist_id:
            return f"https://www.youtube.com/playlist?list={quote(playlist_id, safe='')}"

        return original_url
    except Exception:
        return original_url


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


def _is_youtube_host(host: str) -> bool:
    return (
        host == "youtu.be"
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )


def _first_query_value(query: dict, key: str) -> str:
    values = query.get(key) or []
    return values[0].strip() if values else ""


def _extract_youtube_video_id(parsed, query: dict, host: str) -> str:
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]

    video_id = _first_query_value(query, "v")
    if video_id:
        return video_id

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in ("shorts", "embed", "v"):
        return path_parts[1]

    return ""
