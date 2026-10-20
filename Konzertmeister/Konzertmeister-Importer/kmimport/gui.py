"""GUI mit CustomTkinter: Import -> Prüfung & Filter -> CSV-Vorschau & Export.

Die ganze Logik steckt in kmimport.session.Sitzung; hier ist nur die Oberfläche.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from .config import PROJEKT_ORDNER, lade_config, speichere_config
from .exporter import KODIERUNGEN, ExportFehler
from .filters import Filter
from .session import ExportGesperrt, Sitzung
from .validator import FEHLER, OK, WARNUNG
from .zeit import heute_text

TAB_IMPORT = "1 · Import"
TAB_PRUEFUNG = "2 · Prüfung & Filter"
TAB_EXPORT = "3 · CSV-Vorschau & Export"

# (Schlüssel, Überschrift, Breite)
SPALTEN = [
    ("status", "Status", 85),
    ("datum", "Datum", 90),
    ("beginn", "Beginn", 60),
    ("ende", "Ende", 60),
    ("terminart", "Terminart", 95),
    ("name", "Name", 230),
    ("ort", "Ort", 110),
    ("information", "Information", 320),
    ("kategorien", "Kategorien", 130),
    ("hinweis", "Hinweis", 320),
]
EDITIERBAR = {"datum", "beginn", "ende", "terminart", "name", "ort", "information", "kategorien"}
STATUS_TEXT = {OK: "✔ OK", WARNUNG: "⚠ Prüfen", FEHLER: "✖ Fehler"}
NICHT_ERKANNT = "(nicht erkannt)"


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.title("Konzertmeister-Importer")
        self.geometry("1320x800")
        self.minsize(1050, 620)

        self.s = Sitzung()
        self._editor = None
        self._editor_ziel = ("", "")

        self.var_verein = tk.StringVar(value=self.s.cfg.get("verein", ""))
        self.var_von = tk.StringVar(value=self.s.filter.von)
        self.var_bis = tk.StringVar(value="")
        self.var_name_ein = tk.StringVar(value="")
        self.var_name_aus = tk.StringVar(value="")
        self.var_arten = {}
        self.var_kodierung = tk.StringVar(value=self._kodierung_label(self.s.cfg["csv"].get("kodierung", "")))
        self.var_status = tk.StringVar(value="Noch keine Datei geladen.")

        self.tabs = ctk.CTkTabview(self, command=self._tab_gewechselt)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self._baue_import(self.tabs.add(TAB_IMPORT))
        self._baue_pruefung(self.tabs.add(TAB_PRUEFUNG))
        self._baue_export(self.tabs.add(TAB_EXPORT))

        ctk.CTkLabel(self, textvariable=self.var_status, anchor="w").pack(fill="x", padx=14, pady=(4, 8))

    @staticmethod
    def _kodierung_label(kodierung: str) -> str:
        for label, code in KODIERUNGEN.items():
            if code == kodierung.lower():
                return label
        return next(iter(KODIERUNGEN))

    # ------------------------------------------------------------------ Tab 1: Import
    def _baue_import(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        kopf = ctk.CTkFrame(tab)
        kopf.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(kopf, text="Tätigkeitsprogramm laden", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 4))
        ctk.CTkButton(kopf, text="PDF oder Excel auswählen …", command=self._datei_waehlen).grid(
            row=1, column=0, padx=10, pady=(0, 10))
        self.lbl_datei = ctk.CTkLabel(kopf, text="(keine Datei gewählt)", anchor="w")
        self.lbl_datei.grid(row=1, column=1, sticky="w", padx=6, pady=(0, 10))

        einst = ctk.CTkFrame(tab)
        einst.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(einst, text="Verein (Spalte «Verein» in der CSV):").grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkEntry(einst, textvariable=self.var_verein, width=260).grid(row=0, column=1, padx=6)
        ctk.CTkButton(einst, text="Einstellungen speichern", width=170, command=self._einstellungen_speichern).grid(
            row=0, column=2, padx=10)
        ctk.CTkButton(einst, text="Regeln neu laden", width=140, command=self._regeln_neu_laden).grid(
            row=0, column=3, padx=0)
        ctk.CTkLabel(
            einst, text=f"Regeln für Terminart und Kategorien: {PROJEKT_ORDNER / 'config.json'}",
            text_color=("gray35", "gray65")).grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 10))

        test = ctk.CTkFrame(tab)
        test.grid(row=2, column=0, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(test, text="Import in Konzertmeister zuerst mit einer Testzeile ausprobieren:").grid(
            row=0, column=0, padx=10, pady=10)
        ctk.CTkButton(test, text="Test-CSV erzeugen (Probe, nächster Mittwoch 20:00–22:00)",
                      command=self._test_csv).grid(row=0, column=1, padx=6)

        prot = ctk.CTkFrame(tab)
        prot.grid(row=3, column=0, sticky="nsew", padx=6, pady=6)
        prot.grid_columnconfigure(0, weight=1)
        prot.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(prot, text="Protokoll (übersprungene Zeilen, angehängte Folgezeilen)").grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.txt_protokoll = ctk.CTkTextbox(prot, state="disabled")
        self.txt_protokoll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ------------------------------------------------------------------ Tab 2: Prüfung
    def _baue_pruefung(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        filt = ctk.CTkFrame(tab)
        filt.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))

        # Zeile 1: Zeitraum
        ctk.CTkLabel(filt, text="Zeitraum – Von:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(10, 4), pady=(8, 4), sticky="w")
        e_von = ctk.CTkEntry(filt, textvariable=self.var_von, width=105, placeholder_text="TT.MM.JJJJ")
        e_von.grid(row=0, column=1, pady=(8, 4))
        ctk.CTkLabel(filt, text="Bis:").grid(row=0, column=2, padx=(14, 4), pady=(8, 4))
        e_bis = ctk.CTkEntry(filt, textvariable=self.var_bis, width=105, placeholder_text="TT.MM.JJJJ")
        e_bis.grid(row=0, column=3, pady=(8, 4))
        ctk.CTkLabel(filt, text="(beide inklusive, leer = keine Grenze)", text_color=("gray35", "gray65")).grid(
            row=0, column=4, padx=10, pady=(8, 4), sticky="w")
        ctk.CTkButton(filt, text="Ab heute", width=90, command=self._ab_heute).grid(row=0, column=5, padx=4, pady=(8, 4))
        ctk.CTkButton(filt, text="Ganzes Dokument", width=130, command=self._ganzes_dokument).grid(
            row=0, column=6, padx=4, pady=(8, 4))
        for e in (e_von, e_bis):
            e.bind("<Return>", lambda ev: self._filter_anwenden())

        # Zeile 2: Events als Grenze
        ctk.CTkLabel(filt, text="Von Event:").grid(row=1, column=0, padx=(10, 4), pady=4, sticky="w")
        self.cb_von_event = ctk.CTkComboBox(filt, values=[""], width=300)
        self.cb_von_event.set("")
        self.cb_von_event.grid(row=1, column=1, columnspan=3, pady=4, sticky="w")
        ctk.CTkLabel(filt, text="Bis und mit Event:").grid(row=1, column=4, padx=(14, 4), pady=4, sticky="e")
        self.cb_bis_event = ctk.CTkComboBox(filt, values=[""], width=300)
        self.cb_bis_event.set("")
        self.cb_bis_event.grid(row=1, column=5, columnspan=2, pady=4, sticky="w")

        # Zeile 3: Terminart und Name
        ctk.CTkLabel(filt, text="Terminart:").grid(row=2, column=0, padx=(10, 4), pady=4, sticky="w")
        arten = ctk.CTkFrame(filt, fg_color="transparent")
        arten.grid(row=2, column=1, columnspan=3, sticky="w")
        for art in list(self.s.cfg.get("terminart_regeln", {})) + [NICHT_ERKANNT]:
            var = tk.BooleanVar(value=True)
            self.var_arten[art] = var
            ctk.CTkCheckBox(arten, text=art, variable=var, width=20).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(filt, text="Name enthält:").grid(row=2, column=4, padx=(14, 4), pady=4, sticky="e")
        e_ein = ctk.CTkEntry(filt, textvariable=self.var_name_ein, width=200, placeholder_text="z. B. Probe, Konzert")
        e_ein.grid(row=2, column=5, pady=4, sticky="w")
        ctk.CTkLabel(filt, text="enthält nicht:").grid(row=2, column=6, padx=(10, 4), pady=4, sticky="e")
        e_aus = ctk.CTkEntry(filt, textvariable=self.var_name_aus, width=200, placeholder_text="z. B. Probe")
        e_aus.grid(row=2, column=7, pady=4, sticky="w")
        for e in (e_ein, e_aus):
            e.bind("<Return>", lambda ev: self._filter_anwenden())

        ctk.CTkButton(filt, text="Filter anwenden", width=130, command=self._filter_anwenden).grid(
            row=0, column=7, rowspan=2, padx=10, pady=4, sticky="e")
        ctk.CTkButton(filt, text="Zurücksetzen", width=110, fg_color="gray50", hover_color="gray40",
                      command=self._filter_zuruecksetzen).grid(row=0, column=8, rowspan=2, padx=(0, 10), pady=4)

        rahmen = ctk.CTkFrame(tab)
        rahmen.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        rahmen.grid_columnconfigure(0, weight=1)
        rahmen.grid_rowconfigure(0, weight=1)

        stil = ttk.Style(self)
        try:
            stil.theme_use("clam")
        except tk.TclError:
            pass
        stil.configure("Treeview", rowheight=26, background="#ffffff", fieldbackground="#ffffff",
                       foreground="#000000")
        stil.configure("Treeview.Heading", font=("TkDefaultFont", 10, "bold"))
        stil.map("Treeview", background=[("selected", "#3b78c4")], foreground=[("selected", "#ffffff")])

        self.tree = ttk.Treeview(rahmen, columns=[k for k, _, _ in SPALTEN], show="headings",
                                 selectmode="extended")
        for key, titel, breite in SPALTEN:
            self.tree.heading(key, text=titel)
            self.tree.column(key, width=breite, minwidth=50, anchor="w", stretch=False)
        self.tree.tag_configure(OK, background="#d9f2d9")
        self.tree.tag_configure(WARNUNG, background="#fff3c4")
        self.tree.tag_configure(FEHLER, background="#f8d0d0")
        ys = ttk.Scrollbar(rahmen, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(rahmen, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        ys.grid(row=0, column=1, sticky="ns", pady=(6, 0))
        xs.grid(row=1, column=0, sticky="ew", padx=(6, 0))
        self.tree.bind("<Double-1>", self._doppelklick)
        self.tree.bind("<Button-1>", lambda e: self._edit_bestaetigen())
        self.tree.bind("<MouseWheel>", lambda e: self._edit_bestaetigen())

        leiste = ctk.CTkFrame(tab)
        leiste.grid(row=2, column=0, sticky="ew", padx=6, pady=(4, 6))
        ctk.CTkLabel(leiste, text="Doppelklick = Zelle bearbeiten.   Auswahl:").pack(side="left", padx=10, pady=8)
        for text, befehl in (("Alle Fehler auswählen", self._fehler_auswaehlen),
                             ("Beginn/Ende setzen …", self._zeit_setzen),
                             ("Als geprüft markieren", self._als_geprueft),
                             ("Zeile löschen", self._loeschen)):
            ctk.CTkButton(leiste, text=text, width=150, command=befehl).pack(side="left", padx=4)
        ctk.CTkButton(leiste, text="+ Neuer Termin", width=130, command=self._neuer_termin).pack(side="right", padx=10)
        ctk.CTkLabel(leiste, text="✔ OK   ⚠ Prüfen   ✖ Fehler (blockiert den Export)",
                     text_color=("gray35", "gray65")).pack(side="right", padx=10)

    # ------------------------------------------------------------------ Tab 3: Export
    def _baue_export(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        leiste = ctk.CTkFrame(tab)
        leiste.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ctk.CTkButton(leiste, text="Vorschau aktualisieren", width=170, command=self._vorschau_aktualisieren).pack(
            side="left", padx=10, pady=10)
        self.lbl_export = ctk.CTkLabel(leiste, text="")
        self.lbl_export.pack(side="left", padx=10)
        ctk.CTkButton(leiste, text="Konzertmeister-CSV exportieren …", command=self._exportieren).pack(
            side="right", padx=10)
        ctk.CTkOptionMenu(leiste, values=list(KODIERUNGEN), variable=self.var_kodierung, width=250,
                          command=self._kodierung_gewaehlt).pack(side="right", padx=4)
        ctk.CTkLabel(leiste, text="Zeichensatz:").pack(side="right", padx=(10, 2))
        self.txt_vorschau = ctk.CTkTextbox(tab, wrap="none", font=ctk.CTkFont(family="Courier", size=12),
                                           state="disabled")
        self.txt_vorschau.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        ctk.CTkLabel(
            tab, anchor="w", text_color=("gray35", "gray65"),
            text="Umlaute sehen in Excel falsch aus (z. B. «Ã¤» statt «ä»)? Dann «UTF-8 mit BOM» wählen. "
                 "Zeigt Konzertmeister sie nach dem Import falsch an, «Windows-1252 (ANSI)» probieren."
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))

    # ------------------------------------------------------------------ Aktionen: Import
    def _datei_waehlen(self) -> None:
        eingabe = PROJEKT_ORDNER / "input"
        pfad = filedialog.askopenfilename(
            title="Tätigkeitsprogramm wählen",
            initialdir=str(eingabe if eingabe.exists() else PROJEKT_ORDNER),
            filetypes=[("PDF oder Excel", "*.pdf *.xlsx *.xlsm"), ("PDF", "*.pdf"),
                       ("Excel", "*.xlsx *.xlsm"), ("Alle Dateien", "*.*")])
        if pfad:
            self._laden(pfad)

    def _laden(self, pfad: str) -> None:
        self._verein_uebernehmen()
        self.s.filter = self._filter_lesen()  # Einstellungen aus der Filterleiste gelten auch für die neue Datei
        try:
            self.s.datei_laden(pfad)
        except Exception as fehler:  # Anzeige für den Benutzer
            messagebox.showerror("Datei konnte nicht gelesen werden", str(fehler))
            return
        self.lbl_datei.configure(text=str(pfad))
        self._protokoll_zeigen()
        self._events_aktualisieren()
        self._tabelle_fuellen()
        self.tabs.set(TAB_PRUEFUNG)

    def _protokoll_zeigen(self) -> None:
        self.txt_protokoll.configure(state="normal")
        self.txt_protokoll.delete("1.0", "end")
        self.txt_protokoll.insert("end", "\n".join(self.s.protokoll))
        self.txt_protokoll.configure(state="disabled")

    def _verein_uebernehmen(self) -> None:
        self.s.cfg["verein"] = self.var_verein.get().strip()

    def _einstellungen_speichern(self) -> None:
        self._verein_uebernehmen()
        try:
            speichere_config(self.s.cfg)
        except OSError as fehler:
            messagebox.showerror("Speichern fehlgeschlagen", str(fehler))
            return
        messagebox.showinfo("Gespeichert", "Einstellungen (Verein, Zeichensatz, Regeln) wurden in config.json gespeichert.")

    def _regeln_neu_laden(self) -> None:
        try:
            self.s.cfg = lade_config()
        except (OSError, ValueError) as fehler:
            messagebox.showerror("config.json fehlerhaft", str(fehler))
            return
        self.var_verein.set(self.s.cfg.get("verein", ""))
        self.var_kodierung.set(self._kodierung_label(self.s.cfg["csv"].get("kodierung", "")))
        messagebox.showinfo("Regeln geladen", "Die Regeln aus config.json gelten für den nächsten Import.")

    def _test_csv(self) -> None:
        self._verein_uebernehmen()
        pfad = filedialog.asksaveasfilename(
            title="Test-CSV speichern", defaultextension=".csv", initialfile="test_import.csv",
            initialdir=str(self.s.ausgabe_ordner()), filetypes=[("CSV", "*.csv")])
        if not pfad:
            return
        try:
            pfad, text = self.s.test_csv_schreiben(pfad)
        except (OSError, ExportFehler) as fehler:
            messagebox.showerror("Speichern fehlgeschlagen", str(fehler))
            return
        messagebox.showinfo("Test-CSV erzeugt", f"{pfad}\n\n{text}")

    # ------------------------------------------------------------------ Aktionen: Filter
    def _filter_lesen(self) -> Filter:
        gewaehlt = [a for a, v in self.var_arten.items() if v.get()]
        arten = None if len(gewaehlt) == len(self.var_arten) else ["" if a == NICHT_ERKANNT else a for a in gewaehlt]
        return Filter(
            von=self.var_von.get().strip(), bis=self.var_bis.get().strip(),
            von_event=self.cb_von_event.get().strip(), bis_event=self.cb_bis_event.get().strip(),
            arten=arten, name_enthaelt=self.var_name_ein.get(), name_enthaelt_nicht=self.var_name_aus.get())

    def _filter_anwenden(self) -> None:
        self._edit_bestaetigen()
        meldungen = self.s.filter_anwenden(self._filter_lesen())
        self._tabelle_fuellen()
        hinweis = self.s.leer_hinweis()
        if hinweis:
            meldungen.append(hinweis)
        if meldungen:
            messagebox.showinfo("Filter", "\n".join(meldungen))

    def _filter_zuruecksetzen(self) -> None:
        self.var_von.set(heute_text())
        self.var_bis.set("")
        self.var_name_ein.set("")
        self.var_name_aus.set("")
        self.cb_von_event.set("")
        self.cb_bis_event.set("")
        for v in self.var_arten.values():
            v.set(True)
        self._filter_anwenden()

    def _ab_heute(self) -> None:
        self.var_von.set(heute_text())
        self._filter_anwenden()

    def _ganzes_dokument(self) -> None:
        zeitraum = self.s.dokument_zeitraum()
        self.var_von.set(zeitraum[0] if zeitraum else "")
        self.var_bis.set(zeitraum[1] if zeitraum else "")
        self.cb_von_event.set("")
        self.cb_bis_event.set("")
        self._filter_anwenden()

    def _events_aktualisieren(self) -> None:
        namen = self.s.ereignisnamen() or [""]
        self.cb_von_event.configure(values=[""] + namen)
        self.cb_bis_event.configure(values=[""] + namen)

    # ------------------------------------------------------------------ Aktionen: Prüfung
    def _werte(self, t) -> tuple:
        meldungen = self.s.meldungen(t)
        status = self.s.status(t)
        hinweis = "; ".join(m.text for m in meldungen)
        werte = []
        for key, _, _ in SPALTEN:
            if key == "status":
                werte.append(STATUS_TEXT[status])
            elif key == "hinweis":
                werte.append(hinweis)
            else:
                werte.append(getattr(t, key))
        return tuple(werte), status

    def _zeile_setzen(self, t) -> None:
        werte, status = self._werte(t)
        iid = str(t.uid)
        if self.tree.exists(iid):
            self.tree.item(iid, values=werte, tags=(status,))
        else:
            self.tree.insert("", "end", iid=iid, values=werte, tags=(status,))

    def _tabelle_fuellen(self) -> None:
        self._edit_abbrechen()
        self.tree.delete(*self.tree.get_children())
        for t in self.s.sichtbar:
            self._zeile_setzen(t)
        self._status_aktualisieren()

    def _status_aktualisieren(self) -> None:
        z = self.s.zusammenfassung()
        quelle = f"{self.s.quelle} – " if self.s.quelle else ""
        text = (f"{quelle}{z['gesamt']} von {len(self.s.alle)} Terminen sichtbar:  ✔ {z[OK]} OK   "
                f"⚠ {z[WARNUNG]} prüfen   ✖ {z[FEHLER]} Fehler")
        if z[FEHLER]:
            text += "   (Export gesperrt, bis alle Fehler behoben sind)"
        hinweis = self.s.leer_hinweis()
        self.var_status.set(f"{quelle}{hinweis}" if hinweis else text)

    def _auswahl(self) -> list[int]:
        return [int(i) for i in self.tree.selection()]

    def _fehler_auswaehlen(self) -> None:
        fehler = [str(t.uid) for t in self.s.sichtbar if self.s.status(t) == FEHLER]
        self.tree.selection_set(fehler)
        if fehler:
            self.tree.see(fehler[0])
        else:
            messagebox.showinfo("Keine Fehler", "Es gibt keine Zeilen mit Fehlern.")

    def _zeit_setzen(self) -> None:
        uids = self._auswahl()
        if not uids:
            messagebox.showinfo("Keine Auswahl", "Bitte zuerst eine oder mehrere Zeilen markieren.")
            return
        dialog = ctk.CTkInputDialog(text="Beginn und Ende für die markierten Zeilen (z. B. 20:00-22:00 oder 20.00-22.00):",
                                    title="Beginn/Ende setzen")
        eingabe = dialog.get_input()
        if not eingabe:
            return
        fehler = self.s.zeit_setzen(uids, eingabe)
        if fehler:
            messagebox.showerror("Ungültige Eingabe", fehler)
            return
        for uid in uids:
            self._zeile_setzen(self.s.finde(uid))
        self._status_aktualisieren()

    def _als_geprueft(self) -> None:
        uids = self._auswahl()
        self.s.als_geprueft(uids)
        for uid in uids:
            self._zeile_setzen(self.s.finde(uid))
        self._status_aktualisieren()

    def _loeschen(self) -> None:
        uids = self._auswahl()
        if uids and messagebox.askyesno("Löschen", f"{len(uids)} Zeile(n) aus der Liste entfernen?"):
            self.s.loeschen(uids)
            self._tabelle_fuellen()

    def _neuer_termin(self) -> None:
        t = self.s.neuer_termin()
        self._zeile_setzen(t)
        self.tree.see(str(t.uid))
        self.tree.selection_set(str(t.uid))
        self._status_aktualisieren()

    # --- Zellen direkt bearbeiten
    def _doppelklick(self, ereignis) -> None:
        if self.tree.identify_region(ereignis.x, ereignis.y) != "cell":
            return
        iid = self.tree.identify_row(ereignis.y)
        spalte = self.tree.identify_column(ereignis.x)
        if not iid:
            return
        key = SPALTEN[int(spalte[1:]) - 1][0]
        if key in EDITIERBAR:
            self._bearbeite(iid, key, spalte)

    def _bearbeite(self, iid: str, key: str, spalte: str) -> None:
        self._edit_bestaetigen()
        box = self.tree.bbox(iid, spalte)
        if not box:
            return
        x, y, breite, hoehe = box
        wert = getattr(self.s.finde(int(iid)), key)
        if key == "terminart":
            feld = ttk.Combobox(self.tree, values=[""] + list(self.s.cfg.get("erlaubte_terminarten", [])))
            feld.set(wert)
            feld.bind("<<ComboboxSelected>>", lambda e: self._edit_fertig(iid, key, feld))
        else:
            feld = ttk.Entry(self.tree)
            feld.insert(0, wert)
            feld.select_range(0, "end")
            feld.bind("<FocusOut>", lambda e: self._edit_fertig(iid, key, feld))
        feld.bind("<Return>", lambda e: self._edit_fertig(iid, key, feld))
        feld.bind("<Escape>", lambda e: self._edit_abbrechen())
        feld.place(x=x, y=y, width=max(breite, 90), height=hoehe)
        feld.focus_set()
        self._editor = feld
        self._editor_ziel = (iid, key)

    def _edit_fertig(self, iid: str, key: str, feld) -> None:
        if self._editor is not feld:
            return
        wert = feld.get()
        self._editor = None
        feld.destroy()
        t = self.s.feld_setzen(int(iid), key, wert)
        self._zeile_setzen(t)
        self._status_aktualisieren()

    def _edit_bestaetigen(self) -> None:
        """Laufende Bearbeitung übernehmen (z. B. beim Klick auf eine andere Zeile)."""
        if self._editor is not None:
            iid, key = self._editor_ziel
            self._edit_fertig(iid, key, self._editor)

    def _edit_abbrechen(self) -> None:
        """Laufende Bearbeitung verwerfen (z. B. wenn die Tabelle neu aufgebaut wird)."""
        if self._editor is not None:
            feld, self._editor = self._editor, None
            feld.destroy()

    # ------------------------------------------------------------------ Aktionen: Export
    def _tab_gewechselt(self) -> None:
        if self.tabs.get() == TAB_EXPORT:
            self._vorschau_aktualisieren()

    def _kodierung_gewaehlt(self, label: str) -> None:
        self.s.kodierung_setzen(KODIERUNGEN[label])

    def _vorschau_aktualisieren(self) -> None:
        self._edit_bestaetigen()
        self._verein_uebernehmen()
        self.txt_vorschau.configure(state="normal")
        self.txt_vorschau.delete("1.0", "end")
        self.txt_vorschau.insert("end", self.s.csv_vorschau())
        self.txt_vorschau.configure(state="disabled")
        z = self.s.zusammenfassung()
        self.lbl_export.configure(
            text=f"{z['gesamt']} Termine" + (f" – {z[FEHLER]} Fehler, Export gesperrt" if z[FEHLER] else " – bereit zum Export"))

    def _exportieren(self) -> None:
        self._edit_bestaetigen()
        self._verein_uebernehmen()
        self.s.kodierung_setzen(KODIERUNGEN[self.var_kodierung.get()])
        probleme = self.s.export_probleme()
        if probleme:
            zeigen = "\n".join(probleme[:12]) + (f"\n… und {len(probleme) - 12} weitere" if len(probleme) > 12 else "")
            messagebox.showerror("Export gesperrt", "Bitte zuerst diese Probleme beheben:\n\n" + zeigen)
            self.tabs.set(TAB_PRUEFUNG)
            return
        pfad = filedialog.asksaveasfilename(
            title="CSV speichern", defaultextension=".csv", initialfile="konzertmeister_import.csv",
            initialdir=str(self.s.ausgabe_ordner()), filetypes=[("CSV", "*.csv")])
        if not pfad:
            return
        try:
            self.s.exportieren(pfad)
        except ExportGesperrt as fehler:
            messagebox.showerror("Export gesperrt", "\n".join(fehler.probleme[:12]))
            return
        except (OSError, ExportFehler) as fehler:
            messagebox.showerror("Speichern fehlgeschlagen", str(fehler))
            return
        messagebox.showinfo(
            "Export fertig",
            f"{len(self.s.sichtbar)} Termine exportiert:\n{Path(pfad)}\n\nZeichensatz: {self.var_kodierung.get()}")


def starte_gui() -> None:
    App().mainloop()
