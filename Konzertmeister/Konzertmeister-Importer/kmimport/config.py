"""Einstellungen und Regeln (config.json)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

# Als eigenständige Anwendung (PyInstaller) liegen config.json, input/ und output/ neben der .exe.
PROJEKT_ORDNER = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                  else Path(__file__).resolve().parent.parent)
CONFIG_PFAD = PROJEKT_ORDNER / "config.json"

STANDARD_CONFIG = {
    "config_version": 2,
    "verein": "Tambourenverein Zofingen",
    # Ein Ende um Mitternacht ("24.00"/"00.00") wird so übernommen (Termine liegen innerhalb eines Tages).
    # Das wird im Feld Information dokumentiert. Alternative: "00:00".
    "mitternacht_als": "23:59",
    # Zeilen, deren Terminname eines dieser Stichwörter enthält, sind keine Termine (ohne Gross-/Kleinschreibung).
    "ueberspringen": ["keine probe"],
    # Zeile ohne Datum direkt unter einem Termin = Fortsetzung dieses Termins (wird an Information angehängt).
    "folgezeilen_anhaengen": True,
    "csv": {
        "trennzeichen": ";",
        # utf-8-sig = UTF-8 mit BOM: Excel zeigt Umlaute damit richtig an.
        # Weitere Möglichkeiten: "utf-8" (ohne BOM), "cp1252" (Windows/ANSI).
        "kodierung": "utf-8-sig",
        "alles_in_anfuehrungszeichen": True,
        "spalten": [
            "Datum", "Beginn", "Ende", "Name", "Raum", "Ort", "Treffpunkt",
            "Information", "Terminart", "Kategorien", "Verein",
        ],
        "kategorien_trennzeichen": ", ",
    },
    # Konzertmeister verlangt für jede Kategorie zwischen 3 und 20 Zeichen (Verstoss = Fehler, blockiert den Export).
    "kategorie_zeichen": [3, 20],
    "erlaubte_terminarten": [
        "Probe", "Auftritt", "Sonstiges", "Probenanfrage", "Auftrittsanfrage", "Information",
    ],
    "standard_terminart": "",
    # Die Regeln werden von oben nach unten geprüft; der erste Treffer gewinnt.
    # Geprüft wird nur der Terminname (nicht die Information).
    # Stichwörter mit höchstens 3 Buchstaben (GV, DV) müssen als ganzes Wort vorkommen.
    "terminart_regeln": {
        "Probe": ["Probe", "Probesamstag", "Probesonntag", "Marschprobe"],
        "Auftritt": [
            "Auftritt", "Ständli", "Umzug", "Konzert", "Marschmusikparade", "Marschparade",
            "Fasnacht", "Hirsmontag", "Kinderfest", "Augustfeier", "Fahnenweihe",
        ],
        "Sonstiges": [
            "GV", "DV", "Sitzung", "Vereinsabend", "Vereinsmeisterschaft", "Grillplausch",
            "Hochzeit", "Helfereinsatz", "Wettspiel",
        ],
    },
    # Hier können mehrere Kategorien gleichzeitig zutreffen.
    # Die Kategorienamen müssen in Konzertmeister genauso existieren.
    "kategorie_regeln": {
        "Probe": ["Probe"],
        "Fasnacht": ["Fasnacht", "Hirsmontag", "Schnitzelbank"],
        "Auftritt": [
            "Auftritt", "Ständli", "Konzert", "Marschparade", "Marschmusikparade",
            "Kinderfest", "Umzug", "Augustfeier", "Fahnenweihe",
        ],
        "Verein": [
            "GV", "DV", "Sitzung", "Vereinsabend", "Vereinsmeisterschaft", "Grillplausch",
            "Hochzeit", "Helfereinsatz",
        ],
        "Wettspiel": ["Wettspiel", "ZTPF", "EJTPF", "ZJTPF", "ETPF", "OTV"],
    },
}


def lade_config(pfad: Path | str | None = None) -> dict:
    """Lädt config.json (fehlende Einträge werden mit Standardwerten ergänzt).
    Existiert die Datei nicht, wird sie mit den Standardwerten angelegt."""
    pfad = Path(pfad) if pfad else CONFIG_PFAD
    cfg = copy.deepcopy(STANDARD_CONFIG)
    if pfad.exists():
        with open(pfad, encoding="utf-8") as f:
            benutzer = json.load(f)
        for schluessel, wert in benutzer.items():
            if schluessel == "csv" and isinstance(wert, dict):
                cfg["csv"].update(wert)
            else:
                cfg[schluessel] = wert
        # Migration: Die erste Programmversion schrieb UTF-8 ohne BOM (Umlaute wirkten in Excel kaputt).
        if benutzer.get("config_version", 1) < 2:
            if cfg["csv"].get("kodierung", "").lower() == "utf-8":
                cfg["csv"]["kodierung"] = "utf-8-sig"
            cfg["config_version"] = 2
    else:
        try:
            speichere_config(cfg, pfad)
        except OSError:
            pass
    return cfg


def speichere_config(cfg: dict, pfad: Path | str | None = None) -> None:
    pfad = Path(pfad) if pfad else CONFIG_PFAD
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
