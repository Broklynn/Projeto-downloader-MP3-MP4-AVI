# Downloader YouTube - MP3/MP4

Aplicativo desktop em Python usando CustomTkinter, yt-dlp e FFmpeg.

## Estrutura do projeto

- `main.py` - ponto de entrada do aplicativo
- `src/app.py` - interface e lógica de interação com o usuário
- `src/downloader.py` - lógica de download com yt-dlp
- `src/validators.py` - validações de URL e pastas
- `src/config.py` - configurações e opções de formato
- `src/history.py` - histórico de downloads usando SQLite
- `requirements.txt` - dependências do projeto

## Requisitos

- Python 3.10+
- `customtkinter`
- `yt-dlp`
- `Pillow`
- `requests`
- `ffmpeg` instalado e disponível no `PATH`

## Instalação

No terminal, execute:

```bash
pip install -r requirements.txt
```

## Uso

1. Abra um terminal na pasta do projeto.
2. Execute:

```bash
python main.py
```

3. Cole o link do YouTube.
4. Clique em `Buscar informações`.
5. Escolha o formato e a pasta de destino.
6. Clique em `Baixar`.
7. Use `Cancelar` para parar o download em andamento.
8. Clique em `Abrir pasta` para ver os arquivos baixados.

## Funcionalidades

- Baixa vídeo em MP4 em várias qualidades
- Baixa áudio em MP3 com diferentes bitrates
- Interface moderna com temas claro/escuro
- Histórico de downloads
- Verificação automática de atualizações
- Suporte a playlists
- Detecção automática de FFmpeg
- Aceita diversos formatos de URL do YouTube (watch, youtu.be, shorts, etc.)

## Como gerar o executável

Para gerar um executável .exe para Windows:

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o script de build:
   ```bash
   build.bat
   ```

3. O executável será gerado em `dist/DownloaderYouTube.exe`

### Requisitos para build:
- Python 3.8+
- Todas as dependências do `requirements.txt`
- FFmpeg instalado (opcional, apenas para downloads)

### Como distribuir o app portátil:
- Copie `dist/DownloaderYouTube.exe` para a pasta de distribuição
- Inclua a pasta `tools/ffmpeg/bin/` com `ffmpeg.exe` e `ffprobe.exe`
- A estrutura deve ficar assim:
  - `DownloaderYouTube.exe`
  - `tools/ffmpeg/bin/ffmpeg.exe`
  - `tools/ffmpeg/bin/ffprobe.exe`

### Notas:
- O executável não requer Python instalado
- Arquivos de configuração e histórico são criados na pasta do app
- FFmpeg é detectado automaticamente em:
  - `tools/ffmpeg/bin/ffmpeg.exe` ao lado do executável
  - `tools/ffmpeg/bin/ffmpeg.exe` dentro da pasta do projeto
  - `C:\ffmpeg\bin\ffmpeg.exe`
  - PATH do sistema
- Permite playlist ou vídeo único
- Escolha de pasta de destino
- Histórico básico de downloads em SQLite
- Mensagens de erro mais claras

## Observações

- O FFmpeg é necessário para conversão de áudio para MP3.
- Se o FFmpeg não estiver no `PATH`, o download pode falhar em formatos de áudio.
- Para gerar um executável no futuro, instale o PyInstaller separadamente:

```bash
pip install pyinstaller
```

```bash
pyinstaller --onefile --windowed main.py
```

