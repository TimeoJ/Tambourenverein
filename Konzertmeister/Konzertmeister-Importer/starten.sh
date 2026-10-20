#!/usr/bin/env sh
# Startet den Konzertmeister-Importer. Dieses Skript lädt nichts herunter und installiert nichts.
# Beim allerersten Mal vorher einmalig ./setup.sh ausführen.
# Optionen werden weitergereicht, z. B.:  ./starten.sh programm.pdf --von 01.11.2026 --bis 31.12.2026
cd "$(dirname "$0")" || exit 1
if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import customtkinter, pdfplumber, openpyxl" >/dev/null 2>&1; then
    exec .venv/bin/python main.py "$@"
fi
echo "Der Konzertmeister-Importer ist noch nicht eingerichtet."
echo "Bitte zuerst einmalig ./setup.sh ausführen (es fragt vor jedem Download nach)."
exit 1
