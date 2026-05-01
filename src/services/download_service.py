import copy
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yt_dlp

from ..config import EXECUTABLE_ROOT, PROJECT_ROOT

ProgressHook = Callable[[Dict[str, Any]], None]
CancelCallback = Callable[[], bool]
StatusCallback = Callable[[str], None]

VIDEO_FORMATS = ["MP4", "MKV", "WEBM", "AVI"]
AUDIO_FORMATS = ["MP3", "M4A", "WAV", "OPUS"]
VIDEO_QUALITIES = ["Melhor disponível", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["320 kbps", "192 kbps", "128 kbps"]
FALLBACK_STATUS_MESSAGE = "Qualidade selecionada indisponível. Usando melhor opção disponível."
AVI_CONVERSION_ERROR_MESSAGE = "Falha ao converter para AVI. Tente MP4 ou MKV."
AVI_INTERMEDIATE_MARKER = ".avi_source"


class DownloadError(Exception):
    pass


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    output_folder: Path
    output_format: str
    quality: str
    allow_playlist: bool
    progress_hook: Optional[ProgressHook] = None
    should_cancel: Optional[CancelCallback] = None
    status_callback: Optional[StatusCallback] = None


@dataclass(frozen=True)
class DownloadResult:
    info: Dict[str, Any]
    title: str
    output_folder: Path
    output_format: str
    quality: str


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
        output_format = self.normalize_output_format(request.output_format)
        quality = self.normalize_quality(output_format, request.quality)
        return self.download_with_format(
            url=request.url,
            output_folder=request.output_folder,
            output_format=output_format,
            quality=quality,
            allow_playlist=request.allow_playlist,
            progress_hook=request.progress_hook,
            should_cancel=request.should_cancel,
            status_callback=request.status_callback,
        )

    def download_with_format(
        self,
        url: str,
        output_folder: Path,
        output_format: str,
        quality: str,
        allow_playlist: bool,
        progress_hook: Optional[ProgressHook] = None,
        should_cancel: Optional[CancelCallback] = None,
        status_callback: Optional[StatusCallback] = None,
    ) -> DownloadResult:
        output_format = self.normalize_output_format(output_format)
        quality = self.normalize_quality(output_format, quality)

        if output_format == "AVI":
            return self._download_avi(
                url=url,
                output_folder=output_folder,
                quality=quality,
                allow_playlist=allow_playlist,
                progress_hook=progress_hook,
                should_cancel=should_cancel,
                status_callback=status_callback,
            )

        ydl_opts = self._build_ydl_options(output_format, quality, output_folder, allow_playlist)
        combined_hook = self._build_progress_hook(progress_hook, should_cancel)
        if combined_hook:
            ydl_opts["progress_hooks"] = [combined_hook]

        info = self._extract_with_fallback(url, ydl_opts, status_callback)

        return DownloadResult(
            info=info,
            title=info.get("title") or url,
            output_folder=output_folder,
            output_format=output_format,
            quality=quality,
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
        output_format, quality = self.format_parts_from_key(format_key or format_label or "")
        return self.download_with_format(
            url=url,
            output_folder=output_folder,
            output_format=output_format,
            quality=quality,
            allow_playlist=allow_playlist,
            progress_hook=progress_hook,
            should_cancel=should_cancel,
            status_callback=status_callback,
        )

    def _extract_with_options(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    def _extract_with_fallback(
        self,
        url: str,
        ydl_opts: Dict[str, Any],
        status_callback: Optional[StatusCallback] = None,
    ) -> Dict[str, Any]:
        try:
            return self._extract_with_options(url, ydl_opts)
        except Exception as e:
            if self._should_try_best_fallback(ydl_opts, e):
                if status_callback:
                    status_callback(FALLBACK_STATUS_MESSAGE)
                fallback_opts = copy.deepcopy(ydl_opts)
                fallback_opts["format"] = "best"
                try:
                    return self._extract_with_options(url, fallback_opts)
                except Exception as fallback_error:
                    raise DownloadError(f"Erro no download: {str(fallback_error)}")
            raise DownloadError(f"Erro no download: {str(e)}")

    def _download_avi(
        self,
        url: str,
        output_folder: Path,
        quality: str,
        allow_playlist: bool,
        progress_hook: Optional[ProgressHook] = None,
        should_cancel: Optional[CancelCallback] = None,
        status_callback: Optional[StatusCallback] = None,
    ) -> DownloadResult:
        before_files = self._snapshot_avi_intermediates(output_folder)
        ydl_opts = self._build_avi_intermediate_options(quality, output_folder, allow_playlist)
        combined_hook = self._build_progress_hook(progress_hook, should_cancel)
        if combined_hook:
            ydl_opts["progress_hooks"] = [combined_hook]

        info = self._extract_with_fallback(url, ydl_opts, status_callback)
        intermediate_files = self._find_avi_intermediate_files(info, output_folder, before_files)
        if not intermediate_files:
            raise DownloadError(AVI_CONVERSION_ERROR_MESSAGE)

        if status_callback:
            status_callback("Convertendo para AVI...")

        for source_file in intermediate_files:
            target_file = self._avi_output_path(source_file)
            self._convert_to_avi(source_file, target_file)
            self._remove_file(source_file)

        return DownloadResult(
            info=info,
            title=info.get("title") or url,
            output_folder=output_folder,
            output_format="AVI",
            quality=quality,
        )

    def _should_try_best_fallback(self, ydl_opts: Dict[str, Any], error: Exception) -> bool:
        if ydl_opts.get("format") == "best":
            return False

        message = str(error).lower()
        return (
            "requested format is not available" in message
            or "requested format not available" in message
            or "format is not available" in message
            or "no video formats found" in message
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

    def _build_ydl_options(
        self,
        output_format: str,
        quality: str,
        output_folder: Path,
        allow_playlist: bool,
    ) -> Dict[str, Any]:
        if output_format == "AVI":
            return self._build_avi_intermediate_options(quality, output_folder, allow_playlist)

        base_opts: Dict[str, Any] = {
            "outtmpl": str(output_folder / "%(title)s.%(ext)s"),
            "noplaylist": not allow_playlist,
            "quiet": False,
            "no_warnings": False,
        }

        if self.is_video_format(output_format):
            base_opts.update(self._video_options(output_format, quality))
        else:
            base_opts.update(self._audio_options(output_format, quality))

        self._validate_ffmpeg_location(base_opts)
        return base_opts

    def _video_options(self, output_format: str, quality: str) -> Dict[str, Any]:
        if quality == "Melhor disponível":
            format_selector = "bestvideo+bestaudio/best"
        else:
            height = self._quality_height(quality)
            if output_format == "MP4":
                format_selector = (
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
                )
            elif output_format == "WEBM":
                format_selector = (
                    f"bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/"
                    f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
                )
            else:
                format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

        options: Dict[str, Any] = {
            "format": format_selector,
            "merge_output_format": "mkv" if output_format == "AVI" else output_format.lower(),
        }

        return options

    def _build_avi_intermediate_options(
        self,
        quality: str,
        output_folder: Path,
        allow_playlist: bool,
    ) -> Dict[str, Any]:
        base_opts: Dict[str, Any] = {
            "outtmpl": str(output_folder / f"%(title)s{AVI_INTERMEDIATE_MARKER}.%(ext)s"),
            "noplaylist": not allow_playlist,
            "quiet": False,
            "no_warnings": False,
            "overwrites": True,
            "format": self._avi_intermediate_format_selector(quality),
            "merge_output_format": "mkv",
        }
        self._validate_ffmpeg_location(base_opts)
        return base_opts

    def _avi_intermediate_format_selector(self, quality: str) -> str:
        if quality == "Melhor disponível":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

        height = self._quality_height(quality)
        return (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        )

    def _snapshot_avi_intermediates(self, output_folder: Path) -> Dict[Path, int]:
        return {
            path.resolve(): path.stat().st_mtime_ns
            for path in output_folder.glob(f"*{AVI_INTERMEDIATE_MARKER}.*")
            if path.is_file()
        }

    def _find_avi_intermediate_files(
        self,
        info: Dict[str, Any],
        output_folder: Path,
        before_files: Dict[Path, int],
    ) -> list[Path]:
        candidates: list[Path] = []
        for path_text in self._iter_download_paths(info):
            path = Path(path_text)
            if not path.is_absolute():
                path = output_folder / path
            if path.exists() and path.is_file() and AVI_INTERMEDIATE_MARKER in path.name:
                candidates.append(path)

        for path in output_folder.glob(f"*{AVI_INTERMEDIATE_MARKER}.*"):
            resolved = path.resolve()
            if not path.is_file():
                continue
            if resolved not in before_files or path.stat().st_mtime_ns != before_files[resolved]:
                candidates.append(path)

        unique_files: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen:
                unique_files.append(path)
                seen.add(resolved)
        return unique_files

    def _iter_download_paths(self, info: Dict[str, Any]):
        if not isinstance(info, dict):
            return

        for key in ("filepath", "_filename", "filename"):
            value = info.get(key)
            if value:
                yield value

        for requested_download in info.get("requested_downloads") or []:
            if not isinstance(requested_download, dict):
                continue
            for key in ("filepath", "_filename", "filename"):
                value = requested_download.get(key)
                if value:
                    yield value

        for entry in info.get("entries") or []:
            if isinstance(entry, dict):
                yield from self._iter_download_paths(entry)

    def _avi_output_path(self, source_file: Path) -> Path:
        if AVI_INTERMEDIATE_MARKER in source_file.name:
            base_name = source_file.name.rsplit(AVI_INTERMEDIATE_MARKER, 1)[0]
            return source_file.with_name(f"{base_name}.avi")
        return source_file.with_suffix(".avi")

    def _convert_to_avi(self, source_file: Path, target_file: Path) -> None:
        ffmpeg_executable = self._get_ffmpeg_executable()
        attempts = [
            ("libxvid", "libmp3lame"),
            ("mpeg4", "libmp3lame"),
            ("mpeg4", "mp3"),
        ]

        for video_codec, audio_codec in attempts:
            result = self._run_avi_conversion(source_file, target_file, ffmpeg_executable, video_codec, audio_codec)
            if result.returncode == 0 and target_file.exists() and target_file.stat().st_size > 0:
                return
            self._remove_file(target_file)

        raise DownloadError(AVI_CONVERSION_ERROR_MESSAGE)

    def _run_avi_conversion(
        self,
        source_file: Path,
        target_file: Path,
        ffmpeg_executable: str,
        video_codec: str,
        audio_codec: str,
    ) -> subprocess.CompletedProcess:
        command = [
            ffmpeg_executable,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_file),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-sn",
            "-c:v",
            video_codec,
            "-q:v",
            "5",
            "-c:a",
            audio_codec,
            "-b:a",
            "192k",
            str(target_file),
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )

    def _get_ffmpeg_executable(self) -> str:
        ffmpeg_location = get_ffmpeg_location()
        if not ffmpeg_location:
            raise DownloadError(
                "FFmpeg não encontrado. Instale em C:\\ffmpeg\\bin ou use a instalação automática."
            )

        ffmpeg_dir = Path(ffmpeg_location)
        ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)

        ffmpeg_bin = ffmpeg_dir / "ffmpeg"
        if ffmpeg_bin.exists():
            return str(ffmpeg_bin)

        return "ffmpeg"

    def _remove_file(self, path: Path) -> None:
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    def _audio_options(self, output_format: str, quality: str) -> Dict[str, Any]:
        bitrate = self._quality_bitrate(quality)
        if output_format == "MP3":
            return {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }
        if output_format == "M4A":
            return {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                        "preferredquality": bitrate,
                    }
                ],
            }
        if output_format == "WAV":
            return {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }
                ],
            }
        return {
            "format": "bestaudio[ext=opus]/bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": bitrate,
                }
            ],
        }

    def _validate_ffmpeg_location(self, ydl_opts: Dict[str, Any]) -> None:
        if "postprocessors" not in ydl_opts and "merge_output_format" not in ydl_opts:
            return

        ffmpeg_location = get_ffmpeg_location()
        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location
            return

        raise DownloadError(
            "FFmpeg não encontrado. Instale em C:\\ffmpeg\\bin ou use a instalação automática."
        )

    @staticmethod
    def get_output_format_choices():
        return VIDEO_FORMATS + AUDIO_FORMATS

    @staticmethod
    def get_quality_choices(output_format: str):
        return VIDEO_QUALITIES if DownloadService.is_video_format(output_format) else AUDIO_QUALITIES

    @staticmethod
    def get_format_choices():
        return DownloadService.get_output_format_choices()

    @staticmethod
    def is_video_format(output_format: str) -> bool:
        return DownloadService.normalize_output_format(output_format) in VIDEO_FORMATS

    @staticmethod
    def requires_ffmpeg(output_format: str) -> bool:
        return DownloadService.normalize_output_format(output_format) in VIDEO_FORMATS + AUDIO_FORMATS

    @staticmethod
    def normalize_output_format(output_format: str) -> str:
        normalized = (output_format or "MP4").strip().upper()
        if normalized in VIDEO_FORMATS + AUDIO_FORMATS:
            return normalized
        return "MP4"

    @staticmethod
    def normalize_quality(output_format: str, quality: str) -> str:
        choices = DownloadService.get_quality_choices(output_format)
        return quality if quality in choices else DownloadService.default_quality(output_format)

    @staticmethod
    def default_quality(output_format: str) -> str:
        return "1080p" if DownloadService.is_video_format(output_format) else "320 kbps"

    @staticmethod
    def format_key_from_label(label: str) -> str:
        output_format, quality = DownloadService.format_parts_from_key(label)
        if DownloadService.is_video_format(output_format):
            if quality == "Melhor disponível":
                return f"{output_format.lower()}_best"
            return f"{output_format.lower()}_{DownloadService._quality_height(quality)}"
        return f"{output_format.lower()}_{DownloadService._quality_bitrate(quality)}"

    @staticmethod
    def format_parts_from_key(format_key: str) -> tuple[str, str]:
        value = (format_key or "").strip()
        parts = value.replace(" ", "_").split("_")
        output_format = DownloadService.normalize_output_format(parts[0] if parts else "MP4")
        suffix = parts[1] if len(parts) > 1 else ""
        digits = "".join(ch for ch in suffix if ch.isdigit())

        if DownloadService.is_video_format(output_format):
            if suffix == "best":
                return output_format, "Melhor disponível"
            return output_format, f"{digits}p" if digits else "1080p"

        return output_format, f"{digits} kbps" if digits else "320 kbps"

    @staticmethod
    def _quality_height(quality: str) -> str:
        return "".join(ch for ch in quality if ch.isdigit()) or "1080"

    @staticmethod
    def _quality_bitrate(quality: str) -> str:
        return "".join(ch for ch in quality if ch.isdigit()) or "320"
