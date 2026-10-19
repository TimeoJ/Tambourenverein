#!/usr/bin/env sh
# Startet den Konzertmeister-Importer (Linux/macOS). Python und alle Pakete werden beim ersten Start automatisch eingerichtet.
# Alle Optionen werden weitergereicht, z. B.:  ./starten.sh programm.pdf --von 01.11.2026 --bis 31.12.2026
cd "$(dirname "$0")" || exit 1
if ! command -v uv >/dev/null 2>&1; then
    echo "Einmalige Einrichtung: das Werkzeug 'uv' wird installiert (braucht Internet)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh || exit 1
    PATH="$HOME/.local/bin:$PATH"
fi
exec uv run main.py "$@"
