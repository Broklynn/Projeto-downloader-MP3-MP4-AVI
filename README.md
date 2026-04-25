# 🎬 Downloader YouTube - MP3/MP4

Aplicativo desktop desenvolvido em Python para download de vídeos e músicas do YouTube com interface moderna, simples e eficiente.

---

## 🚀 Funcionalidades

- 📥 Download de vídeos em MP4 (1080p, 720p, 480p)
- 🎧 Download de áudio em MP3 (320k, 192k, 128k)
- 📺 Preview com thumbnail e informações do vídeo
- 🔗 Suporte a diferentes formatos de link do YouTube
- 📜 Histórico de downloads com visual organizado
- 📁 Escolha de pasta de destino
- 🔁 Suporte a playlists (opcional)
- 🌗 Alternância de tema (claro/escuro)
- 📋 Copiar caminho dos arquivos com um clique
- ⚙️ Atualização automática do yt-dlp
- 🔧 FFmpeg portátil (não precisa instalar nada)

---

## 📦 Download

👉 Baixe a versão mais recente:

🔗 https://github.com/Broklynn/Projeto-downloader-MP3-MP4-AVI/releases

---

## 🛠️ Como usar

1. Baixe o arquivo `.zip`
2. Extraia a pasta
3. Execute:



---

## ⚠️ Importante

Mantenha a estrutura de pastas:

```
tools/ffmpeg/bin/
```

O aplicativo utiliza FFmpeg para processar áudio e vídeo.

---

## ⚠️ Aviso do Windows

Como o executável não possui assinatura digital, o Windows pode exibir um aviso.

👉 Clique em: Mais informações → Executar mesmo assim


---

## 💻 Tecnologias utilizadas

- Python
- CustomTkinter
- yt-dlp
- FFmpeg
- SQLite
- PyInstaller

---

## 🧠 Arquitetura do projeto

src/
├── app.py
├── downloader.py
├── validators.py
├── history.py
├── config.py
├── update_checker.py
└── version.py

main.py
build.bat



---

## 🎯 Objetivo do projeto

Este projeto foi desenvolvido com foco em:

- Criar uma aplicação desktop funcional e distribuível
- Aplicar boas práticas de organização de código
- Trabalhar com integração de ferramentas externas (FFmpeg, yt-dlp)
- Melhorar a experiência do usuário (UX)

---

## 📌 Diferenciais

- Aplicação real com distribuição via `.exe`
- Interface moderna com CustomTkinter
- Suporte a múltiplos formatos de link do YouTube
- Histórico persistente com SQLite
- Sistema de atualização integrado
- Estrutura organizada em módulos

---

## 👨‍💻 Autor

Desenvolvido por **Murdoc**



