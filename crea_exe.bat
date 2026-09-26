@echo off
setlocal
cd /d "%~dp0"

echo Installazione/verifica degli strumenti di build...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Impossibile installare gli strumenti di build.
    pause
    exit /b 1
)

echo Creazione di GeoFS_Server.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name GeoFS_Server --icon "icon\GeoFS_Server.ico" --add-data "dashboard.html;." --add-data "icon\GeoFS_Server.ico;icon" --add-data "icon\planefavicon.svg;icon" server_gui.py
if errorlevel 1 (
    echo Build non riuscita.
    pause
    exit /b 1
)

echo.
echo Fatto: dist\GeoFS_Server.exe
pause