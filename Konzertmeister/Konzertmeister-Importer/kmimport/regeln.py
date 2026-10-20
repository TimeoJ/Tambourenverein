"""Terminart und Kategorien aus dem Terminnamen bestimmen (Regeln stehen in config.json)."""

from __future__ import annotations

import re


def _passt(stichwort: str, text: str) -> bool:
    s, t = stichwort.lower().strip(), text.lower()
    if not s:
        return False
    if len(s) <= 3:  # kurze Kürzel wie GV/DV nur als ganzes Wort
        return re.search(rf"(?<!\w){re.escape(s)}(?!\w)", t) is not None
    return s in t


def _treffer(regeln: dict, name: str) -> list[str]:
    return [
        ergebnis for ergebnis, woerter in regeln.items()
        if any(_passt(w, name) for w in woerter)
    ]


def bestimme_terminart(name: str, cfg: dict) -> str:
    treffer = _treffer(cfg.get("terminart_regeln", {}), name)
    return treffer[0] if treffer else cfg.get("standard_terminart", "")


def bestimme_kategorien(name: str, cfg: dict) -> str:
    trenner = cfg["csv"].get("kategorien_trennzeichen", ", ")
    return trenner.join(_treffer(cfg.get("kategorie_regeln", {}), name))
