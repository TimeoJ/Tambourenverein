@echo off
rem Startet den Konzertmeister-Importer. Dieses Skript laedt nichts herunter und installiert nichts.
rem Beim allerersten Mal vorher einmalig setup.bat ausfuehren.
rem Optionen werden weitergereicht, z. B.:  starten.bat programm.pdf --von 01.11.2026 --bis 31.12.2026
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto :einrichten
".venv\Scripts\python.exe" -c "import customtkinter, pdfplumber, openpyxl" >nul 2>nul
if errorlevel 1 goto :einrichten
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
exit /b %errorlevel%

:einrichten
echo Der Konzertmeister-Importer ist noch nicht eingerichtet.
echo Bitte zuerst einmalig setup.bat ausfuehren (es fragt vor jedem Download nach).
echo.
pause
exit /b 1
