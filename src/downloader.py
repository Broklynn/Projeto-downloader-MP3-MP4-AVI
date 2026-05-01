from pathlib import Path

from .services.download_service import DownloadError, DownloadService, get_ffmpeg_location
from .services.preview_service import PreviewService


class YTDownloader:
    """Compatibilidade para imports antigos; a logica real vive em services."""

    def __init__(self, allow_playlist: bool = False):
        self.allow_playlist = allow_playlist
        self.download_service = DownloadService()
        self.preview_service = PreviewService()

    def get_video_info(self, url: str) -> dict:
        return self.preview_service.fetch_info(url)

    def download(
        self,
        url: str,
        output_folder: Path,
        format_key: str,
        allow_playlist: bool,
        progress_hook=None,
    ) -> dict:
        result = self.download_service.download_with_format_key(
            url=url,
            output_folder=output_folder,
            format_key=format_key,
            allow_playlist=allow_playlist,
            progress_hook=progress_hook,
        )
        return result.info

    @staticmethod
    def get_format_choices():
        return DownloadService.get_format_choices()

    @staticmethod
    def format_key_from_label(label: str) -> str:
        return DownloadService.format_key_from_label(label)
