@echo off
rem Startet den Konzertmeister-Importer. Python und alle Pakete werden beim ersten Start automatisch eingerichtet.
rem Alle Optionen werden weitergereicht, z. B.:  starten.bat programm.pdf --von 01.11.2026 --bis 31.12.2026
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
    echo Einmalige Einrichtung: das Werkzeug "uv" wird installiert ^(braucht Internet^)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
uv run main.py %*
if errorlevel 1 pause
