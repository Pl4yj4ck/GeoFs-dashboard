@echo off
setlocal
cd /d "%~dp0.."

where wsl.exe >nul 2>nul
if errorlevel 1 (
    echo WSL non e' installato o non e' disponibile nel PATH.
    echo Installa WSL e una distribuzione Linux con: wsl --install
    pause
    exit /b 1
)

set "WSL_ARCH="
for /f "delims=" %%A in ('wsl.exe --exec uname -m 2^>nul') do set "WSL_ARCH=%%A"
if /I not "%WSL_ARCH%"=="x86_64" (
    echo WSL non e' pronto oppure la distribuzione predefinita non e' Linux x86_64.
    echo Avvia e configura una distribuzione Linux x86_64, poi riprova.
    pause
    exit /b 1
)

set "LINUX_DIR="
for /f "delims=" %%D in ('wsl.exe --exec wslpath -a "%CD%" 2^>nul') do set "LINUX_DIR=%%D"
if not defined LINUX_DIR (
    echo Impossibile convertire il percorso del progetto in un percorso WSL.
    pause
    exit /b 1
)

echo Avvio della build AppImage in WSL...
echo Al primo utilizzo, installa in WSL Python 3, venv, Tkinter e appimagetool.
wsl.exe --cd "%LINUX_DIR%" --exec bash ./scripts_build/crea_appimage.sh
if errorlevel 1 (
    echo Build AppImage non riuscita. Controlla i prerequisiti Linux e riprova.
    pause
    exit /b 1
)

if not exist "dist\GeoFS_Server-x86_64.AppImage" (
    echo Build terminata ma il file AppImage non e' stato trovato in dist.
    pause
    exit /b 1
)

echo.
echo Fatto: dist\GeoFS_Server-x86_64.AppImage
pause
