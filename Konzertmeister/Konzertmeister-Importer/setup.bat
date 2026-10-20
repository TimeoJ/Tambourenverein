@echo off
rem Richtet den Konzertmeister-Importer ein (einmalig). Vor jedem Download und jeder Aenderung wird gefragt.
rem   setup.bat              Stand pruefen (nur lesend), dann nach Rueckfrage einrichten
rem   setup.bat --pruefen    nur den Stand anzeigen, nichts veraendern
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
set "UVDIR=%~dp0.uv"
set "NUR_PRUEFEN=0"
if /i "%~1"=="--pruefen" set "NUR_PRUEFEN=1"

echo ============================================================
echo   Konzertmeister-Importer - Einrichtung
echo ============================================================
echo.
echo Aktueller Stand (nur lesend, es wird nichts veraendert):

set "UV="
where uv >nul 2>nul
if not errorlevel 1 set "UV=uv"
if exist "%UVDIR%\uv.exe" set "UV=%UVDIR%\uv.exe"
if defined UV (echo   [ok]   Werkzeug uv: gefunden ^(%UV%^)) else (echo   [fehlt] Werkzeug uv: nicht gefunden)

set "VENV_OK=0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import customtkinter, pdfplumber, openpyxl" >nul 2>nul
    if not errorlevel 1 set "VENV_OK=1"
)
if "%VENV_OK%"=="1" (echo   [ok]   Programmumgebung .venv mit allen Paketen: vorhanden) else (echo   [fehlt] Programmumgebung .venv mit allen Paketen: nicht vorhanden oder unvollstaendig)
echo.

if "%VENV_OK%"=="1" (
    echo Alles ist bereit. Zum Starten: starten.bat
    goto :ende
)
if "%NUR_PRUEFEN%"=="1" (
    echo Es fehlt noch etwas. Zum Einrichten: setup.bat ^(fragt vorher nach^)
    goto :ende
)

echo Zum Einrichten sind folgende Schritte noetig:
echo.
if not defined UV (
    echo   - Das Werkzeug "uv" herunterladen und in den Programmordner kopieren:
    echo        Herkunft : https://astral.sh/uv/install.ps1  ^(Installer von Astral, Open Source^)
    echo        Ziel     : %UVDIR%
    echo        Das Skript wird zuerst als Datei gespeichert und dann ausgefuehrt, sodass Sie es
    echo        danach in Ruhe ansehen koennen ^(%UVDIR%\install-uv.ps1^).
    echo        Es braucht keine Administratorrechte und aendert weder PATH noch die Registry.
    echo.
)
echo   - Eine Programmumgebung ".venv" im Programmordner anlegen und darin installieren:
echo        - Python, falls auf diesem PC keine passende Version gefunden wird ^(von uv geladen^)
echo        - customtkinter, pdfplumber, openpyxl samt deren Abhaengigkeiten ^(von https://pypi.org^)
echo.
echo Alles landet im Programmordner. Zum Entfernen genuegt es, diesen Ordner zu loeschen.
echo Es wird nichts im Windows-System installiert. Internetverbindung erforderlich.
echo.
choice /c JN /n /m "Moechten Sie fortfahren? [J = Ja, N = Nein] "
if errorlevel 2 (
    echo.
    echo Abgebrochen. Es wurde nichts veraendert und nichts heruntergeladen.
    echo Alternative ohne uv: Siehe README.md, Abschnitt "Installation".
    goto :ende
)
echo.

if not defined UV (
    echo Lade uv herunter...
    if not exist "%UVDIR%" mkdir "%UVDIR%"
    powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://astral.sh/uv/install.ps1' -OutFile '%UVDIR%\install-uv.ps1'"
    if errorlevel 1 goto :fehler
    set "UV_UNMANAGED_INSTALL=%UVDIR%"
    set "UV_NO_MODIFY_PATH=1"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%UVDIR%\install-uv.ps1"
    if errorlevel 1 goto :fehler
    set "UV=%UVDIR%\uv.exe"
    if not exist "%UVDIR%\uv.exe" goto :fehler
)

echo Richte die Programmumgebung ein...
if not exist "%UVDIR%" mkdir "%UVDIR%"
set "UV_PYTHON_INSTALL_DIR=%UVDIR%\python"
set "UV_CACHE_DIR=%UVDIR%\cache"
"%UV%" sync
if errorlevel 1 goto :fehler

echo.
echo Fertig. Zum Starten: starten.bat
goto :ende

:fehler
echo.
echo Die Einrichtung ist fehlgeschlagen. Bitte Internetverbindung pruefen und setup.bat erneut ausfuehren.
echo ^(Bereits Heruntergeladenes wird dabei wiederverwendet.^)

:ende
echo.
pause
endlocal
