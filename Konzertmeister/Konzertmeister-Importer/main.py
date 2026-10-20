"""Konzertmeister-Importer.

  python main.py                      -> GUI starten
  python main.py --test               -> Test-CSV (Probe am kommenden Mittwoch 20:00-22:00)
  python main.py datei.pdf [Optionen] -> ohne GUI direkt eine CSV erzeugen

Beispiel:  python main.py programm.pdf --von 01.11.2026 --bis 31.12.2026 -o output/import.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kmimport.exporter import KODIERUNGEN, ExportFehler
from kmimport.filters import Filter
from kmimport.session import ExportGesperrt, Sitzung
from kmimport.validator import FEHLER, WARNUNG


def kommandozeile(args) -> int:
    s = Sitzung()
    if args.kodierung:
        s.kodierung_setzen(args.kodierung)

    if args.test:
        pfad = Path(args.ausgabe) if args.ausgabe else s.ausgabe_ordner() / "test_import.csv"
        pfad, text = s.test_csv_schreiben(pfad)
        print(text)
        print(f"Geschrieben: {pfad}")
        return 0

    s.datei_laden(args.datei)
    if args.alles:
        von = ""
    elif args.von is not None:
        von = args.von
    else:  # ohne Angabe: ab heute, ausser es ist ein Von-Event gesetzt
        von = "" if args.von_event else s.filter.von
    f = Filter(
        von=von, bis="" if args.alles else (args.bis or ""),
        von_event=args.von_event or "", bis_event=args.bis_event or "",
        arten=[a.strip() for a in args.arten.split(",")] if args.arten else None,
        name_enthaelt=args.name_enthaelt or "", name_enthaelt_nicht=args.name_enthaelt_nicht or "",
    )
    meldungen = s.filter_anwenden(f)
    for zeile in s.protokoll + meldungen:
        print(zeile)
    print()
    for t in s.sichtbar:
        st = {FEHLER: "FEHLER ", WARNUNG: "PRÜFEN ", "ok": "OK     "}[s.status(t)]
        hinweis = "; ".join(m.text for m in s.meldungen(t))
        print(f"{st} {t.datum} {t.beginn or '--:--'}-{t.ende or '--:--'} {t.terminart or '?':<9} {t.name}"
              + (f"   [{hinweis}]" if hinweis else ""))
    z = s.zusammenfassung()
    print(f"\n{z['gesamt']} Termine: {z['ok']} OK, {z['warn']} prüfen, {z['error']} Fehler")
    if s.leer_hinweis():
        print(s.leer_hinweis())

    ziel = Path(args.ausgabe) if args.ausgabe else s.ausgabe_ordner() / "konzertmeister_import.csv"
    try:
        s.exportieren(ziel)
    except ExportGesperrt as e:
        print("\nExport gesperrt, bitte zuerst korrigieren (am einfachsten in der GUI: python main.py):")
        for p in e.probleme:
            print("  -", p)
        return 2
    except ExportFehler as e:
        print(f"\nExport fehlgeschlagen: {e}")
        return 3
    print(f"\nCSV geschrieben: {ziel}  (Kodierung: {s.cfg['csv']['kodierung']})")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datei", nargs="?", help="PDF- oder Excel-Datei (ohne Angabe startet die GUI)")
    p.add_argument("--von", "--ab", dest="von", help="Startdatum (TT.MM.JJJJ, Standard: heute)")
    p.add_argument("--bis", "--bis-datum", dest="bis", help="Enddatum, inklusive (TT.MM.JJJJ)")
    p.add_argument("--von-event", help="Start am Tag des ersten Termins, dessen Name diesen Text enthält")
    p.add_argument("--bis-event", help="Ende (bis und mit) am Tag des ersten Termins mit diesem Text im Namen")
    p.add_argument("--alles", action="store_true", help="keine Datumsgrenzen (auch Vergangenes exportieren)")
    p.add_argument("--arten", help="nur diese Terminarten, z. B. 'Probe,Auftritt' (leer = nicht erkannt)")
    p.add_argument("--name-enthaelt", help="nur Termine, deren Name einen dieser Begriffe enthält (Komma)")
    p.add_argument("--name-enthaelt-nicht", help="Termine mit diesen Begriffen im Namen weglassen (Komma)")
    p.add_argument("--kodierung", choices=sorted(KODIERUNGEN.values()),
                   help="Zeichensatz der CSV (Standard laut config.json: utf-8-sig)")
    p.add_argument("-o", "--ausgabe", help="Ziel-CSV")
    p.add_argument("--test", action="store_true", help="Test-CSV mit einer Probe erzeugen")
    args = p.parse_args(argv)

    if args.test or args.datei:
        return kommandozeile(args)

    try:
        from kmimport.gui import starte_gui
    except ModuleNotFoundError as e:
        print(f"Für die GUI fehlt ein Paket: {e.name}\nInstallation: pip install -r requirements.txt")
        return 1
    starte_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
