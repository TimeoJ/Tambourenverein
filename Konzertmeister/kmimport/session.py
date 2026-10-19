"""Programmlogik ohne GUI. Die GUI ruft nur diese Klasse auf, dadurch ist alles testbar."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import exporter, parser_excel, parser_pdf
from .config import PROJEKT_ORDNER, lade_config
from .filters import Filter, wende_filter_an
from .models import Termin
from .validator import FEHLER, OK, WARNUNG, Meldung, pruefe, status
from .zeit import heute_text, normalisiere_datum, normalisiere_zeit

FELDER = {"datum", "beginn", "ende", "name", "raum", "ort", "treffpunkt",
          "information", "terminart", "kategorien"}


class ExportGesperrt(Exception):
    def __init__(self, probleme: list[str]):
        super().__init__("Export gesperrt")
        self.probleme = probleme


class Sitzung:
    def __init__(self, cfg: dict | None = None, heute: date | None = None):
        self.cfg = cfg if cfg is not None else lade_config()
        self.heute = heute or date.today()
        self.alle: list[Termin] = []
        self.sichtbar: list[Termin] = []
        self.protokoll: list[str] = []
        self.quelle = ""
        self.filter = Filter(von=heute_text(self.heute))

    # --- Laden -----------------------------------------------------------------
    def datei_laden(self, pfad) -> int:
        pfad = Path(pfad)
        endung = pfad.suffix.lower()
        if endung == ".pdf":
            termine, protokoll = parser_pdf.lese_termine(pfad, self.cfg)
        elif endung in (".xlsx", ".xlsm"):
            termine, protokoll = parser_excel.lese_termine(pfad, self.cfg)
        else:
            raise ValueError("Nur PDF- und Excel-Dateien (.xlsx/.xlsm) werden unterstützt. "
                             "Alte .xls-Dateien bitte in Excel als .xlsx speichern.")
        self.quelle = pfad.name
        self.alle = termine
        self.protokoll = [f"{len(termine)} Termine in '{pfad.name}' erkannt."] + protokoll
        self.filter_anwenden(self.filter)
        return len(termine)

    # --- Filter ----------------------------------------------------------------
    def filter_anwenden(self, f: Filter | None = None) -> list[str]:
        """Wendet den Filter an (ohne Angabe: den zuletzt verwendeten) und gibt Hinweise zurück."""
        if f is not None:
            self.filter = f
        self.sichtbar, meldungen = wende_filter_an(self.alle, self.filter, self.heute)
        return meldungen

    def dokument_zeitraum(self) -> tuple[str, str] | None:
        """Frühestes und spätestes Datum aller erkannten Termine (TT.MM.JJJJ) oder None."""
        daten = sorted(d for d in (t.datum_obj() for t in self.alle) if d)
        if not daten:
            return None
        return daten[0].strftime("%d.%m.%Y"), daten[-1].strftime("%d.%m.%Y")

    def leer_hinweis(self) -> str:
        """Erklärung, wenn der Filter alle erkannten Termine ausblendet."""
        zeitraum = self.dokument_zeitraum()
        if self.sichtbar or not self.alle or not zeitraum:
            return ""
        return (f"Das Dokument enthält {len(self.alle)} Termine vom {zeitraum[0]} bis {zeitraum[1]}, "
                "der Filter blendet aber alle aus (Von-Datum prüfen).")

    def ereignisnamen(self) -> list[str]:
        gesehen, namen = set(), []
        for t in sorted(self.alle, key=lambda t: (t.datum_obj() or date.max, t.beginn)):
            if t.name and t.name not in gesehen:
                gesehen.add(t.name)
                namen.append(t.name)
        return namen

    # --- Bearbeiten ------------------------------------------------------------
    def finde(self, uid: int) -> Termin:
        for t in self.alle:
            if t.uid == uid:
                return t
        raise KeyError(uid)

    def feld_setzen(self, uid: int, feld: str, wert: str) -> Termin:
        if feld not in FELDER:
            raise ValueError(f"Unbekanntes Feld: {feld}")
        t = self.finde(uid)
        wert = (wert or "").strip()
        if feld == "datum":
            wert = normalisiere_datum(wert) or wert
        elif feld in ("beginn", "ende"):
            n = normalisiere_zeit(wert)
            wert = n if n is not None else wert
        setattr(t, feld, wert)
        t.geprueft = True
        return t

    def zeit_setzen(self, uids, text: str) -> str | None:
        """Setzt Beginn und Ende für mehrere Zeilen ('20:00-22:00'). Gibt eine Fehlermeldung zurück oder None."""
        m = re.match(r"^\s*(.+?)\s*(?:-|–|—|bis)\s*(.+?)\s*$", text or "")
        beginn = normalisiere_zeit(m.group(1)) if m else None
        ende = normalisiere_zeit(m.group(2)) if m else None
        if not beginn or not ende:
            return "Bitte Beginn und Ende angeben, z. B. 20:00-22:00."
        if ende <= beginn:
            return "Das Ende muss nach dem Beginn liegen."
        for uid in uids:
            t = self.finde(uid)
            t.beginn, t.ende, t.geprueft = beginn, ende, True
        return None

    def als_geprueft(self, uids) -> None:
        for uid in uids:
            self.finde(uid).geprueft = True

    def loeschen(self, uids) -> None:
        weg = set(uids)
        self.alle = [t for t in self.alle if t.uid not in weg]
        self.sichtbar = [t for t in self.sichtbar if t.uid not in weg]

    def neuer_termin(self) -> Termin:
        t = Termin(geprueft=True)
        self.alle.append(t)
        self.sichtbar.append(t)
        return t

    # --- Prüfung ---------------------------------------------------------------
    def meldungen(self, t: Termin) -> list[Meldung]:
        return pruefe(t, self.cfg)

    def status(self, t: Termin) -> str:
        return status(self.meldungen(t))

    def zusammenfassung(self) -> dict:
        zaehler = {OK: 0, WARNUNG: 0, FEHLER: 0}
        for t in self.sichtbar:
            zaehler[self.status(t)] += 1
        zaehler["gesamt"] = len(self.sichtbar)
        return zaehler

    def export_probleme(self) -> list[str]:
        if not self.sichtbar:
            return ["Es gibt keine Termine zum Exportieren."]
        probleme = []
        for t in self.sichtbar:
            fehler = [m.text for m in self.meldungen(t) if m.stufe == FEHLER]
            if fehler:
                probleme.append(f"{t.datum or '(kein Datum)'} {t.name or '(ohne Name)'}: " + "; ".join(fehler))
        return probleme

    # --- CSV -------------------------------------------------------------------
    def csv_vorschau(self) -> str:
        return exporter.csv_text(self.sichtbar, self.cfg)

    def ausgabe_ordner(self) -> Path:
        ordner = PROJEKT_ORDNER / "output"
        ordner.mkdir(exist_ok=True)
        return ordner

    def exportieren(self, pfad) -> Path:
        """Schreibt die CSV. Wirft ExportGesperrt bei offenen Fehlern, ExportFehler bei Kodierungsproblemen."""
        probleme = self.export_probleme()
        if probleme:
            raise ExportGesperrt(probleme)
        return exporter.schreibe_csv(pfad, self.sichtbar, self.cfg)

    def kodierung_setzen(self, kodierung: str) -> None:
        if kodierung not in exporter.KODIERUNGEN.values():
            raise ValueError(f"Unbekannte Kodierung: {kodierung}")
        self.cfg["csv"]["kodierung"] = kodierung

    def test_csv_schreiben(self, pfad) -> tuple[Path, str]:
        termin = exporter.testtermin(self.cfg, self.heute)
        pfad = exporter.schreibe_csv(pfad, [termin], self.cfg)
        return pfad, exporter.csv_text([termin], self.cfg)
