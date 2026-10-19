"""Datenmodell: ein Termin. Alle Felder sind Text, damit sie in der GUI direkt editierbar sind."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date, datetime

_zaehler = itertools.count(1)


@dataclass
class Termin:
    datum: str = ""            # TT.MM.JJJJ
    beginn: str = ""           # HH:MM
    ende: str = ""             # HH:MM
    name: str = ""
    raum: str = ""
    ort: str = ""
    treffpunkt: str = ""
    information: str = ""
    terminart: str = ""
    kategorien: str = ""
    verein: str = ""           # leer = Standard aus config.json
    quelle: str = ""           # Originaltext der Zeile (zur Kontrolle)
    warnungen: list = field(default_factory=list)
    geprueft: bool = False     # True, sobald der Benutzer die Zeile bearbeitet/bestätigt hat
    uid: int = field(default_factory=lambda: next(_zaehler))

    def datum_obj(self) -> date | None:
        try:
            return datetime.strptime(self.datum.strip(), "%d.%m.%Y").date()
        except ValueError:
            return None
