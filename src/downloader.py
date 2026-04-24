from pathlib import Path
from typing import Callable, Optional
import shutil

import yt_dlp

from .config import FFMPEG_LOCATION, FORMAT_OPTIONS
from .validators import is_valid_youtube_url


class DownloadError(Exception):
    pass


class YTDownloader:
    def __init__(self, allow_playlist: bool = False):
        self.allow_playlist = allow_playlist

    def get_video_info(self, url: str) -> dict:
        if not is_valid_youtube_url(url):
            raise DownloadError("URL inválida ou não suportada.")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as error:
            raise DownloadError(self._friendly_error_message(str(error))) from error
        return info

    def download(
        self,
        url: str,
        output_folder: Path,
        format_key: str,
        allow_playlist: bool,
        progress_hook: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        if not is_valid_youtube_url(url):
            raise DownloadError("URL inválida ou não suportada.")

        output_folder.mkdir(parents=True, exist_ok=True)
        ydl_opts = self._build_ydl_options(format_key, output_folder, allow_playlist)
        if progress_hook:
            ydl_opts["progress_hooks"] = [progress_hook]

        self._validate_ffmpeg_if_needed(ydl_opts.get("postprocessors", []))
        self._validate_ffmpeg_location(ydl_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as error:
            raise DownloadError(self._friendly_error_message(str(error))) from error

        return info

    def _build_ydl_options(self, format_key: str, output_folder: Path, allow_playlist: bool) -> dict:
        mapping = {
            "mp4_1080": {
                "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]",
                "postprocessors": [],
            },
            "mp4_720": {
                "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]",
                "postprocessors": [],
            },
            "mp4_480": {
                "format": "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4]",
                "postprocessors": [],
            },
            "mp3_320": {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    }
                ],
            },
            "mp3_192": {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            },
            "mp3_128": {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "128",
                    }
                ],
            },
        }

        selected = mapping.get(format_key)
        if selected is None:
            raise DownloadError("Formato de download não reconhecido.")

        ydl_options = {
            "format": selected["format"],
            "postprocessors": selected["postprocessors"],
            "outtmpl": str(output_folder / "%(title).200B.%(ext)s"),
            "noplaylist": not allow_playlist,
            "quiet": True,
            "no_warnings": True,
            "continuedl": True,
            "ignoreerrors": False,
            "writesubtitles": False,
            "writethumbnail": False,
        }
        if (FFMPEG_LOCATION / "ffmpeg.exe").exists():
            ydl_options["ffmpeg_location"] = str(FFMPEG_LOCATION)

        return ydl_options

    @staticmethod
    def _validate_ffmpeg_if_needed(postprocessors: list) -> None:
        if not postprocessors:
            return

        requires_ffmpeg = any(
            proc.get("key", "").lower().startswith("ffmpeg")
            for proc in postprocessors
        )
        if requires_ffmpeg and not ((FFMPEG_LOCATION / "ffmpeg.exe").exists() or shutil.which("ffmpeg") is not None):
            raise DownloadError(
                f"FFmpeg não encontrado em {FFMPEG_LOCATION}. Instale o FFmpeg em C:\\ffmpeg\\bin ou configure-o no PATH."
            )

    @staticmethod
    def _validate_ffmpeg_location(ydl_opts: dict) -> None:
        ffmpeg_key = ydl_opts.get("ffmpeg_location")
        if ffmpeg_key and (Path(ffmpeg_key) / "ffmpeg.exe").exists():
            return
        if shutil.which("ffmpeg") is not None:
            return
        raise DownloadError(
            f"FFmpeg não encontrado em {FFMPEG_LOCATION}. Instale o FFmpeg em C:\\ffmpeg\\bin ou configure-o no PATH."
        )

    @staticmethod
    def _friendly_error_message(message: str) -> str:
        lower = message.lower()
        if "private" in lower and "video" in lower:
            return "Vídeo privado ou indisponível."
        if "this video is unavailable" in lower or "video unavailable" in lower:
            return "Vídeo indisponível ou removido."
        if "unable to download webpage" in lower or "http error" in lower or "connection" in lower:
            return "Falha de conexão. Verifique sua internet e tente novamente."
        if "unsupported url" in lower:
            return "Link inválido ou não suportado."
        return message

    @staticmethod
    def get_format_choices():
        return [name for name, _ in FORMAT_OPTIONS]

    @staticmethod
    def format_key_from_label(label: str) -> str:
        for name, key in FORMAT_OPTIONS:
            if name == label:
                return key
        raise DownloadError("Formato selecionado inválido.")
