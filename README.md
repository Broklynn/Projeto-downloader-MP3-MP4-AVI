# Guia Rápido - Baixador Simplificado de YouTube

## 1. Instalar Python
- Baixe e instale Python 3.10 ou superior: [https://www.python.org/downloads/](https://www.python.org/downloads/)

## 2. Instalar dependências
Abra o terminal (ou CMD no Windows) e digite:

pip install customtkinter yt-dlp



SE QUISER GARANTIR A ULTIMA VERSÃO:

pip install --upgrade pip
pip install --upgrade customtkinter yt-dlp



1º INSTALAR FFmpeg (NECESSARIO PARA ALGUNS FORMATOS)
O FFmpeg é usado para converter vídeos e extrair áudio. Siga os passos:

Baixe o FFmpeg: https://ffmpeg.org/download.html → escolha Windows builds by gyan.dev.

Extraia a pasta baixada em um local fixo, por exemplo C:\ffmpeg.

Abra Painel de Controle → Sistema → Configurações Avançadas → Variáveis de Ambiente.

Em Variáveis do sistema, selecione Path → Editar → Novo.

Adicione o caminho da pasta bin do FFmpeg, por exemplo:

    C:\ffmpeg\bin

Clique em OK e reinicie o terminal ou CMD.

2º TESTE DIGITANDO NO TERMINAL:

ffmpeg -version


3º RODAR PROGRAMA

No terminal, vá até a pasta do programa e execute:

python main.py


4º. USANDO BAIXADOR

 1º Cole o link do YouTube na caixa de texto.

 2º Escolha o formato desejado (MP3, MP4, AVI, MKV).

 3º Clique em Baixar.

 4º Para cancelar, clique em Cancelar.

 5º Após o download, clique em Abrir Pasta de Downloads para encontrar o arquivo.


 