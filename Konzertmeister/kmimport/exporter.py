"""Konzertmeister-CSV erzeugen."""

from __future__ import annotations

import csv
import io
import unicodedata
from datetime import date
from pathlib import Path

from .models import Termin
from .zeit import naechster_wochentag


def zeile(t: Termin, cfg: dict) -> dict:
    return {
        "Datum": t.datum,
        "Beginn": t.beginn,
        "Ende": t.ende,
        "Name": t.name,
        "Raum": t.raum,
        "Ort": t.ort,
        "Treffpunkt": t.treffpunkt,
        "Information": " ".join(t.information.split()),
        "Terminart": t.terminart,
        "Kategorien": t.kategorien,
        "Verein": t.verein or cfg.get("verein", ""),
    }


def csv_text(termine, cfg: dict) -> str:
    csv_cfg = cfg["csv"]
    spalten = csv_cfg["spalten"]
    puffer = io.StringIO()
    schreiber = csv.writer(
        puffer,
        delimiter=csv_cfg.get("trennzeichen", ";"),
        quoting=csv.QUOTE_ALL if csv_cfg.get("alles_in_anfuehrungszeichen", True) else csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
    )
    schreiber.writerow(spalten)
    for t in termine:
        werte = zeile(t, cfg)
        schreiber.writerow([werte.get(s, "") for s in spalten])
    # Letzte Absicherung: auch von Hand eingetippte Texte mit zerlegten Umlauten (a + ¨) werden zu ä.
    return unicodedata.normalize("NFC", puffer.getvalue())


class ExportFehler(Exception):
    """Die CSV konnte nicht geschrieben werden (z. B. Zeichen in der Kodierung nicht darstellbar)."""


# Anzeigename -> Python-Kodierung. UTF-8 mit BOM ist Standard: Excel erkennt daran UTF-8 und zeigt
# Umlaute (ä, ö, ü) richtig an. Ohne BOM erscheinen sie dort oft als "Ã¤", "Ã¶", "Ã¼".
KODIERUNGEN = {
    "UTF-8 mit BOM (Excel, empfohlen)": "utf-8-sig",
    "UTF-8 ohne BOM": "utf-8",
    "Windows-1252 (ANSI)": "cp1252",
}


def schreibe_csv(pfad, termine, cfg: dict) -> Path:
    pfad = Path(pfad)
    kodierung = cfg["csv"].get("kodierung", "utf-8-sig")
    text = csv_text(termine, cfg)
    try:
        daten = text.encode(kodierung)
    except UnicodeEncodeError as e:
        raise ExportFehler(
            f"Das Zeichen {text[e.start]!r} lässt sich in der Kodierung '{kodierung}' nicht speichern. "
            "Bitte UTF-8 wählen oder das Zeichen im Termin ersetzen.") from e
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_bytes(daten)  # Bytes direkt schreiben: Zeilenenden (\r\n) und BOM bleiben unverändert
    return pfad


def testtermin(cfg: dict, heute: date | None = None) -> Termin:
    """Eine Probe am kommenden Mittwoch von 20:00 bis 22:00 Uhr (zum Testen des Imports)."""
    mittwoch = naechster_wochentag(heute or date.today(), 2)
    return Termin(
        datum=mittwoch.strftime("%d.%m.%Y"),
        beginn="20:00",
        ende="22:00",
        name="Probe",
        terminart="Probe",
        kategorien="Probe",
    )
