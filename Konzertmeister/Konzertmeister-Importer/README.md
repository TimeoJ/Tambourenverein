# Konzertmeister-Importer (Version 1.1)

Liest ein Tätigkeitsprogramm (PDF oder Excel), erkennt die Termine, lässt sie in einer GUI prüfen
und korrigieren und erzeugt daraus eine CSV-Datei für den Import in Konzertmeister.
Den Import in Konzertmeister selbst machst du von Hand.

## Neu in Version 1.1

- **Zeitraum-Filter:** Startdatum und Enddatum setzen, alle Termine dazwischen werden exportiert (beide inklusive).
  Dazu: Start/Ende über ein Event, Terminart, «Name enthält» / «enthält nicht».
- **Zeit- und Datumsformate:** `20.00`, `20:00`, `20,00`, `20h00`, `20 Uhr`, `20-22 Uhr`; Datum als `10.01.2025`,
  `10.1.25`, `10/01/2025`, `10-01-2025` oder `2025-01-10`. Gilt beim Einlesen und bei Eingaben in der GUI.
- **Umlaute:** Die CSV wird jetzt standardmässig als **UTF-8 mit BOM** gespeichert, damit Excel ä, ö, ü richtig
  anzeigt. Im Tab «CSV-Vorschau & Export» lässt sich der Zeichensatz wählen (siehe unten).
- **Excel-Zahlenzeiten:** Tippt man in Excel `20.00` oder `20.30`, speichert Excel die Zahl 20 bzw. 20,3. In Zeit-/Beginn-/Ende-Spalten
  wird das wieder als 20.00 / 20.30 gelesen. Zerlegte Umlaute (a + ¨) werden beim Einlesen und Export zu ä zusammengesetzt (NFC).
- **Verbesserungen aus dem Test mit dem echten Tätigkeitsprogramm 2025** (vorher wurden nur 21 von 97 Terminen erkannt):
  farbig hinterlegte Zeilen im PDF, Fusszeile mit Datum, Folgezeilen, «KEINE PROBE», Ende um Mitternacht,
  bessere Trennung von Name und Information.

## Installation

Es gibt zwei getrennte Skripte, damit nichts ohne dein Wissen passiert:

- **`setup.bat` / `./setup.sh` – einmalige Einrichtung.** Das Skript prüft zuerst nur lesend, was schon da ist
  (`--pruefen` zeigt nur den Stand an). Fehlt etwas, erklärt es genau, was passieren würde (Herkunft der Downloads,
  Zielordner, Grösse der Eingriffe) und **fragt vor dem Download nach**. Bei «Nein» wird nichts verändert.
  Danach legt es im Programmordner `.uv/` (das Werkzeug [uv](https://docs.astral.sh/uv/), ohne Admin-Rechte,
  ohne PATH-Änderung) und `.venv/` (Python-Pakete) an. Ist Python schon installiert, wird dieses verwendet, sonst lädt uv eines.
  Der uv-Installer wird als Datei gespeichert (`.uv/install-uv.ps1` bzw. `.sh`) und kann angesehen werden.
  Alles liegt im Programmordner; zum Entfernen genügt es, den Ordner zu löschen.
- **`starten.bat` / `./starten.sh` – Programm starten.** Lädt nichts herunter und installiert nichts. Ist die
  Einrichtung noch nicht gemacht, weist es auf `setup` hin. Optionen gehen auch hier:
  `starten.bat programm.pdf --von 01.11.2026 --bis 31.12.2026`.

Weitere Wege:
- **Python ist schon da:** `python starten.py` legt `.venv` an und installiert die Pakete selbst (fragt vorher nach). Alternativ `uv run main.py`.
- **Echte Einzeldatei (.exe/.app) ohne Python:** In GitHub unter *Actions → «Anwendung bauen»* starten
  (`.github/workflows/build.yml`, PyInstaller). Die fertige Anwendung ist dann unter *Artifacts* herunterladbar.
  `config.json`, `input/` und `output/` liegen dann neben der Anwendung.
- **Docker:** nur für die Kommandozeile (keine GUI), siehe `Dockerfile`.

Manuell: Python 3.10 oder neuer (getestet mit 3.13). Tkinter gehört bei Windows und macOS zu Python;
unter Linux eventuell `sudo apt install python3-tk`. Dann `pip install -r requirements.txt`.

## Starten

```
python main.py
```

Zuerst am besten den Import mit einer Testzeile ausprobieren: im Tab **Import** auf
«Test-CSV erzeugen» klicken (eine Probe am kommenden Mittwoch, 20:00–22:00 Uhr) und die Datei in
Konzertmeister importieren. Das gleiche geht ohne GUI mit `python main.py --test`.

Zum Ausprobieren liegen fiktive Beispieldateien in `beispiele/` (`beispiel_programm.xlsx`, `.pdf`).

## Ablauf in der GUI

1. **Import**: PDF oder Excel wählen. Das Protokoll zeigt übersprungene Zeilen und angehängte Folgezeilen.
2. **Prüfung & Filter**
   - **Zeitraum – Von / Bis:** Datum eintragen (leer = keine Grenze). «Ab heute» setzt das Startdatum auf heute,
     «Ganzes Dokument» übernimmt den ganzen Zeitraum der Datei. Beim Einlesen steht *Von* auf heute, vergangene
     Termine fehlen also zunächst (bei einem älteren Programm «Ganzes Dokument» klicken).
   - **Von Event / Bis und mit Event:** Start bzw. Ende am Tag des ersten Termins, dessen Name den Text enthält.
     Mehrere Termine am Endtag bleiben drin. Sind Datum und Event beide gesetzt, gilt die strengere Grenze
     (der Filter meldet, welche).
   - **Terminart:** Häkchen für Probe, Auftritt, Sonstiges und «nicht erkannt».
   - **Name enthält / enthält nicht:** Begriffe mit Komma trennen, z. B. `Probe, Konzert`.
   - **Doppelklick** auf eine Zelle bearbeitet sie. «Alle Fehler auswählen» und danach «Beginn/Ende setzen …»
     füllt viele Zeilen auf einmal (z. B. alle «ganzer Tag»-Termine).
   - Farben: ✔ grün OK, ⚠ gelb prüfen, ✖ rot Fehler. **Rote Zeilen blockieren den Export**, bis sie korrigiert
     oder gelöscht sind (Pflichtfelder: Datum, Beginn, Ende, Name). Sobald du eine Zeile bearbeitest oder
     «Als geprüft markieren» klickst, gilt eine gelbe Warnung als quittiert.
3. **CSV-Vorschau & Export**: zeigt exakt den Inhalt der Datei. Unten rechts den **Zeichensatz** wählen, dann
   «Konzertmeister-CSV exportieren …» (Standardordner `output/`).

Ohne GUI geht es auch, zum Beispiel:

```
python main.py programm.pdf --von 01.11.2026 --bis 31.12.2026 -o output/import.csv
python main.py programm.pdf --von-event "Fasnachtsumzug" --bis-event "GV" --arten Probe,Auftritt
python main.py programm.pdf --alles --name-enthaelt-nicht Probe --kodierung cp1252
```

(Ohne Angabe gilt *Von* = heute. Das Programm bricht mit einer Liste ab, wenn noch Fehler offen sind.)

## Umlaute und Zeichensatz

| Auswahl | Wann |
|---|---|
| **UTF-8 mit BOM** (Standard) | Excel zeigt Umlaute damit richtig an. |
| UTF-8 ohne BOM | Wenn Konzertmeister die Datei damit besser liest. |
| Windows-1252 (ANSI) | Wenn Umlaute nach dem Import in Konzertmeister immer noch falsch aussehen. |

Erscheint in Excel «Ã¤» statt «ä», fehlte das BOM. Erscheint in Konzertmeister «ï»¿Datum» oder ein Zeichen vor der
ersten Spalte, stört das BOM: dann «UTF-8 ohne BOM» wählen. Mit «Einstellungen speichern» (Tab Import) merkt sich
das Programm die Wahl in `config.json`. Zeichen, die ein Zeichensatz nicht kennt, werden mit klarer Meldung
abgelehnt statt verfälscht.

## CSV-Format

Semikolon-getrennt, alle Felder in Anführungszeichen, Kopfzeile:

```
"Datum";"Beginn";"Ende";"Name";"Raum";"Ort";"Treffpunkt";"Information";"Terminart";"Kategorien";"Verein"
"04.11.2026";"20:00";"22:00";"Probe";"";"";"";"";"Probe";"Probe";"Tambourenverein Zofingen"
```

Keine mehrtägigen Termine, nur ein Datumsfeld. Spalten, Trennzeichen, Kodierung und der Vereinsname stehen in `config.json`.

## Grundsatz: nichts erfinden

Zeiten werden **nie geschätzt**. Was im Original nicht eindeutig ist, bleibt leer und wird im Feld
«Information» dokumentiert:

| Original | Beginn | Ende | Information (Ergänzung) |
|---|---|---|---|
| `20.00 - 22.00` | 20:00 | 22:00 | – |
| `19.00 - 00.00`, `23.00 - 24.00` | 19:00 / 23:00 | **23:59** | Ende im Original: 00.00 (Mitternacht), als 23:59 übernommen. |
| `???` | leer | leer | Originalzeit im Tätigkeitsprogramm unbekannt (???). Bitte prüfen. |
| `??? (15.55)` | 15:55 | leer | Originaleintrag: ??? (15.55). Startzeit aus Klammer übernommen. Endzeit unbekannt. Bitte prüfen. |
| `ganzer Tag`, `Vormittag`, `Nachmittag` | leer | leer | Originalangabe im Tätigkeitsprogramm: … |
| `ab 11.00 Uhr`, `ca. 21.30` | 11:00 / 21:30 | leer | Originalangabe im Tätigkeitsprogramm: …. Endzeit unbekannt. |
| `15.32` | 15:32 | leer | Im Original wurde nur eine einzelne Uhrzeit angegeben (15.32). Endzeit unbekannt. |
| (keine Zeit) | leer | leer | Im Tätigkeitsprogramm war keine Zeitangabe vorhanden. Bitte prüfen. |

Ein Ende um Mitternacht wird als `23:59` übernommen, weil Termine innerhalb eines Tages liegen. Möchtest du `00:00`,
stelle `"mitternacht_als": "00:00"` in `config.json` ein (das Programm warnt dann bei jedem solchen Termin).

Weil Beginn und Ende Pflichtfelder sind, sind alle Zeilen mit leerer Zeit rot, bis du die Zeit einträgst.

Weitere Regeln:

- **Name und Information:** Der Name reicht bis zur ersten Klammer oder zum ersten Komma, der Rest kommt in die
  Information. `Hirsmontag (Schnitzelbanktour), Probelokal im Kostüm` → Name `Hirsmontag`, Information
  `Schnitzelbanktour, Probelokal im Kostüm`.
- **Folgezeilen:** Eine Zeile ohne Datum direkt unter einem Termin gehört zu diesem Termin und wird als
  «Folgezeile im Original: …» an die Information angehängt (gelb markiert). Abschaltbar mit
  `"folgezeilen_anhaengen": false`.
- **«KEINE PROBE»:** Zeilen mit Stichwörtern aus `ueberspringen` (Standard: «keine probe») sind keine Termine und
  stehen nur im Protokoll.
- **Kopf-, Fuss- und Abschnittszeilen** («Seite 1 …», «Ausblick», Monatsüberschriften) werden ignoriert.
- **Wochentag passt nicht zum Datum** (z. B. «Donnerstag 01.08.2025», aber der 1. August 2025 war ein Freitag):
  gelbe Warnung. So fallen Tippfehler im Programm auf.

## Regeln anpassen (config.json)

Terminart und Kategorien werden anhand von Stichwörtern im Terminnamen bestimmt. Die Listen in
`config.json` kannst du selbst ergänzen, ohne den Code anzufassen:

```json
"terminart_regeln": { "Probe": ["Probe", "Probesamstag"], "Auftritt": ["Umzug", "Ständli"] }
```

- `terminart_regeln`: von oben nach unten, der erste Treffer gewinnt. Erlaubt sind nur die Terminarten
  aus `erlaubte_terminarten` (Probe, Auftritt, Sonstiges, Probenanfrage, Auftrittsanfrage, Information).
- `kategorie_regeln`: hier können mehrere Kategorien gleichzeitig zutreffen (Trennzeichen `, `). **Jeder Kategoriename
  muss laut Konzertmeister 3 bis 20 Zeichen lang sein**; sonst ist die Zeile rot und der Export gesperrt
  (Grenzen in `kategorie_zeichen`).
  **Die Kategorienamen müssen in Konzertmeister genau so existieren.** Die mitgelieferten Namen sind Beispiele.
- Stichwörter mit höchstens 3 Buchstaben (GV, DV, OTV) zählen nur als ganzes Wort.
- Wird nichts erkannt (z. B. «Powerman Zofingen», «Eidg. Musikfest Biel»), bleibt das Feld leer und die Zeile gelb;
  Konzertmeister nimmt dann die Werte der Terminvorlage. Trage solche Namen in die Regeln ein, dann klappt es künftig.

Nach Änderungen an `config.json` in der GUI auf «Regeln neu laden» klicken (gilt ab dem nächsten Import).
Eine `config.json` aus Version 1.0 wird beim Laden automatisch angepasst (Zeichensatz UTF-8 mit BOM, neue Einstellungen).

## Erkennung der Termine

Erwartet wird eine Tabelle ungefähr wie `Wochentag | Datum | Zeit | Anlass`; die Reihenfolge ist egal.
Bei Excel wird eine Kopfzeile (Datum, Zeit/Beginn/Ende, Anlass, Ort, Treffpunkt, Bemerkung …) automatisch
erkannt, alle Tabellenblätter werden gelesen. Beim PDF wird der Seitentext Zeile für Zeile gelesen; echte
Tabellen mit Gitterlinien werden zellenweise gelesen.
Nicht unterstützt: eingescannte PDFs (OCR), alte `.xls`-Dateien (bitte als `.xlsx` speichern),
Datumsangaben ohne Jahr.

## Tests

```
python -m unittest discover -s tests -t .
```

Die GUI-Tests arbeiten mit Attrappen (es öffnet sich kein Fenster) und prüfen nur die Verdrahtung zur Logik.

## Aufbau

```
main.py              Start (GUI oder Kommandozeile)
config.json          Einstellungen und Regeln
kmimport/
  gui.py             Oberfläche (CustomTkinter)
  session.py         Programmlogik ohne GUI
  parser_pdf.py      PDF einlesen
  parser_excel.py    Excel einlesen
  event_extractor.py Termine in Zeilen erkennen
  zeit.py            Zeit- und Datumsformate auslesen und umwandeln
  regeln.py          Terminart und Kategorien
  validator.py       Prüfung (ok / prüfen / Fehler)
  filters.py         Zeitraum, Event, Terminart, Name
  exporter.py        CSV schreiben, Zeichensatz, Testtermin
beispiele/           Beispieldateien und Generator
tests/               Unit-Tests
input/  output/      Ablage für Programme und exportierte CSVs
```
