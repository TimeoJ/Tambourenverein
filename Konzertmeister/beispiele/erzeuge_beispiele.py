"""Erzeugt ein fiktives Tätigkeitsprogramm als Excel und PDF (zum Ausprobieren und für die Tests).

Aufruf:  python beispiele/erzeuge_beispiele.py
Benötigt openpyxl und reportlab (reportlab nur für diese Beispiel-PDFs).

Das Beispiel enthält absichtlich die Sonderfälle, die in echten Tätigkeitsprogrammen vorkommen:
ganzer Tag, ???, ??? (19.55), ca./ab, Einzelzeit, Ende um Mitternacht, "KEINE PROBE", Folgezeile,
falscher Wochentag, Zeitangaben mit : und h statt ., Fusszeile mit Datum und farbig hinterlegte Zeilen.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

# (Datum, Zeitangabe, Anlass, Wochentag überschreiben)   Datum None = Folgezeile ohne Datum
PROGRAMM = [
    (date(2026, 10, 14), "20.00 - 22.00", "Probe", None),                       # Vergangenheit
    (date(2026, 10, 21), "20.00 - 22.00", "Probe", None),
    (date(2026, 10, 28), "20.00 - 22.00", "Probe", None),
    (date(2026, 11, 4), "20:30 - 22:30", "Probe", None),                         # Zeit mit Doppelpunkt
    (date(2026, 11, 11), "20.00 - 22.00", "Probe", "Donnerstag"),               # falscher Wochentag
    (date(2026, 11, 14), "09.00 - 15.00", "Probesamstag (mit Mittagspause im Probelokal)", None),
    (date(2026, 11, 21), "15.32", "Ständli Altersheim, Treffpunkt Probelokal", None),
    (date(2026, 11, 27), "", "KEINE PROBE wegen Weihnachtsmarkt", None),         # kein Termin
    (date(2026, 11, 28), "19.00 - 00.00", "Jahreskonzert Stadtmusik Musterhausen", None),   # Mitternacht
    (date(2026, 12, 5), "ganzer Tag", "Adventsmarkt Zofingen", None),
    (date(2026, 12, 12), "???", "Vereinsabend", None),
    (date(2027, 1, 15), "19h30 - 23h00", "GV 2027", None),                       # Zeit mit h
    (date(2027, 1, 23), "Vormittag", "Probesonntag", None),
    (date(2027, 2, 6), "12.30 - 18.30", "Fasnachtsumzug Dagmersellen, Probelokal im Kostüm", None),
    (date(2027, 2, 8), "18.30 - 24.00", "Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm", None),
    (date(2027, 2, 12), "??? (19.55)", "Kantonalmusikfest Beispielstadt (evt. Marschparade mit MG Muster)", None),
    (date(2027, 3, 13), "ca. 18.00", "Wurlitzer-Plausch Zunzgen", None),
    (date(2027, 4, 24), "ab 11.00 Uhr", "Auffahrt, Familien Grillplausch Waldhaus, Riken", None),
    (date(2027, 5, 29), "07.00 - 17.00", "Powerman Zofingen", None),
    (date(2027, 6, 19), "09.00-13.00", "Tambourenkonzert im Kirchgemeindehaus", None),
    (None, "", "am Abend Waggel (mit Ehemaligen), organisiert durch Max", None),  # Folgezeile
    (date(2027, 6, 26), "20.00 - 22.00", "Sommerkonzert", None),
    "AUSBLICK",
    (date(2027, 9, 4), "14.00 - 17.00", "Kinderfest Zofingen", None),
    (date(2028, 1, 14), "19.00 - 23.00", "GV 2028", None),
]
FUSSZEILE = "Max Muster      Seite 1      18.03.2025"
KOPFZEILE = ["Wochentag", "Datum", "Zeit", "Anlass"]


def _zeilen():
    """Gibt (Wochentag, Datum|None, Zeit, Anlass) zurück; 'Ausblick' als eigene Zeile."""
    for eintrag in PROGRAMM:
        if eintrag == "AUSBLICK":
            yield ("Ausblick", None, "", "")
            continue
        d, zeit, anlass, wd = eintrag
        yield (wd or (WOCHENTAGE[d.weekday()] if d else ""), d, zeit, anlass)


def erzeuge_excel(pfad) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Programm"
    ws.append(["Tätigkeitsprogramm (Beispiel, fiktive Daten)"])
    ws.append([])
    ws.append(KOPFZEILE)
    for wd, d, zeit, anlass in _zeilen():
        if wd == "Ausblick":
            ws.append([wd])
        elif d is None:
            ws.append(["", None, "", anlass])
        else:
            ws.append([wd, datetime(d.year, d.month, d.day), zeit, anlass])
            ws.cell(row=ws.max_row, column=2).number_format = "DD.MM.YYYY"
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 60
    pfad = Path(pfad)
    wb.save(pfad)
    return pfad


def erzeuge_pdf(pfad, mit_gitter: bool = True, mit_farben: bool = False) -> Path:
    """PDF-Tabelle. mit_farben hinterlegt einzelne Zeilen farbig (wie im echten Programm), was
    pdfplumber fälschlich als kleine Tabellen erkennt."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    daten = [KOPFZEILE]
    for wd, d, zeit, anlass in _zeilen():
        if wd == "Ausblick":
            daten.append([wd])
        else:
            daten.append([wd, d.strftime("%d.%m.%Y") if d else "", zeit, anlass])
    tabelle = Table(daten, colWidths=[75, 70, 80, 280], repeatRows=1)
    stil = [("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if mit_gitter:
        stil.append(("GRID", (0, 0), (-1, -1), 0.5, colors.grey))
    if mit_farben:
        for zeile, farbe in ((3, colors.yellow), (9, colors.lightgreen), (10, colors.salmon), (14, colors.orange),
                             (15, colors.lightblue), (20, colors.yellow)):
            stil.append(("BACKGROUND", (0, zeile), (-1, zeile), farbe))
    tabelle.setStyle(TableStyle(stil))

    def fuss(canvas, _doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 30, FUSSZEILE)

    pfad = Path(pfad)
    SimpleDocTemplate(str(pfad), pagesize=A4).build([tabelle], onFirstPage=fuss, onLaterPages=fuss)
    return pfad


if __name__ == "__main__":
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    ziel.mkdir(parents=True, exist_ok=True)
    print(erzeuge_excel(ziel / "beispiel_programm.xlsx"))
    print(erzeuge_pdf(ziel / "beispiel_programm.pdf", mit_gitter=False, mit_farben=True))
