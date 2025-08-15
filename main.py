import customtkinter
from pathlib import Path
import threading
import yt_dlp
from PIL import Image, ImageTk
import requests
from io import BytesIO
import re
import queue
import os
import platform
import subprocess

customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("dark-blue")

app = customtkinter.CTk()
app.geometry("500x600")
app.title("Baixador Fluido")

# --- Variáveis ---
log_queue = queue.Queue()
cancelar_download = False
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- Frames ---
# Entrada do link
frame_link = customtkinter.CTkFrame(app)
frame_link.pack(fill="x", padx=10, pady=5)

label_link = customtkinter.CTkLabel(frame_link, text="Cole o link do YouTube")
label_link.pack(anchor="w", pady=2)

link_entry = customtkinter.CTkEntry(frame_link, placeholder_text="Cole seu link aqui...")
link_entry.pack(fill="x", pady=2)

# Informações do vídeo
frame_info = customtkinter.CTkFrame(app)
frame_info.pack(fill="x", padx=10, pady=5)

thumbnail_label = customtkinter.CTkLabel(frame_info, text="")
thumbnail_label.pack(side="left", padx=5, pady=5)

video_title_label = customtkinter.CTkLabel(frame_info, text="Título do vídeo")
video_title_label.pack(side="left", padx=5, pady=5)

# Opções de download
frame_opcoes = customtkinter.CTkFrame(app)
frame_opcoes.pack(fill="x", padx=10, pady=5)

formatos = ["MP3 128k", "MP4 480p", "MP4 720p", "MP4 1080p", "AVI", "MKV"]
formato_combo = customtkinter.CTkComboBox(frame_opcoes, values=formatos)
formato_combo.set(formatos[2])
formato_combo.pack(side="left", padx=5, pady=5)

# Barra de progresso
progress_bar = customtkinter.CTkProgressBar(app)
progress_bar.pack(fill="x", padx=10, pady=5)
progress_bar.set(0)

# Botões
frame_botoes = customtkinter.CTkFrame(app)
frame_botoes.pack(fill="x", padx=10, pady=5)

download_button = customtkinter.CTkButton(frame_botoes, text="Baixar", state="disabled")
download_button.pack(side="left", padx=5, pady=5)

cancel_button = customtkinter.CTkButton(frame_botoes, text="Cancelar", state="disabled")
cancel_button.pack(side="left", padx=5, pady=5)

abrir_pasta_button = customtkinter.CTkButton(frame_botoes, text="Abrir Pasta", state="disabled")
abrir_pasta_button.pack(side="left", padx=5, pady=5)

# Status centralizado
status_label = customtkinter.CTkLabel(app, text="Pronto")
status_label.pack(fill="x", padx=10, pady=5)

# --- Funções ---
def update_ui_safe(func, *args, **kwargs):
    app.after(0, lambda: func(*args, **kwargs))

def buscar_info_video():
    link = link_entry.get().strip()
    if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', link):
        update_ui_safe(status_label.configure, text="Link inválido")
        update_ui_safe(download_button.configure, state="disabled")
        return

    update_ui_safe(status_label.configure, text="Buscando informações...")
    update_ui_safe(download_button.configure, state="disabled")
    update_ui_safe(video_title_label.configure, text="")
    update_ui_safe(thumbnail_label.configure, image=None, text="")

    def worker():
        try:
            ydl_opts = {"quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                titulo = info.get("title", "Sem título")
                thumb_url = info.get("thumbnail", "")

                update_ui_safe(video_title_label.configure, text=titulo)

                if thumb_url:
                    try:
                        response = requests.get(thumb_url, timeout=2)
                        image = Image.open(BytesIO(response.content)).resize((120,68))
                        thumb_imgtk = ImageTk.PhotoImage(image)
                        update_ui_safe(thumbnail_label.configure, image=thumb_imgtk, text="")
                        thumbnail_label.image = thumb_imgtk
                    except:
                        update_ui_safe(thumbnail_label.configure, text="Thumbnail não disponível")

                update_ui_safe(download_button.configure, state="normal")
                update_ui_safe(status_label.configure, text="Pronto para baixar")
        except:
            update_ui_safe(status_label.configure, text="Erro ao buscar vídeo")
            update_ui_safe(download_button.configure, state="disabled")

    threading.Thread(target=worker, daemon=True).start()

def meu_hook_de_progresso(d):
    global cancelar_download
    if cancelar_download:
        raise yt_dlp.utils.DownloadError("Download cancelado pelo usuário.")

    if d.get("status") == "downloading":
        porc_raw = d.get("_percent_str", "0%")
        porc_limpa = ansi_escape.sub("", porc_raw).strip()  # limpa códigos ANSI

        velocidade_raw = d.get("_speed_str", "0 B/s")
        velocidade_limpa = ansi_escape.sub("", velocidade_raw).strip()

        try:
            porc_float = float(porc_limpa.replace("%","")) / 100
            update_ui_safe(progress_bar.set, porc_float)
            update_ui_safe(status_label.configure, text=f"Baixando... {porc_limpa} | {velocidade_limpa}")
        except ValueError:
            # caso não consiga converter, ignora para não travar
            pass

    elif d.get("status") == "finished":
        update_ui_safe(progress_bar.set, 1)
        update_ui_safe(status_label.configure, text="Finalizando arquivo...")


def fazer_download():
    global cancelar_download
    cancelar_download = False
    update_ui_safe(progress_bar.set, 0)
    update_ui_safe(cancel_button.configure, state="normal")
    update_ui_safe(download_button.configure, state="disabled")
    update_ui_safe(abrir_pasta_button.configure, state="disabled")

    link = link_entry.get().strip()
    formato = formato_combo.get()
    pasta_downloads = Path.home() / "Downloads"

    if formato.startswith("MP4"):
        resolucao = formato.split()[1].replace("p","")
        fmt_str = f"bestvideo[ext=mp4][height<={resolucao}]+bestaudio[ext=m4a]/best[ext=mp4]"
        post = []
    elif formato == "AVI":
        fmt_str = "bestvideo+bestaudio/best"
        post = [{"key":"FFmpegVideoConvertor","preferedformat":"avi"}]
    elif formato == "MKV":
        fmt_str = "bestvideo+bestaudio/best"
        post = [{"key":"FFmpegVideoConvertor","preferedformat":"mkv"}]
    elif formato == "MP3 128k":
        fmt_str = "bestaudio/best"
        post = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"128"}]
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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])

        update_ui_safe(status_label.configure, text="Download concluído!")
        update_ui_safe(abrir_pasta_button.configure, state="normal")
    except Exception as e:
        update_ui_safe(status_label.configure, text=f"Erro: {e}")
    finally:
        update_ui_safe(download_button.configure, state="normal")
        update_ui_safe(cancel_button.configure, state="disabled")

def iniciar_download():
    threading.Thread(target=fazer_download, daemon=True).start()

def cancelar_download_func():
    global cancelar_download
    cancelar_download = True
    update_ui_safe(status_label.configure, text="Cancelando download...")

def abrir_pasta():
    downloads = Path.home() / "Downloads"
    if platform.system() == "Windows":
        os.startfile(downloads)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", downloads])
    else:
        subprocess.Popen(["xdg-open", downloads])

# --- Bindings ---
link_entry.bind("<KeyRelease>", lambda e: buscar_info_video())
download_button.configure(command=iniciar_download)
cancel_button.configure(command=cancelar_download_func)
abrir_pasta_button.configure(command=abrir_pasta)

app.mainloop()
