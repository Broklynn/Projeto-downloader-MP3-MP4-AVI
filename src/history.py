import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .config import HISTORY_DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    output_format TEXT,
    output_quality TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL
)
"""


class HistoryDB:
    def __init__(self, db_path: Path = HISTORY_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            conn.execute(CREATE_TABLE_SQL)
            columns = [row[1] for row in conn.execute("PRAGMA table_info(history)").fetchall()]
            if "output_quality" not in columns:
                conn.execute("ALTER TABLE history ADD COLUMN output_quality TEXT")
            conn.commit()

    def save_record(
        self,
        url: str,
        title: str,
        output_format: str,
        output_quality: str,
        output_path: str,
    ) -> None:
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                (
                    "INSERT INTO history "
                    "(url, title, output_format, output_quality, output_path, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (url, title, output_format, output_quality, output_path, created_at),
            )
            conn.commit()

    def video_downloaded(self, url: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM history WHERE url = ? LIMIT 1",
                (url,),
            ).fetchone()
        return row is not None

    def get_recent(self, limit: int = 10) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                (
                    "SELECT url, title, output_format, output_quality, output_path, created_at "
                    "FROM history ORDER BY id DESC LIMIT ?"
                ),
                (limit,),
            ).fetchall()
        return [
            {
                "url": row[0],
                "title": row[1],
                "output_format": row[2],
                "output_quality": row[3],
                "output_path": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]
