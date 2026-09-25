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
python -m PyInstaller --noconfirm --clean --onefile --windowed --name GeoFS_Server --icon "icon\icon.ico" --add-data "dashboard.html;." --add-data "icon\icon.ico;icon" server_gui.py
if errorlevel 1 (
    echo Build non riuscita.
    pause
    exit /b 1
)

echo.
echo Fatto: dist\GeoFS_Server.exe
pause