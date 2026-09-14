@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Blackjack Pro - generador del INSTALADOR
echo ============================================
echo.

if not exist "dist\BlackjackPro.exe" (
    echo [1/3] No se encontro dist\BlackjackPro.exe -- generandolo primero...
    echo.
    call build_exe.bat
    if not exist "dist\BlackjackPro.exe" (
        echo.
        echo ERROR: no se pudo generar dist\BlackjackPro.exe. Revisa los
        echo mensajes de arriba ^(de build_exe.bat^) antes de continuar.
        pause
        exit /b 1
    )
) else (
    echo [1/3] dist\BlackjackPro.exe ya existe, se usara ese.
    echo       Si has cambiado el codigo desde la ultima vez, corre
    echo       build_exe.bat primero para regenerarlo.
)
echo.

echo [2/3] Buscando Inno Setup ^(ISCC.exe^)...
set "ISCC="

rem Metodo 1 (el fiable): Inno Setup siempre se registra en el
rem "App Paths" del registro de Windows, sea cual sea la version
rem instalada -- asi no hace falta acertar la carpeta ni el numero
rem de version a mano.
for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe" /ve 2^>nul ^| findstr /i "REG_SZ"') do set "ISCC=%%B"
if not defined ISCC for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe" /ve 2^>nul ^| findstr /i "REG_SZ"') do set "ISCC=%%B"
if defined ISCC if not exist "!ISCC!" set "ISCC="

rem Metodo 2 (respaldo): rutas habituales, probando varias versiones
rem conocidas de Inno Setup por si el registro fallase.
if not defined ISCC (
    for %%V in (6 7 5 8) do (
        if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup %%V\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup %%V\ISCC.exe"
        if not defined ISCC if exist "%ProgramFiles%\Inno Setup %%V\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup %%V\ISCC.exe"
    )
)

if not defined ISCC (
    echo.
    echo ERROR: no se encontro Inno Setup en este equipo.
    echo Descargalo gratis de https://jrsoftware.org/isdl.php ^(instalacion
    echo normal, con las opciones por defecto^) y vuelve a correr este script.
    pause
    exit /b 1
)
echo       Encontrado: !ISCC!
echo.

echo [3/3] Compilando el instalador...
"!ISCC!" installer.iss
if errorlevel 1 (
    echo.
    echo ERROR: fallo la compilacion del instalador -- revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
if exist "dist_installer\BlackjackPro_Setup.exe" (
    echo ============================================
    echo   LISTO: dist_installer\BlackjackPro_Setup.exe
    echo ============================================
    echo Ese archivo es el instalador completo -- doble click para
    echo instalar Blackjack Pro con acceso directo en el menu inicio
    echo ^(y, si lo marcas, tambien en el escritorio^), mas su propio
    echo desinstalador. No hacen falta permisos de administrador.
    echo.
    echo Tus partidas guardadas nunca se tocan al instalar o desinstalar:
    echo viven en su propia carpeta "saves", separada del programa.
) else (
    echo ============================================
    echo   Algo fallo -- no se genero el instalador.
    echo   Revisa los mensajes de arriba.
    echo ============================================
)
echo.
pause
