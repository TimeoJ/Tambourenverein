"""Prüft die Verdrahtung der GUI mit Attrappen (Mocks) – es öffnet sich kein Fenster.

Das ersetzt keinen Blick auf die echte Oberfläche, fängt aber Tippfehler und falsche Aufrufe
zwischen GUI und Logik ab, auch auf Rechnern ohne Tkinter/CustomTkinter.
"""

import copy
import importlib
import sys
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import erzeuge_beispiele
from kmimport.config import STANDARD_CONFIG
from kmimport.filters import Filter
from kmimport.session import Sitzung

HEUTE = date(2026, 10, 16)


class _CTk:
    """Ersatz für ctk.CTk: jedes Attribut ist ein Mock."""

    def __init__(self, *a, **k):
        self._m = mock.MagicMock()

    def __getattr__(self, name):
        return getattr(self.__dict__["_m"], name)


def _modul(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    return m


def _variable(value=""):
    return mock.MagicMock(get=mock.MagicMock(return_value=value))


class GuiVerdrahtung(unittest.TestCase):
    def setUp(self):
        self.ctk = _modul("customtkinter", CTk=_CTk)
        self.ctk.__getattr__ = lambda name: mock.MagicMock()  # alle anderen Widgets
        self.tk = _modul("tkinter", StringVar=_variable, BooleanVar=_variable, TclError=Exception)
        self.ttk = mock.MagicMock()
        self.filedialog = mock.MagicMock()
        self.messagebox = mock.MagicMock()
        self.tk.ttk, self.tk.filedialog, self.tk.messagebox = self.ttk, self.filedialog, self.messagebox
        stubs = {"customtkinter": self.ctk, "tkinter": self.tk, "tkinter.ttk": self.ttk,
                 "tkinter.filedialog": self.filedialog, "tkinter.messagebox": self.messagebox}
        patcher = mock.patch.dict(sys.modules, stubs)
        patcher.start()
        self.addCleanup(patcher.stop)
        sys.modules.pop("kmimport.gui", None)
        self.addCleanup(sys.modules.pop, "kmimport.gui", None)
        self.gui = importlib.import_module("kmimport.gui")

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.excel = erzeuge_beispiele.erzeuge_excel(Path(self.tmp.name) / "p.xlsx")

        self.app = self.gui.App()
        self.app.s = Sitzung(copy.deepcopy(STANDARD_CONFIG), heute=HEUTE)
        self.app.s.filter = Filter(von="16.10.2026")
        self.app.tree = mock.MagicMock()
        self.app.tree.exists.return_value = False  # frisch geleerte Tabelle
        self.app.var_von.get.return_value = "heute"
        self.app.var_bis.get.return_value = ""
        self.app.cb_von_event.get.return_value = ""
        self.app.cb_bis_event.get.return_value = ""

    def test_laden_fuellt_tabelle_und_statuszeile(self):
        self.app._laden(str(self.excel))
        self.assertEqual(self.app.tree.insert.call_count, 21)
        self.messagebox.showerror.assert_not_called()
        self.assertIn("21 von 22 Terminen sichtbar", self.app.var_status.set.call_args[0][0])

    def test_laden_mit_falschem_format_zeigt_fehler(self):
        self.app._laden("datei.xls")
        self.messagebox.showerror.assert_called_once()

    def test_filter_zeitraum(self):
        self.app._laden(str(self.excel))
        self.app.tree.insert.reset_mock()
        self.app.var_von.get.return_value = "01.12.2026"
        self.app.var_bis.get.return_value = "31.01.2027"
        self.app._filter_anwenden()
        self.assertEqual(self.app.tree.insert.call_count, 4)

    def test_filter_event_terminart_und_name(self):
        self.app._laden(str(self.excel))
        self.app.tree.insert.reset_mock()
        self.app.cb_bis_event.get.return_value = "Powerman"
        self.app._filter_anwenden()
        self.assertEqual(self.app.tree.insert.call_count, 17)
        self.app.tree.insert.reset_mock()
        self.app.var_name_aus.get.return_value = "Probe"
        self.app._filter_anwenden()
        self.assertEqual(self.app.tree.insert.call_count, 17 - 6)  # 6 Proben bis dahin (Probesamstag/-sonntag inklusive)
        self.app.tree.insert.reset_mock()
        self.app.var_name_aus.get.return_value = ""
        self.app.var_arten["Probe"].get.return_value = False  # Terminart Probe abwählen
        self.app._filter_anwenden()
        self.assertEqual(self.app.tree.insert.call_count, 17 - 6)

    def test_ganzes_dokument_und_zuruecksetzen(self):
        self.app._laden(str(self.excel))
        self.app._ganzes_dokument()
        self.app.var_von.set.assert_called_with("14.10.2026")
        self.app.var_bis.set.assert_called_with("14.01.2028")
        self.app._filter_zuruecksetzen()
        self.app.var_bis.set.assert_called_with("")

    def test_leere_tabelle_erklaert_sich(self):
        self.app._laden(str(self.excel))
        self.app.var_von.get.return_value = "01.01.2030"
        self.app._filter_anwenden()
        self.assertIn("14.10.2026 bis 14.01.2028", self.messagebox.showinfo.call_args[0][1])

    def test_zelle_bearbeiten(self):
        self.app._laden(str(self.excel))
        t = next(x for x in self.app.s.sichtbar if x.name == "Auffahrt")
        self.app.tree.exists.return_value = True  # die Zeile steht bereits in der Tabelle
        feld = self.ttk.Entry.return_value
        feld.get.return_value = "17.00"
        self.app.tree.bbox.return_value = (1, 2, 100, 20)
        self.app._bearbeite(str(t.uid), "ende", "#4")
        self.assertIs(self.app._editor, feld)
        self.app._edit_bestaetigen()
        self.assertEqual(t.ende, "17:00")
        self.assertIsNone(self.app._editor)
        self.app.tree.item.assert_called()

    def test_alle_fehler_auswaehlen(self):
        self.app._laden(str(self.excel))
        self.app._fehler_auswaehlen()
        gewaehlt = self.app.tree.selection_set.call_args[0][0]
        self.assertEqual(len(gewaehlt), 7)

    def test_export_ist_gesperrt_solange_fehler_da_sind(self):
        self.app._laden(str(self.excel))
        self.app._exportieren()
        self.messagebox.showerror.assert_called_once()
        self.assertEqual(self.messagebox.showerror.call_args[0][0], "Export gesperrt")
        self.filedialog.asksaveasfilename.assert_not_called()

    def korrigiere_und_exportiere(self):
        self.app._laden(str(self.excel))
        for t in self.app.s.sichtbar:
            if self.app.s.status(t) == "error":
                self.app.s.zeit_setzen([t.uid], "20:00-22:00")
        ziel = Path(self.tmp.name) / "out.csv"
        self.filedialog.asksaveasfilename.return_value = str(ziel)
        self.app._exportieren()
        return ziel

    def test_export_nach_korrektur_mit_bom(self):
        ziel = self.korrigiere_und_exportiere()
        self.messagebox.showerror.assert_not_called()
        daten = ziel.read_bytes()
        self.assertTrue(daten.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(len(daten.decode("utf-8-sig").splitlines()), 22)

    def test_export_mit_gewaehltem_zeichensatz(self):
        self.app.var_kodierung.get.return_value = "Windows-1252 (ANSI)"
        ziel = self.korrigiere_und_exportiere()
        self.assertIn("Ständli".encode("cp1252"), ziel.read_bytes())
        self.assertNotIn(b"\xc3\xa4", ziel.read_bytes())

    def test_vorschau_und_testcsv(self):
        self.app._laden(str(self.excel))
        self.app._vorschau_aktualisieren()
        eingefuegt = self.app.txt_vorschau.insert.call_args[0][1]
        self.assertTrue(eingefuegt.startswith('"Datum";"Beginn"'))
        ziel = Path(self.tmp.name) / "t.csv"
        self.filedialog.asksaveasfilename.return_value = str(ziel)
        self.app._test_csv()
        self.assertEqual(len(ziel.read_text(encoding="utf-8-sig").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
