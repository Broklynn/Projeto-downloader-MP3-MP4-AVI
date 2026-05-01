from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
import yt_dlp
from PIL import Image

from .download_service import DownloadError

THUMBNAIL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

TITLE_FALLBACK = "Sem título"
DURATION_FALLBACK = "Duração indisponível"
UPLOADER_FALLBACK = "Desconhecido"


@dataclass(frozen=True)
class PreviewResult:
    info: Dict[str, Any]
    title: str
    subtitle: str
    duration_text: str
    thumbnail_url: Optional[str]
    uploader: str
    extractor: str
    platform: str
    is_playlist: bool
    entry_count: int
    can_download: bool
    status_message: str
    error_type: Optional[str] = None


class PreviewService:
    def fetch_preview(self, url: str, allow_playlist: bool) -> PreviewResult:
        try:
            info = self.fetch_info(url, allow_playlist=allow_playlist)
            return self._build_preview_result(info, allow_playlist, url)
        except Exception as error:
            return self._build_error_result(url, error)

    def fetch_info(self, url: str, allow_playlist: bool = False) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": not allow_playlist,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                return info or {}
        except Exception as e:
            raise DownloadError(f"Erro ao obter informações: {str(e)}")

    def load_thumbnail_image(self, thumbnail_url: Optional[str]) -> Optional[Image.Image]:
        if not self._is_valid_thumbnail_url(thumbnail_url):
            return None

        url = str(thumbnail_url).strip()
        try:
            response = requests.get(url, headers=THUMBNAIL_HEADERS, timeout=8)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except (requests.RequestException, OSError):
            return None

    def _build_preview_result(self, info: Dict[str, Any], allow_playlist: bool, url: str = "") -> PreviewResult:
        safe_info = info if isinstance(info, dict) else {}
        title = self._clean_field(safe_info.get("title"), TITLE_FALLBACK)
        is_playlist = safe_info.get("_type") == "playlist"
        thumbnail_url = self._resolve_thumbnail_url(safe_info)
        uploader = self._clean_field(safe_info.get("uploader") or safe_info.get("channel"), UPLOADER_FALLBACK)
        extractor = self._clean_field(safe_info.get("extractor") or safe_info.get("extractor_key"), "")
        platform = self._detect_platform(url, safe_info)

        if is_playlist:
            entry_count = len(safe_info.get("entries") or [])
            subtitle = f"Playlist detectada ({entry_count} vídeos): {title}"
            duration_text = f"Playlist com {entry_count} vídeos"
            can_download = allow_playlist
            status_message = (
                "Pronto para baixar"
                if allow_playlist
                else "Playlist detectada. Ative 'Permitir playlist' para baixar."
            )
        else:
            entry_count = 0
            subtitle = title
            duration_text = self._format_duration(safe_info.get("duration"))
            can_download = True
            status_message = "Pronto para baixar"

        return PreviewResult(
            info=safe_info,
            title=title,
            subtitle=subtitle,
            duration_text=duration_text,
            thumbnail_url=thumbnail_url,
            uploader=uploader,
            extractor=extractor,
            platform=platform,
            is_playlist=is_playlist,
            entry_count=entry_count,
            can_download=can_download,
            status_message=status_message,
        )

    def _build_error_result(self, url: str, error: Exception) -> PreviewResult:
        error_type = self._classify_error(error)
        return PreviewResult(
            info={},
            title=TITLE_FALLBACK,
            subtitle=TITLE_FALLBACK,
            duration_text=DURATION_FALLBACK,
            thumbnail_url=None,
            uploader=UPLOADER_FALLBACK,
            extractor="",
            platform=self._detect_platform(url),
            is_playlist=False,
            entry_count=0,
            can_download=False,
            status_message=self._status_message_for_error(error_type),
            error_type=error_type,
        )

    def _resolve_thumbnail_url(self, info: Dict[str, Any]) -> Optional[str]:
        thumbnail_url = info.get("thumbnail")
        if self._is_valid_thumbnail_url(thumbnail_url):
            return str(thumbnail_url).strip()

        thumbnails = info.get("thumbnails") or []
        if not isinstance(thumbnails, list):
            return None

        for thumbnail in reversed(thumbnails):
            if not isinstance(thumbnail, dict):
                continue
            candidate_url = thumbnail.get("url")
            if self._is_valid_thumbnail_url(candidate_url):
                return str(candidate_url).strip()

        return None

    def _is_valid_thumbnail_url(self, url: Optional[str]) -> bool:
        if not url:
            return False

        try:
            parsed = urlparse(str(url).strip())
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _detect_platform(self, url: str = "", info: Optional[Dict[str, Any]] = None) -> str:
        info = info or {}
        source = " ".join(
            str(value).lower()
            for value in (
                url,
                info.get("extractor"),
                info.get("extractor_key"),
                info.get("webpage_url"),
                info.get("original_url"),
            )
            if value
        )

        if "youtu.be" in source or "youtube" in source:
            return "YouTube"
        if "tiktok" in source:
            return "TikTok"
        if "instagram" in source:
            return "Instagram"
        return "Outro"

    def _classify_error(self, error: Exception) -> str:
        message = str(error).lower()
        if (
            "unsupported url" in message
            or "invalid url" in message
            or "not a valid url" in message
            or "no suitable extractor" in message
        ):
            return "invalid_link"
        if (
            "private" in message
            or "privado" in message
            or "login" in message
            or "sign in" in message
            or "forbidden" in message
            or "403" in message
            or "restricted" in message
            or "restrito" in message
            or "blocked" in message
            or "bloqueado" in message
        ):
            return "private_content"
        if (
            "timeout" in message
            or "timed out" in message
            or "network" in message
            or "connection" in message
            or "temporary failure" in message
            or "unable to download webpage" in message
            or "http error" in message
        ):
            return "network_error"
        return "unknown_error"

    def _status_message_for_error(self, error_type: str) -> str:
        messages = {
            "invalid_link": "Link inválido ou plataforma não suportada.",
            "private_content": "Conteúdo privado, restrito ou bloqueado.",
            "network_error": "Erro de rede ao buscar informações. Verifique sua conexão e tente novamente.",
            "unknown_error": "Não foi possível buscar informações do link.",
        }
        return messages.get(error_type, messages["unknown_error"])

    def _clean_field(self, value: Any, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

    def _format_duration(self, seconds: Optional[int]) -> str:
        try:
            duration_seconds = int(seconds)
        except (TypeError, ValueError):
            return DURATION_FALLBACK
        if duration_seconds <= 0:
            return DURATION_FALLBACK
        minutes, seconds = divmod(duration_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:d}:{seconds:02d}"
