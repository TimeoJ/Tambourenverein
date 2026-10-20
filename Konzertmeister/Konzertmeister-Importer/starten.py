"""Startet den Importer mit eigener virtueller Umgebung (.venv) – ohne uv, nur mit vorhandenem Python.

    python starten.py [Optionen wie bei main.py]

Beim ersten Start wird .venv angelegt und werden die Pakete aus requirements.txt installiert (Internet nötig).
Vor jeder Installation wird gefragt. Ist Python noch nicht installiert, nimm setup.bat bzw. setup.sh.
"""
import subprocess
import sys
import venv
from pathlib import Path

HIER = Path(__file__).resolve().parent
VENV = HIER / ".venv"
PY = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
BENOETIGT = ["customtkinter", "pdfplumber", "openpyxl"]


def _fragen() -> bool:
    print("Die Programmumgebung ist noch nicht vollständig. Folgendes würde jetzt passieren:")
    print(f"  - im Programmordner wird eine Umgebung angelegt: {VENV}")
    print("  - aus dem Internet (https://pypi.org) werden installiert: customtkinter, pdfplumber, openpyxl")
    print("Es wird nichts im System installiert; zum Entfernen den Programmordner löschen.")
    try:
        return input("Fortfahren? [j/N] ").strip().lower() in ("j", "ja", "y", "yes")
    except EOFError:
        return False


def _vorhanden() -> bool:
    return PY.exists() and subprocess.run([str(PY), "-c", "import " + ",".join(BENOETIGT)],
                                          capture_output=True).returncode == 0


def main() -> int:
    if not _vorhanden() and not _fragen():
        print("Abgebrochen. Es wurde nichts verändert.")
        return 1
    if not PY.exists():
        print("Einmalige Einrichtung: virtuelle Umgebung wird erstellt...")
        venv.create(VENV, with_pip=True)
    if subprocess.run([str(PY), "-c", "import " + ",".join(BENOETIGT)], capture_output=True).returncode != 0:
        print("Pakete werden installiert (Internet nötig)...")
        r = subprocess.run([str(PY), "-m", "pip", "install", "--disable-pip-version-check",
                            "customtkinter>=5.2", "pdfplumber>=0.10", "openpyxl>=3.1"])
        if r.returncode != 0:
            print("Installation fehlgeschlagen. Internetverbindung prüfen.")
            return r.returncode
    return subprocess.run([str(PY), str(HIER / "main.py"), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    sys.exit(main())
