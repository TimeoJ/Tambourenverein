"""Excel (.xlsx/.xlsm) einlesen. Alle Tabellenblätter werden gelesen.

Excel speichert Uhrzeiten unterschiedlich: als echte Zeit, als Text ("20.00") oder – wenn man
20.00 tippt – als Zahl 20 bzw. 20.3 (statt 20.30). In Spalten, die als Zeit/Beginn/Ende erkannt
sind, wird das in Text wie "20.00" / "20.30" zurückübersetzt, damit der Zeitparser sie lesen kann.
"""

from __future__ import annotations

import datetime as dt

from .event_extractor import finde_kopfzeile, zeilen_zu_termine


def zelle_text(wert, zeit: bool = False) -> str:
    """Zelle als Text. zeit=True: Die Zelle steht in einer Zeitspalte, Zahlen sind dann Uhrzeiten."""
    if wert is None:
        return ""
    if isinstance(wert, dt.datetime):
        if wert.year <= 1900:  # reine Uhrzeit, von Excel als Datum 1899/1900 gespeichert
            return wert.strftime("%H:%M")
        return wert.strftime("%d.%m.%Y")
    if isinstance(wert, dt.date):
        return wert.strftime("%d.%m.%Y")
    if isinstance(wert, dt.time):
        return wert.strftime("%H:%M")
    if isinstance(wert, dt.timedelta):  # Format [h]:mm
        minuten = round(wert.total_seconds() / 60)
        return f"{minuten // 60 % 24:02d}:{minuten % 60:02d}"
    if isinstance(wert, bool):
        return str(wert)
    if isinstance(wert, (int, float)):
        v = float(wert)
        if 0 < v < 1 and abs(v * 100 - round(v * 100)) > 1e-6:  # Uhrzeit als Tagesbruchteil (0.8333 = 20:00)
            minuten = round(v * 24 * 60)
            return f"{minuten // 60 % 24:02d}:{minuten % 60:02d}"
        if zeit:  # als Zahl getippte Uhrzeit: 20 -> "20.00", 20.3 -> "20.30", 8.45 -> "8.45"
            stunde = int(v)
            return f"{stunde}.{round((v - stunde) * 100):02d}"
        return str(int(v)) if v.is_integer() else str(wert)
    return str(wert).strip()


def lese_termine(pfad, cfg: dict):
    import openpyxl

    wb = openpyxl.load_workbook(str(pfad), data_only=True, read_only=True)
    termine, protokoll = [], []
    try:
        for blatt in wb.worksheets:
            roh = [list(zeile) for zeile in blatt.iter_rows(values_only=True)]
            roh = [z for z in roh if any(c is not None and str(c).strip() != "" for c in z)]
            text = [[zelle_text(c) for c in zeile] for zeile in roh]
            kopf = finde_kopfzeile(text)
            if kopf:
                start, spalten = kopf
                zeitspalten = {spalten[k] for k in ("zeit", "beginn", "ende") if k in spalten}
                daten = [
                    [zelle_text(c, zeit=(i in zeitspalten)) for i, c in enumerate(zeile)]
                    for zeile in roh[start + 1:]
                ]
            else:
                spalten, daten = None, text
            t, p = zeilen_zu_termine(daten, cfg, spalten)
            termine.extend(t)
            protokoll.extend(f"[{blatt.title}] {zeile}" for zeile in p)
    finally:
        wb.close()
    if not termine:
        protokoll.append("In der Excel-Datei wurden keine Zeilen mit Datum gefunden.")
    return termine, protokoll
