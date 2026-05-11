# workbench.md

version: 2.0
last_updated: 2026-04-30
compatible_with:
  workbench_logic: "2.0"
  workbench_ui: "2.0"

## Zweck und Vertragscharakter
Diese Datei ist die verbindliche globale Vertragsdatei für die Generierung von Reinforcement-Learning-Projekten innerhalb der Workbench.

Sie definiert:
- die beteiligten Prompt-Dateien
- ihre Rollen und Zuständigkeiten
- die verbindliche Lese- und Anwendungsreihenfolge
- Prioritätsregeln
- Regeln zur Konfliktauflösung
- globale Technologie-, Struktur-, Benennungs- und Qualitätsanforderungen
- Regeln zur Reproduzierbarkeit und Konfigurationspersistenz

Diese Datei enthält ausschließlich projektunabhängige, globale Regeln.

## Beteiligte Dateien
Die vollständige Projektgenerierung basiert auf genau diesen Dateien:
- `workbench.md`
- `workbench_logic.md`
- `workbench_ui.md`
- `<project_name>.md`

Rollenverteilung:
- `workbench.md`: globale Vertragsregeln, Prioritäten, Struktur, Qualitätsregeln, Benennungsregeln, Reproduzierbarkeit, Konfigurationspersistenz
- `workbench_logic.md`: Architektur, Trainingslogik, Event-Vertrag, Run-Modi, Compare-Logik, Sweep-Logik, Exporte, Logiktests
- `workbench_ui.md`: Layout, Controls, Parameterbereiche, Event-Verarbeitung, Plot-Verhalten, Threading-Bridge, Konfigurationsspeicherung, GUI-Tests
- `<project_name>.md`: projektspezifische Inhalte, Defaults, Parameter, unterstützte Algorithmen, projektspezifische GUI-Erweiterungen, Ausnahmen und Validierungsregeln

## Verbindliche Lese- und Anwendungsreihenfolge
Verwende immer diese Reihenfolge:
1. `workbench.md` lesen und als globale Vertragsgrundlage anwenden
2. `<project_name>.md` lesen und projektspezifische Vorgaben einarbeiten
3. `workbench_logic.md` anwenden und implementieren
4. `workbench_ui.md` anwenden und implementieren

Regeln:
- Alle nachfolgenden Dateien sind im Rahmen dieser Vertragsdatei zu interpretieren.
- Die Reihenfolge beschreibt die Anwendungssequenz, nicht allein die Priorität.
- `workbench_logic.md` und `workbench_ui.md` sind in ihrem jeweiligen Zuständigkeitsbereich gleichrangig, bleiben aber der globalen Vertragslogik aus `workbench.md` untergeordnet.

## Prioritätsregeln
Es gilt folgende Priorität:
1. `workbench.md`
2. `workbench_logic.md` und `workbench_ui.md` in ihrem jeweiligen Zuständigkeitsbereich
3. `<project_name>.md` für projektspezifische Konfiguration, Defaults und Ausnahmen

Präzisierung:
- `<project_name>.md` darf projektspezifische Defaults, Parameterwerte, unterstützte Algorithmen, spezielle GUI-Elemente, projektspezifische Parametergruppen, besondere Validierungsregeln und notwendige Sonderlogik definieren.
- `<project_name>.md` darf keine globalen Architekturprinzipien, keinen globalen Event-Vertrag, keine globale Dateistruktur und keine grundlegenden GUI-Prinzipien außer Kraft setzen.
- `workbench_logic.md` ist maßgeblich für Logik-, Orchestrierungs- und Laufzeitverhalten.
- `workbench_ui.md` ist maßgeblich für GUI-Layout, Eingabemuster, Statusdarstellung und Event-Verarbeitung.

## Konfliktauflösung
Wenn Vorgaben kollidieren, gelten folgende Regeln:
- globale Regeln aus `workbench.md` haben immer Vorrang
- Logikregeln gehören ausschließlich nach `workbench_logic.md`
- UI-Regeln gehören ausschließlich nach `workbench_ui.md`
- projektspezifische Regeln gehören nach `<project_name>.md`, dürfen aber nur innerhalb ihres Zuständigkeitsbereichs überschreiben

Wenn zwei Dateien scheinbar dieselbe Frage regeln, gilt:
- Struktur-, Vertrags-, Benennungs-, Persistenz- und Qualitätsfragen -> `workbench.md`
- Trainings-, Agent-/Algorithmus-, Evaluate-, Run-Modi-, Compare-, Sweep-, Export-, Konfigurations- und Event-Fragen -> `workbench_logic.md`
- Layout-, Panel-, Control-, Plot-, Session-, Threading- und GUI-Interaktionsfragen -> `workbench_ui.md`
- Environment-, Algorithmus-, Parameter- und projektspezifische Sonderregeln -> `<project_name>.md`

### Konfliktmatrix
| Thema | Führende Datei | Überschreibbar durch `<project_name>.md`? |
|---|---|---|
| Dateistruktur | `workbench.md` | nein |
| Benennungsregeln | `workbench.md` | nein |
| globale Architekturprinzipien | `workbench.md` | nein |
| Event-Vertrag | `workbench_logic.md` | nein |
| Logik- und TrainLoop-Verhalten | `workbench_logic.md` | nur projektspezifische Ergänzungen |
| Run-Modi (`single_run`, `algo_compare`, `sweep_run`) | `workbench_logic.md` | nein |
| GUI-Grundlayout und Pflicht-Controls | `workbench_ui.md` | nur projektspezifische Ergänzungen |
| generische Parameterbereiche und Job-List-Struktur | `workbench_ui.md` | nur projektspezifische Ergänzungen |
| Environment-Details | `<project_name>.md` | ja |
| unterstützte Algorithmen und projektspezifische Parameter | `<project_name>.md` | ja |
| GUI-Ausnahmen für ein Projekt | `<project_name>.md` | ja, innerhalb des UI-Rahmens |
| Logik-Ausnahmen für ein Projekt | `<project_name>.md` | ja, innerhalb des Logik-Rahmens |
| Ausgabeordner-Struktur (`plots/`, `configs/`, `models/`) | `workbench.md` | nein — Pfade sind global verbindlich |

## Erlaubte Inhalte je Datei

### `workbench.md`
Erlaubt:
- globale Regeln
- Struktur- und Vertragslogik
- globale Technologien
- Ausgabe- und Qualitätsanforderungen
- Benennungs- und Reproduzierbarkeitsregeln
- Regeln zur Konfigurationspersistenz

Nicht erlaubt:
- projektspezifische Algorithmen
- projektspezifische Environment-Details
- projektspezifische UI-Sonderfelder
- konkrete Hyperparameter einzelner Projekte

### `workbench_logic.md`
Erlaubt:
- generische Architektur und Logikregeln
- Agent-/Algorithmus-Abstraktion
- Event-Vertrag
- TrainLoop-Verhalten
- generische Run-Modi (`single_run`, `algo_compare`, `sweep_run`)
- generische Sweep-Orchestrierung und Job-Isolation
- - Exportlogik (Plot-Export nach `plots/`, Modell-Export nach `models/`; CSV-Export ist
  optional und muss in `<project_name>.md` explizit definiert werden)
- Regeln für Konfigurationszustände und deren Wiederanwendung
- Logiktests

Nicht erlaubt:
- fest auf ein einzelnes Projekt zugeschnittene Logik
- freie Abweichung vom globalen Vertragsrahmen

### `workbench_ui.md`
Erlaubt:
- GUI-Layout
- Pflicht-Controls
- Parameterbereiche
- Methods-Bereich
- Job-List-Struktur
- standardisierte Eingabetypen
- Event-Pump und Worker-Bridge
- Plot- und Statusregeln
- Regeln zur Konfigurationsspeicherung
- GUI-Tests

Nicht erlaubt:
- projektspezifische UI-Details außerhalb des vereinbarten Erweiterungsrahmens
- Bruch des globalen Event-Vertrags

### `<project_name>.md`
Erlaubt:
- projektspezifische Environment-Definition
- projektspezifische unterstützte Algorithmen
- projektspezifische Parameter und Defaults
- projektspezifische GUI-Erweiterungen
- projektspezifische Logik-Ausnahmen
- projektspezifische Validierungsregeln

Nicht erlaubt:
- Umdefinieren globaler Dateinamen
- Umdefinieren des generischen Event-Vertrags
- Aufheben globaler Qualitätsregeln
- willkürlicher Bruch der Logik- oder UI-Grundstruktur

## Globale Technologie- und Backend-Anforderungen
Verwende mindestens:
- Python 3.8+
- Tkinter + ttk für die GUI
- matplotlib mit TkAgg für Plotting
- Pillow, falls für Bilddarstellung oder Konvertierung notwendig
- Gymnasium als Environment-API

Weitere Regeln:
- Die Logik muss headless testbar bleiben.
- GUI und Trainingslogik müssen sauber entkoppelt sein.
- Das System soll für tabellarische Verfahren, neuronale Netze und optionale SB3-nahe Implementierungen erweiterbar sein.
- Die Gesamtarchitektur muss mehrere parallel laufende Worker verarbeiten können.

## Projekt-Ausgabestruktur
Erstelle unter Verwendung von `<project_name>` aus der projektspezifischen Datei mindestens:
- `<project_name>_app.py`
- `<project_name>_logic.py`
- `<project_name>_ui.py`
- `<project_name>_REQUIREMENTS_MATRIX.md`
- `tests/test_<project_name>_logic.py`
- `tests/test_<project_name>_gui.py`
- `requirements.txt`
- `README.md`
- Ausgabeordner `plots/`
- Ausgabeordner `configs/`
- Ausgabeordner `models/` (optional, nur wenn das Projekt Modell-Checkpoints speichert)

Alle Ausgabeordner liegen direkt neben den Implementierungsdateien im Projektordner.
`results_csv/` ist kein Pflichtordner mehr; projektspezifische CSV-Exporte können
in `<project_name>.md` unter `Projekt-Ausgaben oder besondere Exporte` definiert werden.

## Benennungs- und Strukturkonventionen
Pflichtregeln:
- Dateinamen müssen exakt und konsistent verwendet werden.
- Schreibfehler in Dateinamen, Abschnittsüberschriften, Event-Namen oder Feldnamen sind unzulässig.
- Abweichende Schreibweisen wie `worbench`, `workbenc_logic` oder inkonsistente Event-Namen sind unzulässig.
- Event-Namen und Feldnamen müssen über Logik, GUI, Tests und Dokumentation identisch bleiben.
- Abschnittsnamen in den Prompt-Dateien sollen stabil und klar sein.
- Der `<project_name>` wird durch den Dateinamen der projektspezifischen Datei bestimmt (ohne `.md`-Endung). Er muss `snake_case` verwenden und darf keine Leerzeichen oder Sonderzeichen enthalten.
- Dieser Name ist verbindlich für alle generierten Dateinamen, Ordner und Exportpfade.
- Für denselben generischen Zweck dürfen nicht parallel `policy_name` und `algorithm_name` verwendet werden. Der Standardbegriff ist `algorithm_name`.

## Reproduzierbarkeit und Determinismus
Pflichtregeln:
- Seeds sollen, wenn fachlich sinnvoll, explizit unterstützt werden.
- Environment-Neubauten und wichtige Laufparameter müssen nachvollziehbar sein.
- Compare-Läufe müssen pro Algorithmus sauber getrennt und reproduzierbar dokumentiert werden.
- Sweep-Läufe müssen pro Job sauber getrennt und reproduzierbar dokumentiert werden.
- Persistierte Konfigurationszustände sollen Save/Load ohne semantischen Informationsverlust ermöglichen.
- Exportdateien sollen relevante Metadaten im Namen oder in den Exportdaten tragen.
-  Konfigurationsdateien (JSON) werden zwingend im Projektordner unter `configs/` gespeichert.
  Ein freier Dateipfad außerhalb dieses Ordners ist nicht zulässig.
- Dasselbe Prinzip gilt für alle projektbezogenen externen Dateien (Plots, Modelle, Configs):
  Sie werden immer in den dafür definierten Projektordnern abgelegt, nie an einem
  frei gewählten externen Pfad.

## Globale Qualitätsanforderungen
Alle generierten Projekte müssen:
- vollständigen, lauffähigen Code erzeugen
- keine bloßen Gerüste oder TODO-Platzhalter als Endergebnis liefern
- eine klare Trennung zwischen Logik und GUI einhalten
- Tests für Logik und GUI bereitstellen
- eine nachvollziehbare `README.md` liefern
- eine nachvollziehbare `<project_name>_REQUIREMENTS_MATRIX.md` liefern
- strukturierte Exporte nach `results_csv/` und `plots/` unterstützen
- serialisierbare Konfigurationszustände unterstützen oder sauber verarbeiten können

## Verbotene Muster
Unzulässig sind insbesondere:
- inkonsistente Dateinamen
- widersprüchliche Event-Bezeichner
- projektübergreifend wechselnde Feldnamen für denselben Zweck
- GUI-blockierendes Training
- direkte Vermischung von GUI-Logik mit Algorithmus-Logik
- fehlender Abschlusszustand nach Cancel oder Fehler
- stille Missachtung inkompatibler Sweep- oder Compare-Overrides ohne nachvollziehbare Behandlung
- inkonsistente Benennung von `policy_name` und `algorithm_name` für denselben Zweck
- Speichern von Konfigurationen, Plots oder Modell-Checkpoints an frei gewählten externen
  Pfaden statt in den definierten Projektordnern (`configs/`, `plots/`, `models/`)

## Anforderungen an README, Requirements Matrix und Tests

### README
Die `README.md` muss mindestens enthalten:
- Projektziel
- verwendetes Environment
- unterstützte Algorithmen
- Startanleitung
- Beschreibung der wichtigsten Parameter
- Beschreibung der Run-Modi (`single_run`, `algo_compare`, `sweep_run`)
- Hinweise zu Compare, Sweep, Exporten und Tests
- Hinweise zu Konfigurationsspeicherung und Konfigurationsladen

### Requirements Matrix
Die `<project_name>_REQUIREMENTS_MATRIX.md` muss nachvollziehbar zuordnen:
- welche Anforderung aus welcher Prompt-Datei stammt
- in welcher Zieldatei sie umgesetzt wurde
- ob sie vollständig, teilweise oder speziell umgesetzt wurde

### Tests
Pflicht:
- Logiktests
- GUI-Tests
- isolierbare Testausführung im Projektkontext

## Glossar
| Begriff | Definition |
|---|---|
| `session_id` | Eindeutige ID einer GUI-Session; wird GUI-seitig vergeben; dient dem Verwerfen veralteter Worker-Events |
| `run_id` | Eindeutige ID eines einzelnen Trainings-, Compare- oder Sweep-Jobs innerhalb einer Session |
| `algorithm_name` | Lesbarer oder standardisierter Bezeichner eines Algorithmus; wird für GUI, Events, Exporte und Vergleiche verwendet |
| `display_label` | GUI-taugliche Bezeichnung eines Laufs oder Jobs; darf vom reinen `algorithm_name` abweichen |
| `project_name` | Verbindlicher Bezeichner des Projekts; bestimmt durch den Dateinamen der projektspezifischen Datei (snake_case, ohne `.md`) |
| `single_run` | Einzellauf mit genau einem ausgewählten Algorithmus |
| `algo_compare` | Paralleler Vergleich mehrerer ausgewählter Algorithmen unter gemeinsamem GUI-Kontext |
| `sweep_run` | Ausführung mehrerer vordefinierter Jobs aus einer Job List; jeder Job ist ein eigener Lauf |
| `job_list` | Vom Nutzer definierte Liste konkreter Sweep-Konfigurationen, die als einzelne Jobs ausgeführt werden |
| `config_state` | Serialisierbarer Zustand der GUI-/Trainingskonfiguration, der gespeichert und später wieder geladen werden kann |

## Endziel
Diese Datei dient dazu, zusammen mit `workbench_logic.md`, `workbench_ui.md` und `<project_name>.md` konsistente, erweiterbare, reproduzierbare und GUI-taugliche RL-Projekte zu generieren.