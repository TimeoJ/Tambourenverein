import copy
import tempfile
import unittest
from datetime import date
from pathlib import Path

from kmimport import exporter
from kmimport.config import STANDARD_CONFIG, lade_config
from kmimport.event_extractor import analysiere_zeile, teile_titel, zeilen_zu_termine
from kmimport.exporter import ExportFehler
from kmimport.filters import Filter, wende_filter_an
from kmimport.models import Termin
from kmimport.regeln import bestimme_kategorien, bestimme_terminart
from kmimport.session import ExportGesperrt, Sitzung
from kmimport.validator import FEHLER, OK, WARNUNG, pruefe, status
from kmimport.zeit import (interpretiere, naechster_wochentag, normalisiere_datum,
                           normalisiere_zeit, parse_datum)

import erzeuge_beispiele

HEUTE = date(2026, 10, 16)  # Freitag
CFG = copy.deepcopy(STANDARD_CONFIG)


class ZeitTests(unittest.TestCase):
    def pruefe(self, angabe, beginn, ende, notiz_enthaelt=None):
        z = interpretiere(angabe)
        self.assertEqual((z.beginn, z.ende), (beginn, ende), angabe)
        if notiz_enthaelt is None:
            self.assertEqual(z.notiz, "", angabe)
        else:
            self.assertIn(notiz_enthaelt, z.notiz, angabe)

    def test_bereich_mit_allen_schreibweisen(self):
        for angabe in ("20.00 - 22.00", "20:00-22:00", "20.00 – 22.00 Uhr", "20-22 Uhr", "20h00 - 22h00",
                       "20,00 bis 22,00", "20.00- 22.00", "20:00 - 22.00", "20.00-22:00"):
            self.pruefe(angabe, "20:00", "22:00")
        self.pruefe("8.45 - 13.00", "08:45", "13:00")
        self.pruefe("8:45-13:00", "08:45", "13:00")

    def test_spezialfaelle_gemaess_spezifikation(self):
        self.pruefe("???", "", "", "Originalzeit im Tätigkeitsprogramm unbekannt (???). Bitte prüfen.")
        self.pruefe("??? (15.55)", "15:55", "",
                    "Originaleintrag: ??? (15.55). Startzeit aus Klammer übernommen. Endzeit unbekannt. Bitte prüfen.")
        self.pruefe("ganzer Tag", "", "", "Originalangabe im Tätigkeitsprogramm: ganzer Tag.")
        self.pruefe("Vormittag", "", "", "Originalangabe im Tätigkeitsprogramm: Vormittag.")
        self.pruefe("Nachmittag", "", "", "Originalangabe im Tätigkeitsprogramm: Nachmittag.")
        self.pruefe("ab 11.00 Uhr", "11:00", "",
                    "Originalangabe im Tätigkeitsprogramm: ab 11.00 Uhr. Endzeit unbekannt.")
        self.pruefe("ca. 21.30", "21:30", "", "Originalangabe im Tätigkeitsprogramm: ca. 21.30. Endzeit unbekannt.")
        self.pruefe("15.32", "15:32", "",
                    "Im Original wurde nur eine einzelne Uhrzeit angegeben (15.32). Endzeit unbekannt.")
        self.pruefe("15:32", "15:32", "", "einzelne Uhrzeit")

    def test_ende_um_mitternacht(self):
        self.pruefe("19.00 - 00.00", "19:00", "23:59", "Ende im Original: 00.00 (Mitternacht), als 23:59 übernommen.")
        self.pruefe("23.00 - 24.00", "23:00", "23:59", "Ende im Original: 24.00 (Mitternacht)")
        self.assertEqual(interpretiere("19.00 - 24.00", mitternacht="00:00").ende, "00:00")

    def test_keine_angabe_und_ungueltig(self):
        self.pruefe(None, "", "", "keine Zeitangabe")
        self.pruefe("25.99", "", "", "nicht lesbar")

    def test_nie_zeiten_erfinden(self):
        for angabe in ("ganzer Tag", "Nachmittag", "???", "15.32", "ca. 21.30", "ab 11.00 Uhr"):
            self.assertEqual(interpretiere(angabe).ende, "", angabe)

    def test_zeit_normalisieren(self):
        for eingabe, erwartet in (("20.00", "20:00"), ("20:00", "20:00"), ("20,00", "20:00"), ("20h00", "20:00"),
                                  ("20 Uhr", "20:00"), ("20", "20:00"), ("8.5", None), ("8:5", None),
                                  ("25.00", None), ("", ""), ("abends", None)):
            self.assertEqual(normalisiere_zeit(eingabe), erwartet, eingabe)

    def test_datum_normalisieren(self):
        for eingabe, erwartet in (("4.11.26", "04.11.2026"), ("04.11.2026", "04.11.2026"),
                                  ("04-11-2026", "04.11.2026"), ("04/11/2026", "04.11.2026"),
                                  ("2026-11-04", "04.11.2026"), ("31.02.2026", None), ("morgen", None), ("", None)):
            self.assertEqual(normalisiere_datum(eingabe), erwartet, eingabe)
        self.assertEqual(parse_datum("heute", HEUTE), HEUTE)
        self.assertIsNone(parse_datum("", HEUTE))

    def test_naechster_mittwoch(self):
        self.assertEqual(naechster_wochentag(date(2026, 10, 16), 2), date(2026, 10, 21))
        self.assertEqual(naechster_wochentag(date(2026, 10, 21), 2), date(2026, 10, 28))  # heute zählt nicht


class ExtraktionTests(unittest.TestCase):
    def test_titel_und_information(self):
        self.assertEqual(teile_titel("Fasnachtsumzug Dagmersellen, Probelokal im Kostüm"),
                         ("Fasnachtsumzug Dagmersellen", "Probelokal im Kostüm"))
        self.assertEqual(teile_titel("Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm"),
                         ("Hirsmontag", "Schnitzelbanktour, Probelokal im Kostüm"))
        self.assertEqual(teile_titel("11. GV 2025"), ("11. GV 2025", ""))
        self.assertEqual(teile_titel("ZTPF in Langenthal BE (Festakt, Festumzug)"),
                         ("ZTPF in Langenthal BE", "Festakt, Festumzug"))
        self.assertEqual(
            teile_titel("Ständli (18:30 Uhr) Fahnenabgabe (19:30 Uhr) Uhr Log Bat 52 auf der Schützenwiese, "
                        "anschl. Nachtessen im Stadtsaal"),
            ("Ständli", "18:30 Uhr Fahnenabgabe (19:30 Uhr) Uhr Log Bat 52 auf der Schützenwiese, "
                        "anschl. Nachtessen im Stadtsaal"))

    def test_zeile_als_text_wochentag_zuerst(self):
        a = analysiere_zeile(["Freitag 10.01.2025 20.00 - 22.00 1. Probe 2025"])
        self.assertEqual((a.datum, a.wochentag, a.zeit, a.titel),
                         ((10, 1, 2025), "Freitag", "20.00 - 22.00", "1. Probe 2025"))

    def test_zeile_als_zellen(self):
        a = analysiere_zeile(["Sa", "22.02.2025", "18:00", "Wurlitzer-Plausch Zunzgen"])
        self.assertEqual((a.wochentag, a.zeit, a.titel), ("Sa", "18:00", "Wurlitzer-Plausch Zunzgen"))

    def test_andere_datumsformate_in_der_zeile(self):
        for text in ("Sa 22/02/2025 18.00 Plausch", "Sa 22-02-2025 18.00 Plausch", "Sa 2025-02-22 18.00 Plausch",
                     "Sa 22.2.25 18.00 Plausch"):
            a = analysiere_zeile([text])
            self.assertEqual((a.datum, a.zeit, a.titel), ((22, 2, 2025), "18.00", "Plausch"), text)

    def test_beginn_und_ende_in_getrennten_zellen(self):
        a = analysiere_zeile(["1. Probe 2025", "10.01.2025", "20:00", "22:00"])
        self.assertEqual((a.zeit, a.titel), ("20:00 - 22:00", "1. Probe 2025"))

    def test_leere_endzelle_ergibt_einzelzeit(self):
        a = analysiere_zeile(["Probe", "17.01.2025", "20:00", ""])
        self.assertEqual(a.zeit, "20:00")

    def test_titel_mit_zahl_wird_nicht_zur_zeit(self):
        a = analysiere_zeile(["Mi 05.03.2025 1. Probe nach den Ferien"])
        self.assertIsNone(a.zeit)
        self.assertEqual(a.titel, "1. Probe nach den Ferien")

    def test_zeile_ohne_datum_ist_kein_termin(self):
        self.assertIsNone(analysiere_zeile(["Ausblick"]))
        termine, protokoll = zeilen_zu_termine([["Wochentag", "Datum", "Zeit", "Anlass"], ["Ausblick"],
                                                ["irgendein Text ohne Datum"]], CFG)
        self.assertEqual(termine, [])
        self.assertEqual(protokoll, ["Ohne Datum übersprungen: irgendein Text ohne Datum"])

    def test_wochentag_stimmt_nicht(self):
        t, _ = zeilen_zu_termine([["Do", "11.11.2026", "20.00 - 22.00", "Probe"]], CFG)
        self.assertTrue(any("passt nicht zum Datum" in w for w in t[0].warnungen))
        t, _ = zeilen_zu_termine([["Mi", "11.11.2026", "20.00 - 22.00", "Probe"]], CFG)
        self.assertEqual(t[0].warnungen, [])

    def test_information_enthaelt_zusatz_und_notiz(self):
        t, _ = zeilen_zu_termine(
            [["Mo", "08.02.2027", "??? (19.55)", "Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm"]], CFG)
        self.assertEqual(t[0].name, "Hirsmontag")
        self.assertEqual(t[0].beginn, "19:55")
        self.assertEqual(
            t[0].information,
            "Schnitzelbanktour, Probelokal im Kostüm. Originaleintrag: ??? (19.55). "
            "Startzeit aus Klammer übernommen. Endzeit unbekannt. Bitte prüfen.")

    def test_fusszeile_mit_datum_ist_kein_termin(self):
        t, p = zeilen_zu_termine([["Freitag 10.01.2025 20.00 - 22.00 Probe"], ["Max Muster Seite 1 18.03.2025"]], CFG)
        self.assertEqual([x.name for x in t], ["Probe"])
        self.assertEqual(p, [])

    def test_keine_probe_ist_kein_termin(self):
        t, p = zeilen_zu_termine([["Freitag 18.04.2025 KARFREITAG KEINE PROBE"],
                                  ["Mittwoch 23.04.2025 20.00 - 22.00 Probe"]], CFG)
        self.assertEqual(len(t), 1)
        self.assertIn("keine probe", p[0])

    def test_folgezeile_wird_angehaengt(self):
        t, p = zeilen_zu_termine(
            [["Samstag 29.11.2025 09.00-13.00 Tambourenkonzert / Gönneranlass im Kirchgemeindehaus"],
             ["am Abend Tambourenwaggel (mit Ehemaligen), organisiert durch Tobi"],
             ["Ausblick"], ["irgendein Text"]], CFG)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].information,
                         "Folgezeile im Original: am Abend Tambourenwaggel (mit Ehemaligen), organisiert durch Tobi")
        self.assertTrue(any("Folgezeile" in w for w in t[0].warnungen))
        self.assertEqual(p[-1], "Ohne Datum übersprungen: irgendein Text")  # nach "Ausblick" nichts mehr anhängen
        cfg = dict(CFG, folgezeilen_anhaengen=False)
        t, p = zeilen_zu_termine([["Samstag 29.11.2025 09.00-13.00 Konzert"], ["am Abend Waggel"]], cfg)
        self.assertEqual(t[0].information, "")

    def test_zeilen_aus_dem_echten_programm(self):
        """Zeilen so, wie sie im echten Tätigkeitsprogramm (PDF-Text) stehen."""
        zeilen = [[z] for z in [
            "Tätigkeitsprogramm Tambourenverein Zofingen",
            "01. Januar - 1. August 2025",
            "Samstag 22.02.2025 18.00- 23.00 Wurlitzer-Plausch Zunzgen",
            "Montag 10.03.2025 18.30 - 24.00 Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm",
            "Dienstag 01.04.2025 17.30 - 21.00 Ständli (18:30 Uhr) Fahnenabgabe (19:30 Uhr) Uhr Log Bat 52 auf der "
            "Schützenwiese, anschl. Nachtessen im Stadtsaal",
            "Montag 28.04.2025 ganzer Tag Zürcher Sechseläuten mit MG Fislisbach (5 Tambouren)",
            "Donnerstag 29.05.2025 ab 11.00 Uhr Auffahrt, Familien Grillplausch Waldhaus Felli, Riken",
            "Sonntag 01.06.2025 15.32 Aargauischer Musiktag Sulz Marschmusikparade Stadtmusik Zofingen",
            "Sonntag 22.06.2025 ??? (15.55) Luzerner Kantonalmusikfest Sursee (evt. Marschparade mit MG St. Urban)",
            "Donnerstag 03.07.2025 ca. 21.30 Nach Zapfenstreich Bühne abräumen auf Thutplatz ca. 6 - 8 Personen "
            "(für Musikschule)",
            "Donnerstag 14.05.2026 Auffahrt",
            "Max Muster Seite 1 18.03.2025",
        ]]
        t, p = zeilen_zu_termine(zeilen, CFG)
        ergebnis = {x.name: (x.datum, x.beginn, x.ende) for x in t}
        self.assertEqual(len(t), 9)  # 12 Zeilen minus 2 Kopfzeilen minus 1 Fusszeile
        self.assertEqual(ergebnis["Wurlitzer-Plausch Zunzgen"], ("22.02.2025", "18:00", "23:00"))
        self.assertEqual(ergebnis["Hirsmontag"], ("10.03.2025", "18:30", "23:59"))
        self.assertEqual(ergebnis["Ständli"], ("01.04.2025", "17:30", "21:00"))
        self.assertEqual(ergebnis["Zürcher Sechseläuten mit MG Fislisbach"], ("28.04.2025", "", ""))
        self.assertEqual(ergebnis["Luzerner Kantonalmusikfest Sursee"], ("22.06.2025", "15:55", ""))
        self.assertEqual(ergebnis["Nach Zapfenstreich Bühne abräumen auf Thutplatz ca. 6 - 8 Personen"],
                         ("03.07.2025", "21:30", ""))
        self.assertEqual([x for x in t if x.name == "Auffahrt"][1].information,
                         "Im Tätigkeitsprogramm war keine Zeitangabe vorhanden. Bitte prüfen.")
        self.assertEqual(p, [])
        self.assertEqual(t[-1].datum, "14.05.2026")  # Fusszeile (18.03.2025) wurde nicht als Termin gelesen


class RegelTests(unittest.TestCase):
    def test_terminart(self):
        for name, art in [("Probe", "Probe"), ("Probesamstag", "Probe"), ("Generalprobe", "Probe"),
                          ("Fasnachtsumzug Dagmersellen", "Auftritt"), ("Ständli", "Auftritt"),
                          ("Ortsbürgerständli", "Auftritt"), ("11. GV 2025", "Sonstiges"),
                          ("Grillplausch", "Sonstiges"), ("Powerman Zofingen", ""),
                          ("Eidg. Musikfest Biel", ""), ("Luzerner Kantonalmusikfest Sursee", "")]:
            self.assertEqual(bestimme_terminart(name, CFG), art, name)

    def test_kuerzel_nur_als_ganzes_wort(self):
        self.assertEqual(bestimme_terminart("Gvxyz", CFG), "")
        self.assertEqual(bestimme_terminart("GV", CFG), "Sonstiges")

    def test_kategorien(self):
        self.assertEqual(bestimme_kategorien("Probe", CFG), "Probe")
        self.assertEqual(bestimme_kategorien("Fasnachtsumzug", CFG), "Fasnacht, Auftritt")
        self.assertEqual(bestimme_kategorien("GV 2026", CFG), "Verein")
        self.assertEqual(bestimme_kategorien("ZTPF in Langenthal BE", CFG), "Wettspiel")
        self.assertEqual(bestimme_kategorien("Unbekannt", CFG), "")


class ValidatorTests(unittest.TestCase):
    def basis(self, **kw):
        t = Termin(datum="04.11.2026", beginn="20:00", ende="22:00", name="Probe", terminart="Probe")
        for k, v in kw.items():
            setattr(t, k, v)
        return t

    def test_ok(self):
        self.assertEqual(status(pruefe(self.basis(), CFG)), OK)

    def test_fehlende_pflichtfelder_sind_fehler(self):
        for feld in ("datum", "beginn", "ende", "name"):
            self.assertEqual(status(pruefe(self.basis(**{feld: ""}), CFG)), FEHLER, feld)

    def test_ende_vor_beginn(self):
        self.assertEqual(status(pruefe(self.basis(beginn="22:00", ende="20:00"), CFG)), FEHLER)

    def test_ende_00_00_ist_mitternacht_mit_warnung(self):
        self.assertEqual(status(pruefe(self.basis(beginn="19:00", ende="00:00"), CFG)), WARNUNG)

    def test_ungueltige_terminart(self):
        self.assertEqual(status(pruefe(self.basis(terminart="Fest"), CFG)), FEHLER)

    def test_warnung_verschwindet_nach_pruefung(self):
        t = self.basis(warnungen=["etwas ist unklar"])
        self.assertEqual(status(pruefe(t, CFG)), WARNUNG)
        t.geprueft = True
        self.assertEqual(status(pruefe(t, CFG)), OK)


class FilterTests(unittest.TestCase):
    def setUp(self):
        daten = [("14.10.2026", "Probe", "Probe"), ("21.10.2026", "Probe", "Probe"),
                 ("05.12.2026", "Powerman Zofingen", ""), ("05.12.2026", "Aufbau", "Sonstiges"),
                 ("20.01.2027", "GV", "Sonstiges"), ("15.02.2027", "Konzert Zofingen", "Auftritt"),
                 ("", "Ohne Datum", "")]
        self.termine = [Termin(datum=d, name=n, terminart=a, beginn="20:00") for d, n, a in daten]

    def namen(self, **kw):
        sichtbar, meldungen = wende_filter_an(self.termine, Filter(**kw), HEUTE)
        return [t.name for t in sichtbar], meldungen

    def test_ohne_filter_ist_alles_sichtbar(self):
        namen, meldungen = self.namen()
        self.assertEqual(len(namen), 7)
        self.assertEqual(meldungen, [])

    def test_von_heute_entfernt_vergangenheit(self):
        namen, _ = self.namen(von="heute")
        self.assertNotIn("14.10.2026", [t.datum for t in wende_filter_an(self.termine, Filter(von="heute"), HEUTE)[0]])
        self.assertEqual(len(namen), 6)

    def test_zeitraum_von_bis_inklusive(self):
        namen, _ = self.namen(von="21.10.2026", bis="20.01.2027")
        self.assertEqual(namen, ["Probe", "Powerman Zofingen", "Aufbau", "GV", "Ohne Datum"])
        namen, _ = self.namen(von="05.12.2026", bis="05.12.2026")
        self.assertEqual(namen, ["Powerman Zofingen", "Aufbau", "Ohne Datum"])

    def test_datum_mit_anderen_schreibweisen(self):
        namen, _ = self.namen(von="21.10.26", bis="2027-01-20")
        self.assertEqual(len(namen), 5)

    def test_von_event_und_bis_event(self):
        namen, meldungen = self.namen(von_event="powerman", bis_event="gv")
        self.assertEqual(namen, ["Powerman Zofingen", "Aufbau", "GV", "Ohne Datum"])
        self.assertTrue(any("05.12.2026" in m for m in meldungen))

    def test_bis_event_ist_inklusive_und_gilt_bis_zum_ende_des_tages(self):
        namen, _ = self.namen(von="heute", bis_event="powerman")
        self.assertEqual(namen, ["Probe", "Powerman Zofingen", "Aufbau", "Ohne Datum"])

    def test_strengere_grenze_gewinnt(self):
        namen, meldungen = self.namen(von="01.01.2027", von_event="powerman")
        self.assertEqual(namen, ["GV", "Konzert Zofingen", "Ohne Datum"])
        self.assertTrue(any("späteres Von-Datum" in m or "spätere Von-Datum" in m for m in meldungen))
        namen, meldungen = self.namen(bis="01.12.2026", bis_event="gv")
        self.assertEqual(namen, ["Probe", "Probe", "Ohne Datum"])
        self.assertTrue(any("frühere Bis-Datum" in m for m in meldungen))

    def test_unbekanntes_event_und_ungueltiges_datum_begrenzen_nicht(self):
        namen, meldungen = self.namen(bis_event="Gibt es nicht", von="Quatsch")
        self.assertEqual(len(namen), 7)
        self.assertEqual(len(meldungen), 2)

    def test_start_nach_ende(self):
        namen, meldungen = self.namen(von="01.03.2027", bis="01.01.2027")
        self.assertEqual(namen, ["Ohne Datum"])
        self.assertTrue(any("nach dem Enddatum" in m for m in meldungen))

    def test_terminart(self):
        namen, _ = self.namen(arten=["Probe", "Auftritt"])
        self.assertEqual(namen, ["Probe", "Probe", "Konzert Zofingen"])
        namen, _ = self.namen(arten=[""])  # nur nicht erkannte
        self.assertEqual(namen, ["Powerman Zofingen", "Ohne Datum"])

    def test_namensfilter(self):
        namen, _ = self.namen(name_enthaelt="probe; konzert")
        self.assertEqual(namen, ["Probe", "Probe", "Konzert Zofingen"])
        namen, _ = self.namen(name_enthaelt_nicht="Probe, Zofingen")
        self.assertEqual(namen, ["Aufbau", "GV", "Ohne Datum"])


class ExportTests(unittest.TestCase):
    def test_testtermin_exakt_im_zielformat(self):
        text = exporter.csv_text([exporter.testtermin(CFG, HEUTE)], CFG)
        self.assertEqual(
            text,
            '"Datum";"Beginn";"Ende";"Name";"Raum";"Ort";"Treffpunkt";"Information";"Terminart";"Kategorien";"Verein"\r\n'
            '"21.10.2026";"20:00";"22:00";"Probe";"";"";"";"";"Probe";"Probe";"Tambourenverein Zofingen"\r\n')

    def test_umlaute_und_semikolon_im_text(self):
        t = Termin(datum="01.03.2027", beginn="12:30", ende="18:30", name="Ständli; Zürich",
                   information='Mit "Fahne"\nzweite Zeile', terminart="Auftritt")
        text = exporter.csv_text([t], CFG)
        self.assertIn('"Ständli; Zürich"', text)
        self.assertIn('"Mit ""Fahne"" zweite Zeile"', text)

    def schreibe(self, kodierung, name="Müller Köhler Bühne ÄÖÜ äöü ß é"):
        cfg = copy.deepcopy(CFG)
        cfg["csv"]["kodierung"] = kodierung
        t = Termin(datum="01.03.2027", beginn="12:30", ende="18:30", name=name, terminart="Auftritt")
        with tempfile.TemporaryDirectory() as tmp:
            return exporter.schreibe_csv(Path(tmp) / "x.csv", [t], cfg).read_bytes()

    def test_standard_ist_utf8_mit_bom_damit_excel_die_umlaute_richtig_zeigt(self):
        self.assertEqual(CFG["csv"]["kodierung"], "utf-8-sig")
        daten = self.schreibe(CFG["csv"]["kodierung"])
        self.assertTrue(daten.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(daten.count(b"\xef\xbb\xbf"), 1)
        text = daten.decode("utf-8-sig")
        self.assertTrue(text.startswith('"Datum"'))
        self.assertIn("Müller Köhler Bühne ÄÖÜ äöü ß é", text)
        self.assertIn("ä".encode("utf-8"), daten)  # C3 A4

    def test_utf8_ohne_bom(self):
        daten = self.schreibe("utf-8")
        self.assertFalse(daten.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Müller".encode("utf-8"), daten)

    def test_windows_1252(self):
        daten = self.schreibe("cp1252")
        self.assertIn(b"M\xfcller K\xf6hler B\xfchne \xc4\xd6\xdc \xe4\xf6\xfc \xdf \xe9", daten)
        self.assertEqual(daten.decode("cp1252").count("Müller"), 1)

    def test_nicht_darstellbares_zeichen_gibt_klare_fehlermeldung(self):
        with self.assertRaises(ExportFehler) as ctx:
            self.schreibe("cp1252", name="Łódź")
        self.assertIn("cp1252", str(ctx.exception))
        self.assertTrue(self.schreibe("utf-8-sig", name="Łódź"))  # in UTF-8 geht es

    def test_zeilenenden_bleiben_windows_stil(self):
        daten = self.schreibe("utf-8-sig")
        self.assertEqual(daten.count(b"\r\n"), 2)
        self.assertNotIn(b"\r\r\n", daten)

    def test_alte_config_wird_migriert(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "config.json"
            pfad.write_text('{"verein": "Mein Verein", "csv": {"kodierung": "utf-8"}}', encoding="utf-8")
            cfg = lade_config(pfad)
        self.assertEqual(cfg["csv"]["kodierung"], "utf-8-sig")
        self.assertEqual(cfg["verein"], "Mein Verein")
        self.assertEqual(cfg["ueberspringen"], ["keine probe"])  # neue Einstellungen kommen dazu


class QuellenTests(unittest.TestCase):
    """Excel und alle PDF-Varianten (Gitterlinien, ohne, farbig hinterlegte Zeilen) müssen dasselbe liefern."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        o = Path(cls.tmp.name)
        cls.dateien = {
            "xlsx": erzeuge_beispiele.erzeuge_excel(o / "p.xlsx"),
            "pdf_gitter": erzeuge_beispiele.erzeuge_pdf(o / "g.pdf", True),
            "pdf_ohne": erzeuge_beispiele.erzeuge_pdf(o / "o.pdf", False),
            "pdf_farbig": erzeuge_beispiele.erzeuge_pdf(o / "f.pdf", False, True),
            "pdf_farbig_gitter": erzeuge_beispiele.erzeuge_pdf(o / "fg.pdf", True, True),
        }
        cls.ergebnisse = {}
        for name, pfad in cls.dateien.items():
            s = Sitzung(copy.deepcopy(CFG), heute=HEUTE)
            s.datei_laden(pfad)
            cls.ergebnisse[name] = s

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def neu(self, quelle="xlsx"):
        s = Sitzung(copy.deepcopy(CFG), heute=HEUTE)
        s.datei_laden(self.dateien[quelle])
        return s

    def zeilen(self, s):
        return [(t.datum, t.beginn, t.ende, t.name, t.information, t.terminart, t.kategorien) for t in s.alle]

    def test_alle_quellen_liefern_dasselbe(self):
        ref = self.zeilen(self.ergebnisse["xlsx"])
        self.assertEqual(len(ref), 22)  # 25 Zeilen: Ausblick, KEINE PROBE und die Folgezeile sind keine Termine
        for name, s in self.ergebnisse.items():
            self.assertEqual(self.zeilen(s), ref, name)

    def test_fusszeile_und_ausblick_sind_keine_termine(self):
        for name, s in self.ergebnisse.items():
            namen = [t.name for t in s.alle]
            self.assertFalse(any("Seite" in n or "Ausblick" in n or "KEINE PROBE" in n for n in namen), name)
            self.assertNotIn("18.03.2025", [t.datum for t in s.alle], name)

    def test_zeitformate_mit_doppelpunkt_und_h(self):
        t = {x.datum: x for x in self.ergebnisse["xlsx"].alle}
        self.assertEqual((t["04.11.2026"].beginn, t["04.11.2026"].ende), ("20:30", "22:30"))
        self.assertEqual((t["15.01.2027"].beginn, t["15.01.2027"].ende), ("19:30", "23:00"))

    def test_vergangenheit_ist_gefiltert(self):
        s = self.neu()
        s.filter_anwenden(Filter(von="heute"))
        self.assertEqual(len(s.sichtbar), 21)
        self.assertNotIn("14.10.2026", [t.datum for t in s.sichtbar])

    def test_export_gesperrt_bis_alles_korrigiert(self):
        s = self.neu()
        s.filter_anwenden(Filter(von="heute"))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ExportGesperrt) as ctx:
                s.exportieren(Path(tmp) / "x.csv")
            self.assertEqual(len(ctx.exception.probleme), 7)
            fehler = [t.uid for t in s.sichtbar if s.status(t) == FEHLER]
            self.assertIsNone(s.zeit_setzen(fehler, "20.00-22.00"))  # Punkt statt Doppelpunkt
            self.assertEqual(s.zusammenfassung()[FEHLER], 0)
            ziel = s.exportieren(Path(tmp) / "x.csv")
            zeilen = ziel.read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual(len(zeilen), 1 + 21)
            self.assertIn("Jahreskonzert Stadtmusik Musterhausen", ziel.read_text(encoding="utf-8-sig"))
            self.assertIn("Ständli Altersheim", ziel.read_text(encoding="utf-8-sig"))

    def test_zeitraum_per_session(self):
        s = self.neu()
        s.filter_anwenden(Filter(von="01.12.2026", bis="31.01.2027"))
        self.assertEqual([t.datum for t in s.sichtbar], ["05.12.2026", "12.12.2026", "15.01.2027", "23.01.2027"])

    def test_bis_event_per_session(self):
        s = self.neu()
        s.filter_anwenden(Filter(von="heute", bis_event="Powerman"))
        self.assertEqual(s.sichtbar[-1].name, "Powerman Zofingen")
        self.assertEqual(len(s.sichtbar), 17)

    def test_dokument_zeitraum_und_leer_hinweis(self):
        s = self.neu()
        self.assertEqual(s.dokument_zeitraum(), ("14.10.2026", "14.01.2028"))
        s.filter_anwenden(Filter(von="01.01.2030"))
        self.assertEqual(s.sichtbar, [])
        self.assertIn("14.10.2026 bis 14.01.2028", s.leer_hinweis())

    def test_feld_bearbeiten_normalisiert_und_markiert_geprueft(self):
        s = self.neu()
        t = next(x for x in s.alle if x.name == "Auffahrt")
        self.assertEqual(s.status(t), FEHLER)  # Ende fehlt
        s.feld_setzen(t.uid, "ende", "17.00")
        self.assertEqual(t.ende, "17:00")
        self.assertEqual(s.status(t), OK)  # Warnung ist nach der Bearbeitung quittiert
        s.feld_setzen(t.uid, "datum", "24-04-2027")
        self.assertEqual(t.datum, "24.04.2027")

    def test_falsches_format_bleibt_als_fehler_sichtbar(self):
        s = self.neu()
        t = s.alle[0]
        s.feld_setzen(t.uid, "beginn", "abends")
        self.assertEqual(t.beginn, "abends")
        self.assertEqual(s.status(t), FEHLER)

    def test_nicht_unterstuetztes_format(self):
        with self.assertRaises(ValueError):
            Sitzung(copy.deepcopy(CFG), heute=HEUTE).datei_laden("datei.xls")

    def test_kodierung_setzen(self):
        s = self.neu()
        s.kodierung_setzen("cp1252")
        self.assertEqual(s.cfg["csv"]["kodierung"], "cp1252")
        with self.assertRaises(ValueError):
            s.kodierung_setzen("latin-99")


class ExcelZahlenzeitenUndUmlauteTests(unittest.TestCase):
    """Regressionstests: In Excel als Zahl getippte Zeiten (20.00 -> 20, 20.30 -> 20.3)
    und zerlegte Umlaute (a + Trema) aus PDFs/Excel."""

    def excel(self, zeilen, kopf=("Datum", "Zeit", "Anlass")):
        import datetime as dt
        import openpyxl
        from kmimport import parser_excel

        wb = openpyxl.Workbook()
        ws = wb.active
        if kopf:
            ws.append(list(kopf))
        for zeile in zeilen:
            ws.append(zeile)
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "z.xlsx"
            wb.save(pfad)
            termine, _ = parser_excel.lese_termine(pfad, copy.deepcopy(CFG))
        return termine

    def test_zeit_als_zahl_in_zeitspalte(self):
        import datetime as dt
        d = dt.datetime(2026, 11, 4)
        t = self.excel([[d, 20.0, "A"], [d, 20.3, "B"], [d, 8.45, "C"], [d, "20.00 - 22.00", "D"],
                        [d, dt.time(20, 0), "E"], [d, 0.8333333333, "F"]])
        self.assertEqual([(x.name, x.beginn, x.ende) for x in t], [
            ("A", "20:00", ""), ("B", "20:30", ""), ("C", "08:45", ""), ("D", "20:00", "22:00"),
            ("E", "20:00", ""), ("F", "20:00", "")])

    def test_beginn_und_ende_als_zahlen(self):
        import datetime as dt
        t = self.excel([[dt.datetime(2026, 11, 4), 19.3, 22.0, "Probe"]],
                       kopf=("Datum", "Beginn", "Ende", "Anlass"))
        self.assertEqual((t[0].beginn, t[0].ende), ("19:30", "22:00"))

    def test_zahlen_ausserhalb_von_zeitspalten_bleiben_zahlen(self):
        import datetime as dt
        t = self.excel([[dt.datetime(2026, 11, 4), "20.00 - 22.00", 2026.0]], kopf=("Datum", "Zeit", "Anlass"))
        self.assertEqual(t[0].name, "2026")

    def test_zerlegte_umlaute_werden_zusammengesetzt(self):
        import unicodedata
        zerlegt = unicodedata.normalize("NFD", "Zürcher Sechseläuten (Gönner)")
        self.assertNotEqual(zerlegt, "Zürcher Sechseläuten (Gönner)")
        t, _ = zeilen_zu_termine([[f"Mo 28.04.2027 20.00 - 22.00 {zerlegt}"]], copy.deepcopy(CFG))
        self.assertEqual(t[0].name, "Zürcher Sechseläuten")
        self.assertEqual(t[0].information, "Gönner")

    def test_csv_enthaelt_nur_zusammengesetzte_umlaute_und_hat_bom(self):
        import unicodedata
        t = Termin(datum="01.03.2027", beginn="12:30", ende="18:30",
                   name=unicodedata.normalize("NFD", "Ständli Zürich"), terminart="Auftritt")
        with tempfile.TemporaryDirectory() as tmp:
            pfad = exporter.schreibe_csv(Path(tmp) / "x.csv", [t], copy.deepcopy(CFG))
            daten = pfad.read_bytes()
        self.assertTrue(daten.startswith(b"\xef\xbb\xbf"))           # UTF-8 mit BOM (Excel erkennt Umlaute)
        text = daten.decode("utf-8-sig")
        self.assertIn("Ständli Zürich", text)
        self.assertEqual(text, unicodedata.normalize("NFC", text))
        self.assertIn("Ständli".encode("utf-8"), daten)               # ä = C3 A4, kein "Ã¤"


if __name__ == "__main__":
    unittest.main()
