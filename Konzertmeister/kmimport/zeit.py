"""Datums- und Zeit-Helfer. Hier steht die Logik für die Zeitangaben im Tätigkeitsprogramm.

Grundsatz: Niemals Zeiten schätzen oder erfinden. Was nicht eindeutig im Original steht,
bleibt leer und wird im Feld "Information" dokumentiert.

Lesbare Formate:
  Zeit:   20.00  20:00  20,00  20h00  20 Uhr  20.00 Uhr  8.45  (auch Bereiche: 20.00 - 22.00, 20-22 Uhr)
  Datum:  10.01.2025  10.1.25  10/01/2025  10-01-2025  2025-01-10
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# --- Datum -----------------------------------------------------------------------------
DATUM_RE = re.compile(
    r"(?<![\d./-])(?:"
    r"(?P<t>\d{1,2})(?P<s>[./-])(?P<m>\d{1,2})(?P=s)(?P<j>\d{4}|\d{2})"
    r"|(?P<ij>\d{4})-(?P<im>\d{2})-(?P<it>\d{2})"
    r")(?!\d)"
)


def datum_tupel(m: re.Match) -> tuple[int, int, int]:
    """(Tag, Monat, Jahr) aus einem DATUM_RE-Treffer; zweistellige Jahre -> 20xx."""
    if m.group("ij"):
        return int(m.group("it")), int(m.group("im")), int(m.group("ij"))
    jahr = int(m.group("j"))
    return int(m.group("t")), int(m.group("m")), jahr + 2000 if jahr < 100 else jahr


# --- Uhrzeit ---------------------------------------------------------------------------
_SEP = r"(?:[.:,]|h)"  # 20.00 / 20:00 / 20,00 / 20h00
# Eine Uhrzeit: "20.00", "20:00", "20.00 Uhr", "20 Uhr", "20h".
_T = rf"\d{{1,2}}(?:{_SEP}\d{{2}}(?:\s*(?:Uhr|h)\b)?|\s*(?:Uhr|h)\b)"
_T_MIN = rf"\d{{1,2}}{_SEP}\d{{2}}(?:\s*(?:Uhr|h)\b)?"
_TRENNER = r"(?:-|–|—|bis)"
# Beginn darf auch eine blanke Stunde sein, wenn danach "- 22 Uhr" folgt ("20-22 Uhr").
_T1 = rf"(?:{_T}|\d{{1,2}}(?=\s*{_TRENNER}\s*\d{{1,2}}(?:{_SEP}\d{{2}})?\s*(?:Uhr|h)\b))"

UNBEKANNT_RE = re.compile(rf"\?{{2,}}(?:\s*\(\s*(?P<t>{_T})\s*\))?", re.I)
WORT_RE = re.compile(
    r"(?:ganzer\s+Tag|ganzt(?:ä|ae)gig|ganztags|Vormittag|Nachmittag|Mittag|Abend)(?![\wäöüÄÖÜ])",
    re.I,
)
ZEIT_RE = re.compile(rf"(?P<pre>(?:ca\.?|circa|ab|um)\s*)?(?P<t1>{_T1})", re.I)
BEREICH_RE = re.compile(
    rf"(?:\s*{_TRENNER}\s*(?P<t2>{_T})|\s+(?P<t3>{_T_MIN})(?!\.?\d))", re.I
)

_ZEIT_FORM = re.compile(r"^\s*(\d{1,2})(?:[.:,h](\d{2}))?\s*(?:Uhr|h)?\s*$", re.I)

WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def hhmm(text: str, erlaube_24: bool = False) -> str | None:
    """'20.00' / '8:30' / '20 Uhr' -> '20:00' (None, wenn keine gültige Uhrzeit).
    Mit erlaube_24 wird '24.00' als '24:00' (Mitternacht) akzeptiert."""
    m = re.match(r"\s*(\d{1,2})(?:[.:,h](\d{2}))?", text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if erlaube_24 and h == 24 and mi == 0:
        return "24:00"
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def normalisiere_zeit(text: str) -> str | None:
    """Eingabe aus der GUI: '' bleibt '', gültige Zeiten werden zu HH:MM, sonst None.
    Akzeptiert 20.00, 20:00, 20,00, 20h00, 20 Uhr, 20."""
    if not text or not text.strip():
        return ""
    if not _ZEIT_FORM.match(text):
        return None
    return hhmm(text)


def normalisiere_datum(text: str) -> str | None:
    """'4.11.26' / '04-11-2026' / '2026-11-04' -> '04.11.2026' (None, wenn kein gültiges Datum)."""
    m = DATUM_RE.fullmatch((text or "").strip())
    if not m:
        return None
    tag, monat, jahr = datum_tupel(m)
    try:
        return date(jahr, monat, tag).strftime("%d.%m.%Y")
    except ValueError:
        return None


def parse_datum(text: str, heute: date | None = None) -> date | None:
    """Datum aus der GUI. 'heute' ergibt das heutige Datum; ungültig oder leer -> None."""
    t = (text or "").strip().lower()
    if t == "heute":
        return heute or date.today()
    n = normalisiere_datum(t)
    return datetime.strptime(n, "%d.%m.%Y").date() if n else None


def heute_text(heute: date | None = None) -> str:
    return (heute or date.today()).strftime("%d.%m.%Y")


def naechster_wochentag(ab: date, wochentag: int) -> date:
    """Nächster Wochentag (0=Montag ... 6=Sonntag), frühestens morgen."""
    tage = (wochentag - ab.weekday()) % 7 or 7
    return ab + timedelta(days=tage)


def finde_zeit_am_anfang(text: str) -> tuple[str, str] | None:
    """Liest eine Zeitangabe vom Textanfang. Gibt (zeitangabe, rest) zurück oder None."""
    t = text.strip()
    if not t:
        return None
    m = UNBEKANNT_RE.match(t) or WORT_RE.match(t)
    if m:
        return t[: m.end()].strip(), t[m.end():].strip()
    m = ZEIT_RE.match(t)
    if not m:
        return None
    ende = m.end()
    r = BEREICH_RE.match(t, ende)
    if r:
        ende = r.end()
    return t[:ende].strip(), t[ende:].strip()


@dataclass
class ZeitInfo:
    beginn: str = ""
    ende: str = ""
    notiz: str = ""      # Text für das Feld "Information"
    warnung: str = ""    # Text für die Warnliste der GUI


def interpretiere(angabe: str | None, mitternacht: str = "23:59") -> ZeitInfo:
    """Wandelt die Zeitangabe aus dem Original in Beginn/Ende um (ohne etwas zu schätzen).

    Ein Ende um Mitternacht ("24.00" oder "00.00") wird als `mitternacht` übernommen und
    im Feld Information dokumentiert, denn der Termin liegt innerhalb eines Tages."""
    if not angabe or not angabe.strip():
        return ZeitInfo(
            notiz="Im Tätigkeitsprogramm war keine Zeitangabe vorhanden. Bitte prüfen.",
            warnung="Keine Zeitangabe gefunden",
        )
    e = " ".join(angabe.split())

    m = UNBEKANNT_RE.match(e)
    if m:
        if m.group("t"):
            b = hhmm(m.group("t"))
            if b:
                return ZeitInfo(
                    beginn=b,
                    notiz=f"Originaleintrag: {e}. Startzeit aus Klammer übernommen. "
                          "Endzeit unbekannt. Bitte prüfen.",
                    warnung=f"Zeitangabe im Original unklar: {e}",
                )
        return ZeitInfo(
            notiz="Originalzeit im Tätigkeitsprogramm unbekannt (???). Bitte prüfen.",
            warnung="Zeitangabe im Original unbekannt (???)",
        )

    if WORT_RE.match(e):
        return ZeitInfo(
            notiz=f"Originalangabe im Tätigkeitsprogramm: {e}.",
            warnung=f"Zeitangabe im Original ungenau: {e}",
        )

    m = ZEIT_RE.match(e)
    ungueltig = ZeitInfo(
        notiz=f"Originalangabe im Tätigkeitsprogramm: {e}. Zeit nicht lesbar. Bitte prüfen.",
        warnung=f"Zeitangabe nicht lesbar: {e}",
    )
    if not m:
        return ungueltig
    beginn = hhmm(m.group("t1"))
    r = BEREICH_RE.match(e, m.end())
    ende_text = (r.group("t2") or r.group("t3")) if r else None
    ende = hhmm(ende_text, erlaube_24=True) if ende_text else None
    if beginn is None or (r and ende is None):
        return ungueltig
    ungefaehr = bool(m.group("pre"))

    if ende:
        notizen: list[str] = []
        warnungen: list[str] = []
        if ende in ("24:00", "00:00") and beginn != "00:00":
            notizen.append(f"Ende im Original: {ende_text.strip()} (Mitternacht), als {mitternacht} übernommen.")
            warnungen.append(f"Ende um Mitternacht ({ende_text.strip()}), als {mitternacht} übernommen")
            ende = mitternacht
        if ungefaehr:
            notizen.append(f"Originalangabe im Tätigkeitsprogramm: {e}.")
            warnungen.append(f"Zeitangabe im Original ungenau: {e}")
        return ZeitInfo(beginn, ende, " ".join(notizen), "; ".join(warnungen))

    if ungefaehr:
        return ZeitInfo(
            beginn,
            notiz=f"Originalangabe im Tätigkeitsprogramm: {e}. Endzeit unbekannt.",
            warnung=f"Nur Startzeit im Original: {e}",
        )
    return ZeitInfo(
        beginn,
        notiz=f"Im Original wurde nur eine einzelne Uhrzeit angegeben ({e}). Endzeit unbekannt.",
        warnung=f"Nur eine Uhrzeit im Original: {e}",
    )
