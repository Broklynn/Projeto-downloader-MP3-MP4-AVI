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

from .config import DEFAULT_DOWNLOAD_PATH, ConfigManager
from .downloader import DownloadError, YTDownloader, get_ffmpeg_location
from .history import HistoryDB
from .validators import is_valid_folder_path, is_valid_url
from .update_checker import UpdateChecker

customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("dark-blue")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class App:
    def __init__(self):
        self.config_manager = ConfigManager()
        customtkinter.set_appearance_mode(self.config_manager.get_appearance_mode())
        customtkinter.set_default_color_theme("dark-blue")
        self.window = customtkinter.CTk()
        self.window.title("Downloader YouTube - MP3/MP4")
        self.window.geometry("560x660")
        self.window.minsize(560, 660)
        self.window.resizable(False, False)

        self.downloader = YTDownloader()
        self.history_db = HistoryDB()
        self.current_video_info = None
        self.download_cancelled = False
        self.thumbnail_image = None
        self.ffmpeg_available = get_ffmpeg_location() is not None

        # Verificador de atualização
        self.update_checker = UpdateChecker()
        self.update_info = None
        self.update_button = None

        self._build_ui()

        # Verificar atualizações em segundo plano
        self._check_for_updates_async()

        if not self.ffmpeg_available:
            self.set_status(
                "Aviso: FFmpeg não encontrado. Coloque tools/ffmpeg/bin/ffmpeg.exe ao lado do executável "
                "ou instale em C:\\ffmpeg\\bin, ou deixe ffmpeg disponível no PATH."
            )

    def _build_ui(self):
        customtkinter.CTkLabel(self.window, text="Downloader YouTube", font=(None, 24, "bold")).pack(padx=16, pady=(16, 8))

        self.url_entry = customtkinter.CTkEntry(self.window, placeholder_text="Cole o link (YouTube, Instagram, TikTok...)")
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

        self.destination_var = customtkinter.StringVar(value=self.config_manager.get_last_download_path())
        self.destination_entry = customtkinter.CTkEntry(path_frame, textvariable=self.destination_var)
        self.destination_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=8)
        path_frame.grid_columnconfigure(0, weight=1)

        self.browse_button = customtkinter.CTkButton(path_frame, text="Escolher pasta", command=self.choose_folder)
        self.browse_button.grid(row=0, column=1, padx=(0, 8), pady=8)

        self.status_label = customtkinter.CTkLabel(self.window, text="Pronto para começar", anchor="w")
        self.status_label.pack(fill="x", padx=16, pady=(0, 8))

        self.toast_label = customtkinter.CTkLabel(self.window, text="", anchor="center", fg_color="#2E8B57", text_color="white", corner_radius=8)
        self.toast_label.pack(fill="x", padx=16, pady=(0, 8))
        self.toast_label.pack_forget()  # Esconder inicialmente

        self.progress_bar = customtkinter.CTkProgressBar(self.window)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))

        self.button_frame = customtkinter.CTkFrame(self.window)
        self.button_frame.pack(fill="x", padx=16, pady=(0, 16))
        for index in range(6):  # Aumentado para 6 colunas
            self.button_frame.grid_columnconfigure(index, weight=1)

        self.download_button = customtkinter.CTkButton(self.button_frame, text="Baixar", command=self.start_download, state="disabled")
        self.download_button.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=8)

        self.open_folder_button = customtkinter.CTkButton(self.button_frame, text="Abrir pasta", command=self.open_destination_folder, state="disabled")
        self.open_folder_button.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)

        self.history_button = customtkinter.CTkButton(self.button_frame, text="Histórico", command=self.show_history)
        self.history_button.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=8)

        self.theme_button = customtkinter.CTkButton(self.button_frame, text="Tema", command=self.toggle_theme)
        self.theme_button.grid(row=0, column=3, sticky="ew", padx=(0, 8), pady=8)

        self.update_ytdlp_button = customtkinter.CTkButton(self.button_frame, text="Atualizar yt-dlp", command=self.update_ytdlp)
        self.update_ytdlp_button.grid(row=0, column=4, sticky="ew", padx=(0, 8), pady=8)

        self.history_scrollable = customtkinter.CTkScrollableFrame(self.window, height=200)
        self.history_scrollable.pack(fill="x", padx=16, pady=(0, 16))
        self.history_scrollable.grid_columnconfigure(0, weight=1)

        self._show_history_placeholder()

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not is_valid_url(url):
            self.set_status("Link inválido. Cole uma URL válida.")
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

            self.set_status("Pronto para baixar")
            self.download_button.configure(state="normal")
            self._update_info_label(subtitle)
            self._update_duration_label(duration_text)
            self._load_thumbnail(info.get("thumbnail"))
        except Exception as error:
            self.set_status(self._format_yt_dlp_error(error, context="info"))
            self.download_button.configure(state="disabled")

    def _format_yt_dlp_error(self, error: Exception, context: str = "download") -> str:
        message = str(error)
        lower = message.lower()

        if "unsupported url" in lower or "unable to download webpage" in lower or "unsupported" in lower:
            return "Plataforma não suportada ou URL inválida. Cole um link de site suportado pelo yt-dlp."
        if "private" in lower or "não disponível" in lower or "restrito" in lower or "blocked" in lower:
            return "Conteúdo privado ou restrito. Verifique se o vídeo está disponível publicamente."
        if "forbidden" in lower or "403" in lower:
            return "Acesso negado ao conteúdo. Pode ser vídeo privado ou bloqueado."
        if "404" in lower or "not found" in lower:
            return "Conteúdo não encontrado. Verifique a URL e tente novamente."
        if "no video formats found" in lower or "unable to extract" in lower:
            return "Não foi possível extrair informações do link. Pode ser uma plataforma ou formato não suportado."

        return message

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
            self.config_manager.set_last_download_path(folder)

    def start_download(self):
        url = self.url_entry.get().strip()
        destination = self.destination_var.get().strip()
        format_label = self.format_combo.get()
        allow_playlist = self.allow_playlist_var.get()

        if not is_valid_url(url):
            self.set_status("Link inválido. Cole uma URL válida.")
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

        self.download_button.configure(state="disabled")
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
            self.show_toast("Download concluído com sucesso!")
            self.open_folder_button.configure(state="normal")
        except Exception as error:
            message = self._format_yt_dlp_error(error, context="download")
            self.set_status(f"Erro no download: {message}")
        finally:
            self.window.after(0, lambda: self.download_button.configure(state="normal"))

    def update_ytdlp(self):
        self.update_ytdlp_button.configure(state="disabled")
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
            self.window.after(0, lambda: self.update_ytdlp_button.configure(state="normal"))

    def show_toast(self, message, duration=3000):
        self.toast_label.configure(text=message)
        self.toast_label.pack(fill="x", padx=16, pady=(0, 8))
        self.window.after(duration, lambda: self.toast_label.pack_forget())

    def copy_path_to_clipboard(self, path):
        self.window.clipboard_clear()
        self.window.clipboard_append(path)
        self.show_toast("Caminho copiado para a área de transferência!")

    def toggle_theme(self):
        current = customtkinter.get_appearance_mode()
        next_mode = "Light" if current == "Dark" else "Dark"
        customtkinter.set_appearance_mode(next_mode)
        self.config_manager.set_appearance_mode(next_mode)
        tema_label = "Claro" if next_mode == "Light" else "Escuro"
        self.set_status(f"Tema alterado para {tema_label}")

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
        self._display_history(records)
        if records:
            self.set_status("Histórico carregado abaixo.")
        else:
            self.set_status("Nenhum download no histórico ainda.")

    def _show_history_placeholder(self):
        self._clear_history_display()
        placeholder = customtkinter.CTkLabel(
            self.history_scrollable,
            text="Use o botão Histórico para ver downloads anteriores.",
            anchor="w",
            justify="left",
            wraplength=520,
            font=(None, 11),
        )
        placeholder.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    def _clear_history_display(self):
        for widget in self.history_scrollable.winfo_children():
            widget.destroy()

    def _display_history(self, records):
        self._clear_history_display()
        if not records:
            placeholder = customtkinter.CTkLabel(
                self.history_scrollable,
                text="Nenhum download no histórico ainda.",
                anchor="w",
                justify="left",
                wraplength=520,
                font=(None, 11),
            )
            placeholder.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return

        for index, record in enumerate(records):
            frame = customtkinter.CTkFrame(self.history_scrollable, corner_radius=12, fg_color="#252525")
            frame.grid(row=index, column=0, sticky="ew", padx=8, pady=(6, 6))
            frame.grid_columnconfigure((0, 1), weight=1)

            title = record.get("title", "Título indisponível")
            title_label = customtkinter.CTkLabel(
                frame,
                text=title,
                anchor="w",
                justify="left",
                wraplength=400,
                font=(None, 14, "bold"),
            )
            title_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

            copy_button = customtkinter.CTkButton(
                frame,
                text="Copiar",
                command=lambda path=record.get("output_path", ""): self.copy_path_to_clipboard(path),
                width=80,
                height=28,
                font=(None, 10),
            )
            copy_button.grid(row=0, column=1, sticky="e", padx=12, pady=(12, 4))

            info_text = f"{record.get('created_at', '')} • {record.get('output_format', '')}"
            info_label = customtkinter.CTkLabel(
                frame,
                text=info_text,
                anchor="w",
                justify="left",
                wraplength=500,
                font=(None, 11),
            )
            info_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 6))

            output_path = record.get("output_path", "Caminho indisponível")
            path_label = customtkinter.CTkLabel(
                frame,
                text=output_path,
                anchor="w",
                justify="left",
                wraplength=500,
                font=(None, 11),
            )
            path_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

            separator = customtkinter.CTkLabel(
                frame,
                text="",
                height=1,
                fg_color="#333333",
            )
            separator.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 0))

    def set_status(self, text: str):
        self.window.after(0, lambda: self.status_label.configure(text=text))

    def run(self):
        self.window.mainloop()

    def _check_for_updates_async(self):
        """Verifica atualizações em segundo plano sem travar a interface."""
        def callback(update_info):
            self.window.after(0, lambda: self._handle_update_check_result(update_info))

        self.update_checker.check_async(callback)

    def _handle_update_check_result(self, update_info):
        """Processa o resultado da verificação de atualização."""
        if update_info:
            self.update_info = update_info
            self._show_update_notification(update_info)
        else:
            # Se não conseguiu verificar, mostra mensagem discreta
            self.set_status("Não foi possível verificar atualizações.")

    def _show_update_notification(self, update_info):
        """Mostra notificação de atualização disponível."""
        version = update_info.get("version", "")
        self.set_status(f"Nova versão disponível: {version}")

        # Adiciona botão de atualização se não existir
        if not self.update_button:
            self.update_button = customtkinter.CTkButton(
                self.button_frame,
                text="Ver atualização",
                command=self._open_update_url,
                width=120,
                height=32,
                font=(None, 11)
            )
            self.update_button.grid(row=0, column=4, padx=(8, 0), pady=8, sticky="e")

    def _open_update_url(self):
        """Abre o navegador na URL de download da atualização."""
        if self.update_info and self.update_info.get("download_url"):
            import webbrowser
            webbrowser.open(self.update_info["download_url"])


def run_app() -> None:
    app = App()
    app.run()
