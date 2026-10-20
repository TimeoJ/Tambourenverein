#!/usr/bin/env sh
# Richtet den Konzertmeister-Importer ein (einmalig, Linux/macOS). Vor jedem Download wird gefragt.
#   ./setup.sh              Stand prüfen (nur lesend), dann nach Rückfrage einrichten
#   ./setup.sh --pruefen    nur den Stand anzeigen, nichts verändern
cd "$(dirname "$0")" || exit 1
HIER=$(pwd)
UVDIR="$HIER/.uv"
NUR_PRUEFEN=0
[ "$1" = "--pruefen" ] && NUR_PRUEFEN=1

echo "============================================================"
echo "  Konzertmeister-Importer - Einrichtung"
echo "============================================================"
echo
echo "Aktueller Stand (nur lesend, es wird nichts verändert):"

UV=""
if command -v uv >/dev/null 2>&1; then UV="uv"; fi
if [ -x "$UVDIR/uv" ]; then UV="$UVDIR/uv"; fi
if [ -n "$UV" ]; then echo "  [ok]    Werkzeug uv: gefunden ($UV)"; else echo "  [fehlt] Werkzeug uv: nicht gefunden"; fi

VENV_OK=0
if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import customtkinter, pdfplumber, openpyxl" >/dev/null 2>&1; then VENV_OK=1; fi
if [ "$VENV_OK" = 1 ]; then echo "  [ok]    Programmumgebung .venv mit allen Paketen: vorhanden"; else echo "  [fehlt] Programmumgebung .venv mit allen Paketen: nicht vorhanden oder unvollständig"; fi
echo

if [ "$VENV_OK" = 1 ]; then echo "Alles ist bereit. Zum Starten: ./starten.sh"; exit 0; fi
if [ "$NUR_PRUEFEN" = 1 ]; then echo "Es fehlt noch etwas. Zum Einrichten: ./setup.sh (fragt vorher nach)"; exit 0; fi

echo "Zum Einrichten sind folgende Schritte nötig:"
echo
if [ -z "$UV" ]; then
    echo "  - Das Werkzeug \"uv\" herunterladen und in den Programmordner kopieren:"
    echo "       Herkunft : https://astral.sh/uv/install.sh  (Installer von Astral, Open Source)"
    echo "       Ziel     : $UVDIR"
    echo "       Das Skript wird zuerst als Datei gespeichert und dann ausgeführt, sodass Sie es"
    echo "       danach ansehen können ($UVDIR/install-uv.sh)."
    echo "       Es braucht keine Administratorrechte und ändert weder PATH noch Shell-Profile."
    echo
fi
echo "  - Eine Programmumgebung \".venv\" im Programmordner anlegen und darin installieren:"
echo "       - Python, falls auf diesem Rechner keine passende Version gefunden wird (von uv geladen)"
echo "       - customtkinter, pdfplumber, openpyxl samt Abhängigkeiten (von https://pypi.org)"
echo
echo "Alles landet im Programmordner. Zum Entfernen genügt es, diesen Ordner zu löschen."
echo "Es wird nichts im System installiert. Internetverbindung erforderlich."
echo
printf "Möchten Sie fortfahren? [j/N] "
read -r antwort
case "$antwort" in
    j|J|ja|Ja|JA|y|Y|yes) ;;
    *) echo; echo "Abgebrochen. Es wurde nichts verändert und nichts heruntergeladen."
       echo "Alternative ohne uv: Siehe README.md, Abschnitt \"Installation\"."; exit 0 ;;
esac
echo

fehler() {
    echo
    echo "Die Einrichtung ist fehlgeschlagen. Bitte Internetverbindung prüfen und ./setup.sh erneut ausführen."
    exit 1
}

if [ -z "$UV" ]; then
    echo "Lade uv herunter..."
    mkdir -p "$UVDIR" || fehler
    curl -LsSf -o "$UVDIR/install-uv.sh" https://astral.sh/uv/install.sh || fehler
    UV_UNMANAGED_INSTALL="$UVDIR" UV_NO_MODIFY_PATH=1 sh "$UVDIR/install-uv.sh" || fehler
    UV="$UVDIR/uv"
    [ -x "$UV" ] || fehler
fi

echo "Richte die Programmumgebung ein..."
mkdir -p "$UVDIR"
UV_PYTHON_INSTALL_DIR="$UVDIR/python" UV_CACHE_DIR="$UVDIR/cache" "$UV" sync || fehler

echo
echo "Fertig. Zum Starten: ./starten.sh"
