@echo off
setlocal
cd /d "%~dp0.."

echo.
set /p "VERSION=Versione da includere nell'EXE (es. 1.2.3): "
if not defined VERSION (
    echo Versione non inserita.
    pause
    exit /b 1
)
powershell -NoProfile -Command "if ($env:VERSION -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$') { exit 1 }"
if errorlevel 1 (
    echo Versione non valida. Usa il formato 1.2.3 o 1.2.3-beta.
    pause
    exit /b 1
)
>app_version.txt echo %VERSION%

echo Installazione/verifica degli strumenti di build...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Impossibile installare gli strumenti di build.
    del app_version.txt
    pause
    exit /b 1
)

echo Creazione di GeoFS_Server.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name GeoFS_Server --icon "icon\GeoFS_Server.ico" --add-data "dashboard.html;." --add-data "app_version.txt;." --add-data "icon\GeoFS_Server.ico;icon" --add-data "icon\planefavicon.svg;icon" server_gui.py
if errorlevel 1 (
    echo Build non riuscita.
    del app_version.txt
    pause
    exit /b 1
)

del app_version.txt
echo.
echo Fatto: dist\GeoFS_Server.exe
pause