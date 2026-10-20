"""Prüfung eines Termins vor dem Export (Variante B: Fehler blockieren den Export)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Termin

_ZEIT = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

OK, WARNUNG, FEHLER = "ok", "warn", "error"


@dataclass
class Meldung:
    stufe: str   # "error" oder "warn"
    text: str


def kategorien_liste(text: str) -> list[str]:
    """Zerlegt das Kategorien-Feld (Trennung mit Komma oder Semikolon) in einzelne Namen."""
    return [k.strip() for k in re.split(r"[;,]", text or "") if k.strip()]


def _pruefe_kategorien(t: Termin, cfg: dict) -> list[Meldung]:
    """Jede Kategorie muss laut Konzertmeister zwischen 3 und 20 Zeichen lang sein."""
    kleinste, groesste = cfg.get("kategorie_zeichen", [3, 20])
    m = []
    for k in kategorien_liste(t.kategorien):
        if not kleinste <= len(k) <= groesste:
            m.append(Meldung(FEHLER, f"Kategorie '{k}' hat {len(k)} Zeichen (erlaubt: {kleinste} bis {groesste})"))
    return m


def pruefe(t: Termin, cfg: dict) -> list[Meldung]:
    m: list[Meldung] = []
    if t.datum_obj() is None:
        m.append(Meldung(FEHLER, "Datum fehlt oder ist ungültig (TT.MM.JJJJ)"))
    if not t.name.strip():
        m.append(Meldung(FEHLER, "Name fehlt"))
    for label, wert in (("Beginn", t.beginn), ("Ende", t.ende)):
        wert = wert.strip()
        if not wert:
            m.append(Meldung(FEHLER, f"{label} fehlt"))
        elif not _ZEIT.match(wert):
            m.append(Meldung(FEHLER, f"{label} ungültig (HH:MM)"))
    beginn, ende = t.beginn.strip(), t.ende.strip()
    if _ZEIT.match(beginn) and _ZEIT.match(ende):
        if ende == "00:00" and beginn != "00:00":  # Mitternacht (nur möglich, wenn so konfiguriert)
            if not t.geprueft:
                m.append(Meldung(WARNUNG, "Ende 00:00 (Mitternacht): in Konzertmeister prüfen, ob das akzeptiert wird"))
        elif ende <= beginn:
            m.append(Meldung(FEHLER, "Ende liegt nicht nach dem Beginn"))
    m.extend(_pruefe_kategorien(t, cfg))
    if t.terminart and t.terminart not in cfg.get("erlaubte_terminarten", []):
        m.append(Meldung(FEHLER, f"Terminart '{t.terminart}' ist in Konzertmeister nicht erlaubt"))
    if not t.geprueft:
        m.extend(Meldung(WARNUNG, w) for w in t.warnungen)
    return m


def status(meldungen: list[Meldung]) -> str:
    if any(x.stufe == FEHLER for x in meldungen):
        return FEHLER
    if meldungen:
        return WARNUNG
    return OK
