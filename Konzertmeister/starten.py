"""Startet den Importer mit eigener virtueller Umgebung (.venv) – ohne uv, nur mit vorhandenem Python.

    python starten.py [Optionen wie bei main.py]

Beim ersten Start wird .venv angelegt und werden die Pakete aus requirements.txt installiert (Internet nötig).
Ist Python noch nicht installiert, nimm stattdessen starten.bat bzw. starten.sh (die holen Python selbst).
"""
import subprocess
import sys
import venv
from pathlib import Path

HIER = Path(__file__).resolve().parent
VENV = HIER / ".venv"
PY = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
BENOETIGT = ["customtkinter", "pdfplumber", "openpyxl"]


def main() -> int:
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
