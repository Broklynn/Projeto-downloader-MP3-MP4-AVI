import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
from .config import EXECUTABLE_ROOT, PROJECT_ROOT, FORMAT_OPTIONS


class DownloadError(Exception):
    pass


def get_ffmpeg_location() -> Optional[str]:
    """
    Detecta a localização do FFmpeg nesta ordem:
    1. pasta_do_exe/tools/ffmpeg/bin/ffmpeg.exe
    2. pasta_do_projeto/tools/ffmpeg/bin/ffmpeg.exe
    3. C:/ffmpeg/bin/ffmpeg.exe
    4. PATH do sistema

    Retorna o diretório onde o ffmpeg.exe está localizado, ou None se não encontrado.
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


class YTDownloader:
    def __init__(self, allow_playlist: bool = False):
        self.allow_playlist = allow_playlist

    def get_video_info(self, url: str) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            raise DownloadError(f"Erro ao obter informações: {str(e)}")

    def download(
        self,
        url: str,
        output_folder: Path,
        format_key: str,
        allow_playlist: bool,
        progress_hook=None
    ) -> dict:
        ydl_opts = self._build_ydl_options(format_key, output_folder, allow_playlist)
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        except Exception as e:
            raise DownloadError(f"Erro no download: {str(e)}")

    def _build_ydl_options(self, format_key: str, output_folder: Path, allow_playlist: bool) -> dict:
        base_opts = {
            'outtmpl': str(output_folder / '%(title)s.%(ext)s'),
            'noplaylist': not allow_playlist,
            'quiet': False,
            'no_warnings': False,
        }

        if format_key.startswith('mp4'):
            quality = format_key.split('_')[1]
            base_opts.update({
                'format': f'bestvideo[ext=mp4][height<={quality}]+bestaudio[ext=m4a]/bestvideo[height<={quality}]+bestaudio/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })
        elif format_key.startswith('mp3'):
            bitrate = format_key.split('_')[1]
            base_opts.update({
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': bitrate,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }],
            })

        self._validate_ffmpeg_location(base_opts)
        return base_opts

    def _validate_ffmpeg_if_needed(self, postprocessors: list) -> None:
        if postprocessors or any('extractaudio' in str(p) for p in postprocessors):
            ffmpeg_location = get_ffmpeg_location()
            if not ffmpeg_location:
                raise DownloadError("FFmpeg necessário para MP3/MP4. Instale em C:\\ffmpeg\\bin")

    def _validate_ffmpeg_location(self, ydl_opts: dict) -> None:
        # FFmpeg é necessário para MP4 (merge) e MP3 (extract audio)
        if 'postprocessors' in ydl_opts or 'merge_output_format' in ydl_opts:
            ffmpeg_location = get_ffmpeg_location()
            if ffmpeg_location:
                ydl_opts['ffmpeg_location'] = ffmpeg_location
                print(f"FFmpeg detectado em: {ffmpeg_location}")
            else:
                raise DownloadError("FFmpeg não encontrado. Instale em C:\\ffmpeg\\bin ou use a instalação automática.")

    @staticmethod
    def get_format_choices():
        return [label for label, key in FORMAT_OPTIONS]

    @staticmethod
    def format_key_from_label(label: str) -> str:
        for l, key in FORMAT_OPTIONS:
            if l == label:
                return key
        return "mp4_720"