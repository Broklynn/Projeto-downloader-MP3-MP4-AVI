from pathlib import Path
import json
import sys


def get_source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_executable_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.argv[0]).resolve().parent
    return get_source_root()


PROJECT_ROOT = get_source_root()
EXECUTABLE_ROOT = get_executable_root()
DEFAULT_DOWNLOAD_PATH = Path.home() / "Downloads"
HISTORY_DB_PATH = PROJECT_ROOT / "history.db"
CONFIG_FILE = PROJECT_ROOT / "config.json"


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
