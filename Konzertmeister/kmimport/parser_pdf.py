"""PDF einlesen (nur Tabellen-PDFs mit Text, kein OCR)."""

from __future__ import annotations

from .event_extractor import enthaelt_datum, zeilen_zu_termine


def lese_zeilen(pfad) -> list[list[str]]:
    """Liest alle Zeilen. Erkannte Tabellen werden zellenweise gelesen,
    sonst Zeile für Zeile aus dem Seitentext (Tabelle ohne Gitterlinien)."""
    import pdfplumber

    zeilen: list[list[str]] = []
    with pdfplumber.open(str(pfad)) as pdf:
        for seite in pdf.pages:
            try:
                tabellen = seite.extract_tables()
            except Exception:  # defekte Tabellenstruktur -> Textmodus
                tabellen = []
            tab_zeilen = [[c or "" for c in zeile] for t in tabellen for zeile in t]
            text = seite.extract_text() or ""
            text_zeilen = [[zeile] for zeile in text.splitlines() if zeile.strip()]
            # Farbig hinterlegte Zeilen erkennt pdfplumber oft als winzige "Tabellen". Die Tabellen
            # werden deshalb nur verwendet, wenn sie mindestens so viele Datumszeilen liefern wie der Text.
            n_tab = sum(enthaelt_datum(z) for z in tab_zeilen)
            n_text = sum(enthaelt_datum(z) for z in text_zeilen)
            zeilen.extend(tab_zeilen if n_tab and n_tab >= n_text else text_zeilen)
    return zeilen


def lese_termine(pfad, cfg: dict):
    zeilen = lese_zeilen(pfad)
    if not zeilen:
        return [], ["Im PDF wurde kein Text gefunden (eingescanntes PDF? OCR wird nicht unterstützt)."]
    return zeilen_zu_termine(zeilen, cfg)
