@echo off
title GeoFS Dashboard

cd /d "%~dp0"

:: Trova l'IPv4 locale principale
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4.*"') do (
    set "IP=%%A"
    goto :found
)

:found
set "IP=%IP: =%"

cls

echo.
echo ================================================
echo.
echo IPv4 = http://%IP%:8080
echo.
python _server.py
pause
