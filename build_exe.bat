@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Blackjack Pro - generador del ejecutable
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] No se encontro el entorno virtual .venv -- creandolo...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: no se pudo crear el entorno virtual. ^Esta Python instalado
        echo y agregado al PATH? Descargalo de https://python.org si hace falta.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Entorno virtual .venv encontrado.
)

echo [2/4] Instalando dependencias del proyecto...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: fallo la instalacion de dependencias -- revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo [3/4] Instalando PyInstaller...
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: fallo la instalacion de PyInstaller.
    pause
    exit /b 1
)

echo [4/4] Generando BlackjackPro.exe (puede tardar 1-3 minutos)...
".venv\Scripts\python.exe" -m PyInstaller blackjack_pro.spec --noconfirm
echo.

if exist "dist\BlackjackPro.exe" (
    echo ============================================
    echo   LISTO: dist\BlackjackPro.exe
    echo ============================================
    echo Puedes mover ese archivo a donde quieras -- la primera vez que
    echo lo abras va a crear su propia carpeta "saves" al lado, con tus
    echo perfiles y partidas.
) else (
    echo ============================================
    echo   Algo fallo -- no se genero dist\BlackjackPro.exe
    echo   Revisa los mensajes de arriba.
    echo ============================================
)
echo.
pause
