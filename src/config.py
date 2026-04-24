from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOWNLOAD_PATH = Path.home() / "Downloads"
HISTORY_DB_PATH = PROJECT_ROOT / "history.db"
FFMPEG_LOCATION = Path(r"C:\ffmpeg\bin")

FORMAT_OPTIONS = [
    ("MP4 1080p", "mp4_1080"),
    ("MP4 720p", "mp4_720"),
    ("MP4 480p", "mp4_480"),
    ("MP3 320k", "mp3_320"),
    ("MP3 192k", "mp3_192"),
    ("MP3 128k", "mp3_128"),
]
