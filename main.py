import customtkinter
import yt_dlp
from pathlib import Path
import threading
import re
import shutil
import os
import platform
import subprocess

cancelar_download = False
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- Janela ---
app = customtkinter.CTk()
app.geometry("750x600")  # um pouco maior pra caber o botão novo
app.title("Baixador Simplificado")

# Widgets principais
titulo_label = customtkinter.CTkLabel(app, text="Insira o link do YouTube")
titulo_label.pack(padx=10, pady=10)

link_entry = customtkinter.CTkEntry(app, placeholder_text="Cole seu link aqui...", width=500, height=30)
link_entry.pack(padx=10, pady=10)

# ComboBox de formatos fixos
formatos = ["MP3 128k", "MP4 480p", "MP4 720p", "MP4 1080p", "AVI", "MKV"]
formato_combo = customtkinter.CTkComboBox(app, values=formatos, state="normal")
formato_combo.set(formatos[0])
formato_combo.pack(padx=10, pady=10)

# Botões de controle
botao_frame = customtkinter.CTkFrame(app)
botao_frame.pack(padx=10, pady=10)

download_button = customtkinter.CTkButton(botao_frame, text="Baixar")
download_button.pack(side="left", padx=5)

cancel_button = customtkinter.CTkButton(botao_frame, text="Cancelar", fg_color="red", hover_color="#aa0000", state="disabled")
cancel_button.pack(side="left", padx=5)

# Barra de progresso
progress_bar = customtkinter.CTkProgressBar(app, width=500)
progress_bar.set(0)
progress_bar.pack(padx=10, pady=10)

status_detalhado_label = customtkinter.CTkLabel(app, text="")
status_detalhado_label.pack(padx=10, pady=5)

status_label = customtkinter.CTkLabel(app, text="")
status_label.pack(padx=10, pady=5)

# Botão para abrir a pasta (começa invisível)
def abrir_pasta_downloads():
    pasta = Path.home() / "Downloads"
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(pasta)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", pasta])
        else:  # Linux e outros
            subprocess.run(["xdg-open", pasta])
    except Exception as e:
        update_ui_safe(status_label.configure, text=f"Erro ao abrir pasta: {e}", text_color="red")

abrir_pasta_button = customtkinter.CTkButton(app, text="Abrir Pasta de Downloads", command=abrir_pasta_downloads)
abrir_pasta_button.pack(pady=10)
abrir_pasta_button.configure(state="disabled")  # desabilitado até terminar o download

# --- Funções auxiliares ---
def update_ui_safe(func, *args, **kwargs):
    app.after(0, lambda: func(*args, **kwargs))

def meu_hook_de_progresso(d):
    global cancelar_download
    if cancelar_download:
        raise yt_dlp.utils.DownloadError("Download cancelado pelo usuário.")
    if d['status'] == 'downloading':
        porc_raw = d.get('_percent_str', '0%')
        porc_limpa = ansi_escape.sub('', porc_raw).strip()
        try:
            porc_float = float(porc_limpa.replace('%', '')) / 100
            update_ui_safe(progress_bar.set, porc_float)
            update_ui_safe(status_detalhado_label.configure, text=f"Baixando... {porc_limpa}")
        except Exception:
            pass
    elif d['status'] == 'finished':
        update_ui_safe(progress_bar.set, 1)
        update_ui_safe(status_detalhado_label.configure, text="Finalizando...")

def fazer_download():
    global cancelar_download
    cancelar_download = False
    update_ui_safe(abrir_pasta_button.configure, state="disabled")

    link = link_entry.get().strip()
    formato = formato_combo.get()

    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', link):
        update_ui_safe(status_label.configure, text="Erro: link inválido.", text_color="red")
        return

    update_ui_safe(status_label.configure, text="", text_color="white")
    update_ui_safe(progress_bar.set, 0)
    update_ui_safe(cancel_button.configure, state="normal")
    update_ui_safe(download_button.configure, state="disabled")

    try:
        pasta_downloads = Path.home() / "Downloads"
        if formato.startswith("MP4"):
            resolucao = formato.split()[1].replace("p", "")
            fmt_str = f"bestvideo[ext=mp4][height<={resolucao}]+bestaudio[ext=m4a]/best[ext=mp4]"
            post = []
        elif formato == "AVI":
            fmt_str = "bestvideo+bestaudio/best"
            post = [{"key": "FFmpegVideoConvertor", "preferedformat": "avi"}]
        elif formato == "MKV":
            fmt_str = "bestvideo+bestaudio/best"
            post = [{"key": "FFmpegVideoConvertor", "preferedformat": "mkv"}]
        elif formato == "MP3 128k":
            fmt_str = "bestaudio/best"
            post = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}]
        else:
            fmt_str = "best"
            post = []

        ydl_opts = {
            "format": fmt_str,
            "postprocessors": post,
            "outtmpl": str(pasta_downloads / "%(title).200B.%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [meu_hook_de_progresso],
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])

        update_ui_safe(status_label.configure, text="Download concluído com sucesso!", text_color="green")
        update_ui_safe(status_detalhado_label.configure, text="Arquivo salvo em Downloads")
        update_ui_safe(abrir_pasta_button.configure, state="normal")  # libera botão
    except yt_dlp.utils.DownloadError as e:
        update_ui_safe(status_label.configure, text=str(e), text_color="orange")
    except Exception as e:
        update_ui_safe(status_label.configure, text=f"Erro durante o download: {e}", text_color="red")
    finally:
        update_ui_safe(download_button.configure, state="normal")
        update_ui_safe(cancel_button.configure, state="disabled")

def iniciar_download():
    threading.Thread(target=fazer_download, daemon=True).start()

def cancelar_download_func():
    global cancelar_download
    cancelar_download = True
    update_ui_safe(status_detalhado_label.configure, text="Cancelando download...")

# Liga botões
download_button.configure(command=iniciar_download)
cancel_button.configure(command=cancelar_download_func)

# --- Motor ---
app.mainloop()
