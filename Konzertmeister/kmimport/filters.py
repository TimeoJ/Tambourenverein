"""Filter: Zeitraum (von/bis, je Datum oder Event), Terminart und Namensfilter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .models import Termin
from .zeit import parse_datum


@dataclass
class Filter:
    """Alle Felder sind optional; leer = keine Einschränkung.

    von / bis             Datum (TT.MM.JJJJ oder 'heute'); beide Grenzen gelten inklusive
    von_event / bis_event Teil eines Terminnamens; 'von' beginnt am Tag des ersten Treffers,
                          'bis' endet am Tag des ersten Treffers (bis und mit diesem Tag)
    arten                 None = alle; sonst die erlaubten Terminarten ('' = nicht erkannt)
    name_enthaelt         nur Termine, deren Name einen dieser Begriffe enthält (Trennung mit , oder ;)
    name_enthaelt_nicht   Termine, deren Name einen dieser Begriffe enthält, ausblenden
    Sind Datum und Event gleichzeitig gesetzt, gilt die strengere Grenze.
    """
    von: str = ""
    bis: str = ""
    von_event: str = ""
    bis_event: str = ""
    arten: tuple | list | None = None
    name_enthaelt: str = ""
    name_enthaelt_nicht: str = ""


def _begriffe(text: str) -> list[str]:
    return [b.strip().lower() for b in re.split(r"[;,]", text or "") if b.strip()]


def _sortiert(termine):
    return sorted(termine, key=lambda t: (t.datum_obj() is None, t.datum_obj() or date.max, t.beginn or "99:99"))


def _finde_event(termine: list[Termin], suche: str) -> Termin | None:
    s = (suche or "").strip().lower()
    if not s:
        return None
    for t in termine:
        if s in t.name.lower():
            return t
    for t in termine:
        if s in t.information.lower():
            return t
    return None


def _grenze_datum(text: str, bezeichnung: str, heute: date, meldungen: list[str]) -> date | None:
    if not (text or "").strip():
        return None
    d = parse_datum(text, heute)
    if d is None:
        meldungen.append(f"'{bezeichnung}' ist kein gültiges Datum ({text!r}, erwartet TT.MM.JJJJ) – keine Begrenzung.")
    return d


def wende_filter_an(termine, f: Filter, heute: date | None = None):
    """Gibt (sichtbare_termine, meldungen) zurück. Termine ohne gültiges Datum bleiben immer sichtbar,
    damit Fehler nicht verloren gehen."""
    heute = heute or date.today()
    meldungen: list[str] = []
    alle = _sortiert(termine)
    mit_datum = [t for t in alle if t.datum_obj() is not None]

    start = _grenze_datum(f.von, "Von", heute, meldungen)
    if (f.von_event or "").strip():
        t = _finde_event(mit_datum, f.von_event)
        if t is None:
            meldungen.append(f"Von-Event '{f.von_event}' wurde nicht gefunden – keine Begrenzung nach Event.")
        else:
            d = t.datum_obj()
            if start is not None and start > d:
                meldungen.append(f"Von-Event '{t.name}' ({t.datum}) liegt vor dem Von-Datum "
                                 f"{start.strftime('%d.%m.%Y')} – es gilt das spätere Von-Datum.")
            else:
                start = d
                meldungen.append(f"Start am {t.datum}: {t.name}")

    ende = _grenze_datum(f.bis, "Bis", heute, meldungen)
    if (f.bis_event or "").strip():
        kandidaten = [t for t in mit_datum if start is None or t.datum_obj() >= start]
        t = _finde_event(kandidaten, f.bis_event)
        if t is None:
            meldungen.append(f"Bis-Event '{f.bis_event}' wurde nicht gefunden – keine Begrenzung nach Event.")
        else:
            d = t.datum_obj()
            if ende is not None and ende < d:
                meldungen.append(f"Bis-Event '{t.name}' ({t.datum}) liegt nach dem Bis-Datum "
                                 f"{ende.strftime('%d.%m.%Y')} – es gilt das frühere Bis-Datum.")
            else:
                ende = d
                meldungen.append(f"Ende am {t.datum} (bis und mit): {t.name}")

    if start and ende and start > ende:
        meldungen.append("Das Startdatum liegt nach dem Enddatum – es gibt keine Termine im Zeitraum.")

    ein, aus = _begriffe(f.name_enthaelt), _begriffe(f.name_enthaelt_nicht)
    ergebnis = []
    for t in alle:
        d = t.datum_obj()
        if d is not None and ((start and d < start) or (ende and d > ende)):
            continue
        if f.arten is not None and t.terminart not in f.arten:
            continue
        name = t.name.lower()
        if ein and not any(b in name for b in ein):
            continue
        if aus and any(b in name for b in aus):
            continue
        ergebnis.append(t)
    return ergebnis, meldungen
