import os
import platform
import re
import shutil
import subprocess
import sys
import threading
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter
import requests
import yt_dlp
from PIL import Image

from .config import DEFAULT_DOWNLOAD_PATH, FFMPEG_LOCATION
from .downloader import DownloadError, YTDownloader
from .history import HistoryDB
from .validators import is_valid_folder_path, is_valid_youtube_url

customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("dark-blue")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class App:
    def __init__(self):
        self.window = customtkinter.CTk()
        self.window.title("Downloader YouTube - MP3/MP4")
        self.window.geometry("540x640")
        self.window.resizable(False, False)

        self.downloader = YTDownloader()
        self.history_db = HistoryDB()
        self.current_video_info = None
        self.download_cancelled = False
        self.thumbnail_image = None
        self.ffmpeg_available = (FFMPEG_LOCATION / "ffmpeg.exe").exists() or shutil.which("ffmpeg") is not None

        self._build_ui()

        if not self.ffmpeg_available:
            path_text = str(FFMPEG_LOCATION)
            self.set_status(f"Aviso: FFmpeg não encontrado em {path_text}. Instale-o para converter MP3/MP4 corretamente.")
            self.window.after(200, lambda: messagebox.showwarning(
                "FFmpeg ausente",
                f"O FFmpeg não foi encontrado em {path_text}.\nInstale-o em {path_text} ou adicione-o ao PATH.",
            ))

    def _build_ui(self):
        customtkinter.CTkLabel(self.window, text="Downloader YouTube", font=(None, 24, "bold")).pack(padx=16, pady=(16, 8))

        self.url_entry = customtkinter.CTkEntry(self.window, placeholder_text="Cole o link do YouTube aqui...")
        self.url_entry.pack(fill="x", padx=16, pady=(0, 10))
        self.url_entry.bind("<Return>", lambda event: self.fetch_info())

        self.fetch_button = customtkinter.CTkButton(self.window, text="Buscar informações", command=self.fetch_info)
        self.fetch_button.pack(fill="x", padx=16, pady=(0, 10))

        self.video_frame = customtkinter.CTkFrame(self.window)
        self.video_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.thumbnail_label = customtkinter.CTkLabel(self.video_frame, text="Sem thumbnail", width=120, height=68)
        self.thumbnail_label.pack(side="left", padx=(0, 10), pady=10)

        info_text_frame = customtkinter.CTkFrame(self.video_frame)
        info_text_frame.pack(side="left", fill="x", expand=True, pady=10)

        self.info_label = customtkinter.CTkLabel(info_text_frame, text="Título do vídeo aparecerá aqui.", wraplength=360, justify="left")
        self.info_label.pack(fill="x", pady=(0, 4))

        self.duration_label = customtkinter.CTkLabel(info_text_frame, text="Duração: --:--", wraplength=360, justify="left", font=(None, 12))
        self.duration_label.pack(fill="x")

        options_frame = customtkinter.CTkFrame(self.window)
        options_frame.pack(fill="x", padx=16, pady=(0, 10))

        customtkinter.CTkLabel(options_frame, text="Formato:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=8)
        self.format_combo = customtkinter.CTkComboBox(
            options_frame,
            values=YTDownloader.get_format_choices(),
            width=220,
        )
        self.format_combo.set(YTDownloader.get_format_choices()[0])
        self.format_combo.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.allow_playlist_var = customtkinter.BooleanVar(value=False)
        self.allow_playlist_switch = customtkinter.CTkCheckBox(
            options_frame,
            text="Permitir playlist",
            variable=self.allow_playlist_var,
            onvalue=True,
            offvalue=False,
        )
        self.allow_playlist_switch.grid(row=1, column=0, columnspan=2, sticky="w", padx=(0, 8), pady=(0, 8))

        path_frame = customtkinter.CTkFrame(self.window)
        path_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.destination_var = customtkinter.StringVar(value=str(DEFAULT_DOWNLOAD_PATH))
        self.destination_entry = customtkinter.CTkEntry(path_frame, textvariable=self.destination_var)
        self.destination_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=8)
        path_frame.grid_columnconfigure(0, weight=1)

        self.browse_button = customtkinter.CTkButton(path_frame, text="Escolher pasta", command=self.choose_folder)
        self.browse_button.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.status_label = customtkinter.CTkLabel(self.window, text="Pronto para começar", anchor="w")
        self.status_label.pack(fill="x", padx=16, pady=(0, 8))

        self.progress_bar = customtkinter.CTkProgressBar(self.window)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))

        buttons_frame = customtkinter.CTkFrame(self.window)
        buttons_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.download_button = customtkinter.CTkButton(buttons_frame, text="Baixar", command=self.start_download, state="disabled")
        self.download_button.grid(row=0, column=0, padx=(0, 8), pady=8)

        self.cancel_button = customtkinter.CTkButton(buttons_frame, text="Cancelar", command=self.cancel_download, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.open_folder_button = customtkinter.CTkButton(buttons_frame, text="Abrir pasta", command=self.open_destination_folder, state="disabled")
        self.open_folder_button.grid(row=0, column=2, padx=(0, 8), pady=8)

        self.history_button = customtkinter.CTkButton(buttons_frame, text="Histórico", command=self.show_history)
        self.history_button.grid(row=0, column=3, padx=(0, 8), pady=8)

        self.update_button = customtkinter.CTkButton(buttons_frame, text="Atualizar yt-dlp", command=self.update_ytdlp)
        self.update_button.grid(row=1, column=0, columnspan=4, sticky="ew", padx=(0, 8), pady=(0, 8))

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not is_valid_youtube_url(url):
            self.set_status("Link inválido. Cole um link do YouTube.")
            self.download_button.configure(state="disabled")
            return

        self.set_status("Buscando informações...")
        self.download_button.configure(state="disabled")
        self.info_label.configure(text="Buscando título...")
        self.duration_label.configure(text="Duração: --:--")
        self.thumbnail_label.configure(image=None, text="Sem thumbnail")
        self.thumbnail_image = None

        thread = threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True)
        thread.start()

    def _fetch_info_thread(self, url: str):
        try:
            allow_playlist = self.allow_playlist_var.get()
            self.downloader.allow_playlist = allow_playlist
            info = self.downloader.get_video_info(url)
            self.current_video_info = info

            title = info.get("title", "Título não disponível")
            subtitle = title
            if info.get("_type") == "playlist":
                total = len(info.get("entries", []))
                subtitle = f"Playlist detectada ({total} vídeos): {title}"
                duration_text = f"Playlist com {total} vídeos"
                if not allow_playlist:
                    self.set_status("Playlist detectada. Ative 'Permitir playlist' para baixar.")
                    self.download_button.configure(state="disabled")
                    self._update_info_label(subtitle)
                    self._update_duration_label(duration_text)
                    return
            else:
                duration_text = self._format_duration(info.get("duration"))

            already_downloaded = self.history_db.video_downloaded(url)
            if already_downloaded:
                self.set_status("Este vídeo já foi baixado anteriormente.")
                self.download_button.configure(state="disabled")
            else:
                self.set_status("Pronto para baixar")
                self.download_button.configure(state="normal")

            self._update_info_label(subtitle)
            self._update_duration_label(duration_text)
            self._load_thumbnail(info.get("thumbnail"))
        except Exception as error:
            self.set_status(f"Erro ao buscar informações: {error}")
            self.download_button.configure(state="disabled")

    def _update_info_label(self, text: str):
        self.window.after(0, lambda: self.info_label.configure(text=text))

    def _update_duration_label(self, text: str):
        self.window.after(0, lambda: self.duration_label.configure(text=f"Duração: {text}"))

    def _format_duration(self, seconds: Optional[int]) -> str:
        if not seconds or seconds <= 0:
            return "--:--"
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:d}:{seconds:02d}"

    def _clean_text(self, value: Optional[str]) -> str:
        if not value:
            return ""
        text = ANSI_ESCAPE_RE.sub("", str(value))
        text = text.replace("\r", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _format_speed(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            cleaned = self._clean_text(value)
            return cleaned
        try:
            speed = float(value)
        except (TypeError, ValueError):
            return ""
        if speed <= 0:
            return ""
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        index = 0
        while speed >= 1024 and index < len(units) - 1:
            speed /= 1024
            index += 1
        return f"{speed:.1f} {units[index]}"

    def _progress_hook(self, data: dict):
        if self.download_cancelled:
            raise yt_dlp.utils.DownloadError("Download cancelado pelo usuário.")

        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            percent = 0.0
            if total and total > 0:
                percent = min(max(downloaded / total, 0.0), 1.0)

            self.window.after(0, lambda: self.progress_bar.set(percent))

            percent_text = f"{percent * 100:.1f}%"
            speed_text = self._format_speed(data.get("speed"))
            status_text = f"Baixando... {percent_text}"
            if speed_text:
                status_text = f"{status_text} | {speed_text}"

            self.window.after(0, lambda: self.status_label.configure(text=status_text))
        elif status == "finished":
            self.window.after(0, lambda: self.progress_bar.set(1.0))
            self.window.after(0, lambda: self.status_label.configure(text="Download concluído"))
        elif status == "error":
            self.window.after(0, lambda: self.status_label.configure(text="Erro no download"))

    def _load_thumbnail(self, thumbnail_url: str):
        if not thumbnail_url:
            return
        try:
            response = requests.get(thumbnail_url, timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            self.thumbnail_image = customtkinter.CTkImage(light_image=image, dark_image=image, size=(120, 68))
            self.window.after(0, lambda: self.thumbnail_label.configure(image=self.thumbnail_image, text=""))
        except Exception:
            self.window.after(0, lambda: self.thumbnail_label.configure(text="Thumbnail indisponível"))

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.destination_var.get())
        if folder:
            self.destination_var.set(folder)

    def start_download(self):
        url = self.url_entry.get().strip()
        destination = self.destination_var.get().strip()
        format_label = self.format_combo.get()
        allow_playlist = self.allow_playlist_var.get()

        if not is_valid_youtube_url(url):
            self.set_status("Link inválido. Cole um link do YouTube.")
            return

        if not is_valid_folder_path(destination):
            self.set_status("Pasta de destino inválida. Escolha outra pasta.")
            return

        if format_label.startswith("MP3") and not self.ffmpeg_available:
            messagebox.showerror(
                "FFmpeg ausente",
                "FFmpeg é necessário para baixar MP3. Instale o FFmpeg e reinicie o aplicativo.",
            )
            self.set_status("Instale o FFmpeg antes de baixar MP3.")
            return

        if self.history_db.video_downloaded(url):
            messagebox.showinfo(
                "Já baixado",
                "Esse vídeo já foi baixado anteriormente. Evitando duplicação.",
            )
            self.set_status("Download evitado: vídeo já baixado.")
            return

        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.open_folder_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.download_cancelled = False
        self.set_status("Iniciando download...")

        thread = threading.Thread(
            target=self._download_thread,
            args=(url, Path(destination), format_label, allow_playlist),
            daemon=True,
        )
        thread.start()

    def _download_thread(self, url: str, destination: Path, format_label: str, allow_playlist: bool):
        try:
            format_key = YTDownloader.format_key_from_label(format_label)
            info = self.downloader.download(
                url=url,
                output_folder=destination,
                format_key=format_key,
                allow_playlist=allow_playlist,
                progress_hook=self._progress_hook,
            )
            title = info.get("title") or url
            self.history_db.save_record(
                url=url,
                title=title,
                output_format=format_label,
                output_path=str(destination),
            )
            self.set_status("Download concluído com sucesso.")
            self.open_folder_button.configure(state="normal")
        except Exception as error:
            message = str(error)
            if "ffmpeg" in message.lower():
                message = "Erro: FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH."
                self.window.after(0, lambda: messagebox.showerror("Erro FFmpeg", message))
            self.set_status(f"Erro no download: {message}")
        finally:
            self.window.after(0, lambda: self.download_button.configure(state="normal"))
            self.window.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def update_ytdlp(self):
        self.update_button.configure(state="disabled")
        self.set_status("Atualizando yt-dlp...")
        threading.Thread(target=self._update_ytdlp_thread, daemon=True).start()

    def _update_ytdlp_thread(self):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.set_status("yt-dlp atualizado com sucesso.")
                self.window.after(0, lambda: messagebox.showinfo("Atualização", "yt-dlp atualizado com sucesso."))
            else:
                stderr = result.stderr.strip() or result.stdout.strip()
                self.set_status("Falha ao atualizar yt-dlp.")
                self.window.after(0, lambda: messagebox.showerror("Erro", f"Não foi possível atualizar yt-dlp.\n{stderr}"))
        except Exception as error:
            self.set_status(f"Erro ao atualizar yt-dlp: {error}")
            self.window.after(0, lambda: messagebox.showerror("Erro", f"Erro ao atualizar yt-dlp:\n{error}"))
        finally:
            self.window.after(0, lambda: self.update_button.configure(state="normal"))

    def cancel_download(self):
        self.download_cancelled = True
        self.set_status("Cancelando download...")

    def open_destination_folder(self):
        destination = self.destination_var.get().strip()
        if not is_valid_folder_path(destination):
            self.set_status("Pasta de destino inválida.")
            return

        if platform.system() == "Windows":
            os.startfile(destination)
        elif platform.system() == "Darwin":
            os.system(f"open \"{destination}\"")
        else:
            os.system(f"xdg-open \"{destination}\"")

    def show_history(self):
        records = self.history_db.get_recent(10)
        if not records:
            messagebox.showinfo("Histórico", "Nenhum download registrado ainda.")
            return

        lines = [
            f"{rec['created_at']} - {rec['title']} ({rec['output_format']})\n{rec['output_path']}\n"
            for rec in records
        ]
        messagebox.showinfo("Histórico", "\n".join(lines))

    def set_status(self, text: str):
        self.window.after(0, lambda: self.status_label.configure(text=text))

    def run(self):
        self.window.mainloop()


def run_app() -> None:
    app = App()
    app.run()
