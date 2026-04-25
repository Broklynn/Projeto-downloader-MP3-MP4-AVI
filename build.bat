@echo off
echo ========================================
echo  Downloader YouTube - Build Script
echo ========================================
echo.

REM Limpar builds antigos
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo Limpando builds antigos...
echo.

REM Ativar ambiente virtual se existir
if exist .venv\Scripts\activate.bat (
    echo Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
    echo.
)

REM Instalar dependências se necessário
echo Verificando dependências...
pip install -r requirements.txt --quiet
echo.

REM Gerar executável
echo Gerando executável...
echo Comando: pyinstaller --noconsole --onefile --name "DownloaderYouTube" main.py
echo.

pyinstaller --noconsole --onefile --name "DownloaderYouTube" main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERRO: Falha ao gerar executável!
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Executável gerado com sucesso!
echo.
echo Localização: dist\DownloaderYouTube.exe
echo.
echo Para testar o executável:
echo dist\DownloaderYouTube.exe

echo.
pause