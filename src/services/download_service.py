import copy
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yt_dlp

from ..config import EXECUTABLE_ROOT, FORMAT_OPTIONS, PROJECT_ROOT

ProgressHook = Callable[[Dict[str, Any]], None]
CancelCallback = Callable[[], bool]
StatusCallback = Callable[[str], None]


class DownloadError(Exception):
    pass


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    output_folder: Path
    format_label: str
    allow_playlist: bool
    progress_hook: Optional[ProgressHook] = None
    should_cancel: Optional[CancelCallback] = None
    status_callback: Optional[StatusCallback] = None


@dataclass(frozen=True)
class DownloadResult:
    info: Dict[str, Any]
    title: str
    output_folder: Path
    format_label: str


def get_ffmpeg_location() -> Optional[str]:
    """
    Detecta a localizacao do FFmpeg nesta ordem:
    1. pasta_do_exe/tools/ffmpeg/bin/ffmpeg.exe
    2. pasta_do_projeto/tools/ffmpeg/bin/ffmpeg.exe
    3. C:/ffmpeg/bin/ffmpeg.exe
    4. PATH do sistema

    Retorna o diretorio onde o ffmpeg.exe esta localizado, ou None se nao encontrado.
    """
    executable_ffmpeg = EXECUTABLE_ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if executable_ffmpeg.exists():
        return str(executable_ffmpeg.parent)

    project_ffmpeg = PROJECT_ROOT / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if project_ffmpeg.exists():
        return str(project_ffmpeg.parent)

    ffmpeg_exe = Path(r"C:/ffmpeg/bin/ffmpeg.exe")
    if ffmpeg_exe.exists():
        return str(ffmpeg_exe.parent)

    which_result = shutil.which("ffmpeg")
    if which_result:
        return str(Path(which_result).parent)

    return None


class DownloadService:
    def download(self, request: DownloadRequest) -> DownloadResult:
        format_key = self.format_key_from_label(request.format_label)
        return self.download_with_format_key(
            url=request.url,
            output_folder=request.output_folder,
            format_key=format_key,
            allow_playlist=request.allow_playlist,
            progress_hook=request.progress_hook,
            should_cancel=request.should_cancel,
            status_callback=request.status_callback,
            format_label=request.format_label,
        )

    def download_with_format_key(
        self,
        url: str,
        output_folder: Path,
        format_key: str,
        allow_playlist: bool,
        progress_hook: Optional[ProgressHook] = None,
        should_cancel: Optional[CancelCallback] = None,
        status_callback: Optional[StatusCallback] = None,
        format_label: Optional[str] = None,
    ) -> DownloadResult:
        ydl_opts = self._build_ydl_options(format_key, output_folder, allow_playlist)
        combined_hook = self._build_progress_hook(progress_hook, should_cancel)
        if combined_hook:
            ydl_opts["progress_hooks"] = [combined_hook]

        try:
            info = self._extract_with_options(url, ydl_opts)
        except Exception as e:
            if self._should_try_best_fallback(format_key, ydl_opts, e):
                if status_callback:
                    status_callback("Formato solicitado indisponível. Tentando melhor formato disponível.")
                fallback_opts = copy.deepcopy(ydl_opts)
                fallback_opts["format"] = "best"
                try:
                    info = self._extract_with_options(url, fallback_opts)
                except Exception as fallback_error:
                    raise DownloadError(f"Erro no download: {str(fallback_error)}")
            else:
                raise DownloadError(f"Erro no download: {str(e)}")

        return DownloadResult(
            info=info,
            title=info.get("title") or url,
            output_folder=output_folder,
            format_label=format_label or format_key,
        )

    def _extract_with_options(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    def _should_try_best_fallback(self, format_key: str, ydl_opts: Dict[str, Any], error: Exception) -> bool:
        if not format_key.startswith("mp4") or ydl_opts.get("format") == "best":
            return False

        message = str(error).lower()
        return (
            "requested format is not available" in message
            or "requested format not available" in message
            or "format is not available" in message
        )

    def _build_progress_hook(
        self,
        progress_hook: Optional[ProgressHook],
        should_cancel: Optional[CancelCallback],
    ) -> Optional[ProgressHook]:
        if not progress_hook and not should_cancel:
            return None

        def hook(data: Dict[str, Any]) -> None:
            if should_cancel and should_cancel():
                raise yt_dlp.utils.DownloadError("Download cancelado pelo usuario.")
            if progress_hook:
                progress_hook(data)

        return hook

    def _build_ydl_options(self, format_key: str, output_folder: Path, allow_playlist: bool) -> Dict[str, Any]:
        base_opts: Dict[str, Any] = {
            "outtmpl": str(output_folder / "%(title)s.%(ext)s"),
            "noplaylist": not allow_playlist,
            "quiet": False,
            "no_warnings": False,
        }

        if format_key.startswith("mp4"):
            quality = format_key.split("_")[1]
            base_opts.update(
                {
                    "format": (
                        f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
                    ),
                    "merge_output_format": "mp4",
                    "postprocessors": [
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": "mp4",
                        }
                    ],
                }
            )
        elif format_key.startswith("mp3"):
            bitrate = format_key.split("_")[1]
            base_opts.update(
                {
                    "format": "bestaudio/best",
                    "extractaudio": True,
                    "audioformat": "mp3",
                    "audioquality": bitrate,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": bitrate,
                        }
                    ],
                }
            )

        self._validate_ffmpeg_location(base_opts)
        return base_opts

    def _validate_ffmpeg_location(self, ydl_opts: Dict[str, Any]) -> None:
        if "postprocessors" not in ydl_opts and "merge_output_format" not in ydl_opts:
            return

        ffmpeg_location = get_ffmpeg_location()
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location
            print(f"FFmpeg detectado em: {ffmpeg_location}")
            return

        raise DownloadError(
            "FFmpeg não encontrado. Instale em C:\\ffmpeg\\bin ou use a instalação automática."
        )

    @staticmethod
    def get_format_choices():
        return [label for label, key in FORMAT_OPTIONS]

    @staticmethod
    def format_key_from_label(label: str) -> str:
        for option_label, key in FORMAT_OPTIONS:
            if option_label == label:
                return key
        return "mp4_720"
