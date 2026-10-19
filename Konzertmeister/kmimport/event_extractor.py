"""Gemeinsame Termin-Erkennung für PDF und Excel.

Eingabe sind Zeilen, jede Zeile eine Liste von Zellen (bei PDF-Textzeilen nur eine Zelle).
Erwartetes Layout ungefähr: Wochentag | Datum | Zeit | Anlass – die Reihenfolge ist aber egal.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from .models import Termin
from .regeln import bestimme_kategorien, bestimme_terminart
from .zeit import (DATUM_RE, WOCHENTAGE_KURZ, datum_tupel, finde_zeit_am_anfang,
                   interpretiere)

_WD = r"(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag|Mo|Di|Mi|Do|Fr|Sa|So)"
_L = "A-Za-zÄÖÜäöüß"
_WD_ENDE = re.compile(rf"(?<![{_L}])({_WD})\.?[\s,;:(\-–]*$")
_WD_ANFANG = re.compile(rf"^[\s,;:(\-–]*({_WD})\.?(?![{_L}])[\s,;:)\-–]*")
_WD_GANZ = re.compile(rf"^({_WD})\.?,?$")
_WD_INDEX = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}

_KOPFWOERTER = {
    "wochentag", "tag", "datum", "zeit", "uhrzeit", "anlass", "termin", "termine",
    "bezeichnung", "bemerkung", "bemerkungen", "ort", "treffpunkt", "beginn", "ende",
    "information", "info", "raum", "von", "bis", "veranstaltung", "programm",
}
_MONATE = ("januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember")
_IGNORIEREN = re.compile(
    r"^(?:ausblick|tätigkeitsprogramm.*|\d+\s*/\s*\d+|version.*"
    rf"|(?:\d{{1,2}}\.?\s*)?(?:{_MONATE})\b.*\d{{4}})$",
    re.I,
)
_FUSSZEILE = re.compile(r"\bSeite\s*\d+\b", re.I)  # "Marcel Gyger Seite 1 18.03.2025"

_KOPF_MUSTER = {
    "datum": r"^datum",
    "wochentag": r"^(wochentag|tag)$",
    "zeit": r"^(zeit|uhrzeit)",
    "beginn": r"^(beginn|start|von)\b",
    "ende": r"^(ende|bis)\b",
    "name": r"(anlass|bezeichnung|veranstaltung|titel|programm|^name|^termin)",
    "ort": r"^ort",
    "treffpunkt": r"^treffpunkt",
    "raum": r"^raum",
    "info": r"(bemerkung|information|^info|hinweis)",
}


def _nfc(text: str) -> str:
    """Umlaute immer zusammengesetzt (ä statt a + ¨). Manche PDFs/Excel-Dateien liefern zerlegte Zeichen,
    die in Konzertmeister oder Excel dann falsch aussehen."""
    return unicodedata.normalize("NFC", text)


def _sauber(text: str) -> str:
    text = " ".join(_nfc(str(text)).split())
    text = re.sub(r"\s+,", ",", text)
    return text.strip(" ,;:-–—|")


def _sauber_zelle(z) -> str:
    return " ".join(_nfc(str(z)).split()) if z is not None else ""


def _wd_index(text: str) -> int:
    return _WD_INDEX[text.lower()[:2]]


def enthaelt_datum(zellen) -> bool:
    return DATUM_RE.search(" ".join(str(z) for z in zellen if z)) is not None


def ist_ignorierbar(text: str) -> bool:
    t = text.strip().lower()
    if not t or _IGNORIEREN.match(t):
        return True
    woerter = re.findall(r"\w+", t)
    return bool(woerter) and all(w in _KOPFWOERTER for w in woerter)


@dataclass
class Analyse:
    datum: tuple          # (Tag, Monat, Jahr) als Zahlen
    wochentag: str | None
    zeit: str | None
    titel: str
    hinweise: list = field(default_factory=list)


def analysiere_zeile(zellen) -> Analyse | None:
    """Findet Datum, Wochentag, Zeitangabe und Titel in einer Zeile. None = kein Termin."""
    zellen = [_sauber_zelle(z) for z in zellen]
    zellen = [z for z in zellen if z]
    datum = None
    wochentag = None
    zeiten: list[str] = []
    rest: list[str] = []

    for zelle in zellen:
        arbeit = zelle
        if datum is None:
            m = DATUM_RE.search(arbeit)
            if m:
                datum = datum_tupel(m)
                vor, nach = arbeit[: m.start()], arbeit[m.end():]
                mv = _WD_ENDE.search(vor)
                if mv and wochentag is None:
                    wochentag, vor = mv.group(1), vor[: mv.start()]
                mn = _WD_ANFANG.match(nach)
                if mn and wochentag is None:
                    wochentag, nach = mn.group(1), nach[mn.end():]
                arbeit = _sauber(f"{vor} {nach}")
                if not arbeit:
                    continue
        if wochentag is None and _WD_GANZ.match(arbeit):
            wochentag = _WD_GANZ.match(arbeit).group(1)
            continue
        gefunden = finde_zeit_am_anfang(arbeit)
        if gefunden and (not zeiten or gefunden[1] == ""):
            zeiten.append(gefunden[0])
            arbeit = gefunden[1]
            if not arbeit:
                continue
        rest.append(arbeit)

    if datum is None:
        return None

    hinweise = []
    zeit = None
    if len(zeiten) == 1:
        zeit = zeiten[0]
    elif len(zeiten) >= 2:
        if len(zeiten) == 2 and all(_einfach(z) for z in zeiten):
            zeit = f"{zeiten[0]} - {zeiten[1]}"
        else:
            zeit = zeiten[0]
            hinweise.append("Weitere Zeitangaben im Original ignoriert: " + ", ".join(zeiten[1:]))
    return Analyse(datum, wochentag, zeit, _sauber(" ".join(rest)), hinweise)


def _einfach(zeit: str) -> bool:
    """Reine Uhrzeit ohne ca./ab/Bereich/Sonderwort?"""
    return re.fullmatch(r"\d{1,2}(?:[.:,h]\d{2})?(?:\s*(?:Uhr|h))?", zeit.strip(), re.I) is not None


def teile_titel(text: str) -> tuple[str, str]:
    """Trennt den Terminnamen von Zusatzinformationen.

    Der Name reicht bis zur ersten Klammer oder zum ersten Komma, der Rest kommt in die Information
    (eine Klammer direkt nach dem Namen wird dabei aufgelöst):
      'Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm'
          -> ('Hirsmontag', 'Schnitzelbanktour, Probelokal im Kostüm')
      'Ständli (18:30 Uhr) Fahnenabgabe (19:30 Uhr) Uhr Log, anschl. Nachtessen'
          -> ('Ständli', '18:30 Uhr Fahnenabgabe (19:30 Uhr) Uhr Log, anschl. Nachtessen')
    """
    text = _sauber(text)
    m = re.search(r"[(,]", text)
    if not m:
        return text, ""
    name = _sauber(text[: m.start()])
    rest = text[m.start():].lstrip(" ,;")
    if not name:  # Text beginnt mit Klammer/Komma: nichts abspalten
        return _sauber(text.replace("(", " ").replace(")", " ")), ""
    if rest.startswith("("):
        ende = rest.find(")")
        if ende != -1:
            rest = rest[1:ende] + rest[ende + 1:]
    return name, _sauber(rest)


def baue_termin(analyse: Analyse, quelle: str, cfg: dict, extras: dict | None = None) -> Termin:
    extras = extras or {}
    t = Termin(quelle=quelle)
    tag, monat, jahr = analyse.datum
    t.datum = f"{tag:02d}.{monat:02d}.{jahr:04d}"

    d: date | None = t.datum_obj()
    if analyse.wochentag and d and d.weekday() != _wd_index(analyse.wochentag):
        t.warnungen.append(
            f"Wochentag im Original ({analyse.wochentag}) passt nicht zum Datum "
            f"{t.datum} ({WOCHENTAGE_KURZ[d.weekday()]})"
        )

    t.name, zusatz = teile_titel(analyse.titel)
    if extras.get("info"):
        zusatz = ", ".join(x for x in (zusatz, _sauber(extras["info"])) if x)

    z = interpretiere(analyse.zeit, cfg.get("mitternacht_als", "23:59"))
    t.beginn, t.ende = z.beginn, z.ende
    if z.warnung:
        t.warnungen.append(z.warnung)
    t.warnungen.extend(analyse.hinweise)

    info = zusatz
    for n in [z.notiz] + analyse.hinweise:
        if n:
            info = n if not info else info + (" " if info.endswith((".", "!", "?")) else ". ") + n
    t.information = info

    t.ort = _sauber(extras.get("ort", ""))
    t.treffpunkt = _sauber(extras.get("treffpunkt", ""))
    t.raum = _sauber(extras.get("raum", ""))

    t.terminart = bestimme_terminart(t.name, cfg)
    t.kategorien = bestimme_kategorien(t.name, cfg)
    if not t.terminart:
        t.warnungen.append("Terminart nicht erkannt (wird sonst aus der Konzertmeister-Vorlage übernommen)")
    return t


def _folgezeile_anhaengen(t: Termin, text: str) -> None:
    zusatz = f"Folgezeile im Original: {text}"
    t.information = zusatz if not t.information else (
        t.information + (" " if t.information.endswith((".", "!", "?")) else ". ") + zusatz)
    t.warnungen.append("Folgezeile ohne Datum angehängt – bitte prüfen")
    t.quelle += f" | {text}"


# --- Excel mit Kopfzeile -------------------------------------------------------------

def finde_kopfzeile(zeilen, max_zeilen: int = 20):
    """Sucht eine Kopfzeile (Datum/Zeit/Anlass ...). Gibt (zeilenindex, {schluessel: spalte}) oder None."""
    for i, zeile in enumerate(zeilen[:max_zeilen]):
        zuordnung: dict[str, int] = {}
        for spalte, zelle in enumerate(zeile):
            text = _sauber_zelle(zelle).lower()
            if not text:
                continue
            for schluessel, muster in _KOPF_MUSTER.items():
                if schluessel not in zuordnung and re.search(muster, text):
                    zuordnung[schluessel] = spalte
                    break
        if "datum" in zuordnung and ({"name", "zeit", "beginn"} & set(zuordnung)):
            return i, zuordnung
    return None


def _nach_spalten(zeile, spalten: dict):
    def hole(schluessel):
        idx = spalten.get(schluessel)
        return zeile[idx] if idx is not None and idx < len(zeile) else ""

    zellen = [hole(k) for k in ("wochentag", "datum", "zeit", "beginn", "ende", "name")]
    extras = {k: _sauber_zelle(hole(k)) for k in ("ort", "treffpunkt", "raum", "info")}
    return zellen, extras


def zeilen_zu_termine(zeilen, cfg: dict, spalten: dict | None = None):
    """Wandelt Zeilen in Termine um. Gibt (termine, protokoll) zurück.

    - Kopf-, Fuss- und Abschnittszeilen ("Ausblick", "Seite 1 ...") werden ignoriert.
    - Zeilen mit einem Stichwort aus cfg["ueberspringen"] (z. B. "KEINE PROBE") sind keine Termine.
    - Eine Zeile ohne Datum direkt nach einem Termin gilt als Folgezeile desselben Termins und wird
      an dessen Information angehängt (abschaltbar mit cfg["folgezeilen_anhaengen"] = false).
    """
    termine: list[Termin] = []
    protokoll: list[str] = []
    vorheriger: Termin | None = None
    skip = [s.lower() for s in cfg.get("ueberspringen", []) if s.strip()]

    for zeile in zeilen:
        quelle = _sauber(" | ".join(_sauber_zelle(z) for z in zeile if _sauber_zelle(z)))
        if not quelle:
            continue
        if _FUSSZEILE.search(quelle):
            vorheriger = None
            continue

        extras: dict = {}
        zellen = zeile
        if spalten:
            zellen, extras = _nach_spalten(zeile, spalten)
        analyse = analysiere_zeile(zellen)

        if analyse is None:
            if ist_ignorierbar(quelle):
                vorheriger = None
            elif vorheriger is not None and cfg.get("folgezeilen_anhaengen", True):
                _folgezeile_anhaengen(vorheriger, quelle)
                protokoll.append(f"Folgezeile an '{vorheriger.name}' ({vorheriger.datum}) angehängt: {quelle}")
            else:
                protokoll.append(f"Ohne Datum übersprungen: {quelle}")
            continue

        treffer = next((s for s in skip if s in analyse.titel.lower()), None)
        if treffer:
            protokoll.append(f"Kein Termin (Stichwort '{treffer}'), übersprungen: {quelle}")
            vorheriger = None
            continue

        vorheriger = baue_termin(analyse, quelle, cfg, extras)
        termine.append(vorheriger)
    return termine, protokoll
