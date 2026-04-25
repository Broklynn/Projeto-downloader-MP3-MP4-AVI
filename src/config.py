from pathlib import Path
import json
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOWNLOAD_PATH = Path.home() / "Downloads"
HISTORY_DB_PATH = PROJECT_ROOT / "history.db"
FFMPEG_LOCATION = Path(r"C:\ffmpeg\bin")
CONFIG_FILE = PROJECT_ROOT / "config.json"

FORMAT_OPTIONS = [
    ("MP4 1080p", "mp4_1080"),
    ("MP4 720p", "mp4_720"),
    ("MP4 480p", "mp4_480"),
    ("MP3 320k", "mp3_320"),
    ("MP3 192k", "mp3_192"),
    ("MP3 128k", "mp3_128"),
]


class ConfigManager:
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.default_config = {
            "last_download_path": str(DEFAULT_DOWNLOAD_PATH),
            "appearance_mode": "System"
        }
        self.config = self.load_config()

    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_last_download_path(self):
        path = Path(self.config.get("last_download_path", str(DEFAULT_DOWNLOAD_PATH)))
        if path.exists():
            return str(path)
        return str(DEFAULT_DOWNLOAD_PATH)

    def set_last_download_path(self, path):
        self.config["last_download_path"] = path
        self.save_config()

    def get_appearance_mode(self):
        return self.config.get("appearance_mode", "Dark")

    def set_appearance_mode(self, mode):
        self.config["appearance_mode"] = mode
        self.save_config()