# workbench_ui.md

version: 2.0
last_updated: 2026-04-30
compatible_with:
  workbench: "2.0"
  workbench_logic: "2.0"

## Zweck und Geltungsbereich
Diese Datei definiert die projektübergreifenden Regeln für die grafische Oberfläche von Reinforcement-Learning-Projekten. Sie beschreibt Layout, Panel-Struktur, Controls, Parameterbereiche, Event-Verarbeitung, Worker-Bridge, Statusdarstellung, Live-Plot-Verhalten, Run-Modi und Regeln für kleinere Displays.

Die GUI-Regeln sollen ein konsistentes Bedienkonzept über mehrere RL-Projekte hinweg sicherstellen, während projektspezifische Erweiterungen innerhalb definierter Bereiche erlaubt bleiben.

## Zentrale GUI-Klasse
Implementiere eine zentrale GUI-Klasse mit mindestens folgenden Verantwortlichkeiten:
- Aufbau aller Hauptpanels unter Verwendung verschiebbarer Trennbalken
- Verwaltung des Parameterzustands
- Speichern und Laden serialisierbarer Konfigurationszustände
- Starten und Überwachen von Worker-Läufen (auch parallel)
- UI-seitige Event-Pump (muss parallele Events verarbeiten können)
- Statusanzeige des aktuellen Laufs
- Live-Plot-Verwaltung
- Live-Animations-Verwaltung des Environments
- Verwaltung der Run-Modi `single_run`, `algo_compare` und `sweep_run`
- Verwaltung einer Job List für Sweep-Läufe
- thread-sichere Session- und Worker-Verwaltung

## Architektur
Die zentrale GUI-Klasse muss enthalten:
- Panel zur Umgebungsdarstellung oder Anbindung an ein separates Animationsfenster
- Parameter-Panel mit Scrollbereich und Mausrad-Unterstützung
- Steuerleiste
- Current-Run-Bereich für Status und Fortschritt
- live aktualisierten Matplotlib-Plot
- Methoden-/Algorithmenbereich mit algorithmusspezifischen Parametern
- Bereich für Sweep-/Job-List-Verwaltung
- Trainings-Threads im Hintergrund mit UI-Pump im Main-Thread

## Fenster- und Layoutregeln
Das Top-Level-Layout darf **nicht** als starres Grid implementiert werden. Verwende stattdessen verschiebbare Trennbalken (`ttk.PanedWindow`), damit der Nutzer die Teilbereiche flexibel in der Größe anpassen kann.

Empfohlene Struktur der PanedWindows:
- Ein vertikales Haupt-PanedWindow (`orient=tk.VERTICAL`), das die Anwendung in drei Hauptzonen teilt:
  1. **Obere Zone:** Ein horizontales PanedWindow
  2. **Mittlere Zone:** Ein Frame für Controls und Statusanzeige
  3. **Untere Zone:** Der Live-Plot  

- Das Parameter-Panel der oberen Zone wird intern mit einem grid-Layout in Gruppen aufgeteilt. `pack` ist für die Gruppenanordnung innerhalb des Parameter-Panels nicht erlaubt. Das grid-Layout erlaubt Spalten- und Zeilenkonfiguration mit `weight` sowie `rowspan` für Gruppen, die sich über mehrere Zeilen erstrecken.

Startgewichte des vertikalen Haupt-PanedWindow:
- Obere Zone: weight=6
- Mittlere Zone: weight=1
- Untere Zone: weight=3

Diese Gewichte sind projektspezifisch anpassbar, müssen aber sicherstellen, dass die obere Zone beim Start den größten Anteil erhält.  

Weitere Regeln:
- Die Hauptbereiche müssen sauber skalieren.
- Bei kleineren Displays darf kein zentraler Bereich unbenutzbar werden.
- Wenn Inhalte nicht mehr vollständig sichtbar sind, müssen Scroll- oder Resize-Strategien greifen statt Abschneiden.
- Das Hauptfenster darf flexibel auf eingebettete oder ausgelagerte Animation reagieren.
- Freier Raum nach dem Auslagern einer Animation in ein separates Fenster muss sinnvoll durch Status-, Plot- oder Konfigurationsbereiche nutzbar bleiben.

## Parameter-Panel
Das Parameter-Panel muss enthalten:
- scrollbaren Inhaltsbereich
- Gruppen oder Bereiche, die die gesamte Panelbreite ausfüllen
- **Pflicht:** Unterstützung für Mausrad-Scrolling. Der Nutzer muss den Inhalt des Parameter-Panels mit dem Mausrad (oder Trackpad) verschieben können, ohne den Scrollbalken manuell klicken und ziehen zu müssen

Pflichtgruppen und ihr grid-Layout:
Das Parameter-Panel verwendet ein 2-spaltiges grid. Die Gruppen werden wie folgt angeordnet:
| Position                | Gruppe                      |
| ----------------------- | --------------------------- |
| row=0, col=0            | Environment                 |
| row=1, col=0            | Training / General          |
| row=0, col=1, rowspan=2 | Presets / Common Parameters |
| row=2, col=0            | Methods / Specific       |
| row=2, col=1            | Parameter Tuning / Job List |

- Die Environment-Gruppe muss mindestens enthalten:
  - Checkbox „Animation aktivieren/deaktivieren"
  - Spinbox „Frame interval (ms)" — Default: `10`, nur aktiv wenn Animation an
  - Projektspezifische Environment-Parameter gemäß `<project_name>.md`

Regeln:
- Die genaue visuelle Gruppierung darf projektspezifisch verfeinert werden, die Semantik dieser Bereiche muss jedoch erhalten bleiben.
- Gemeinsame Parameter müssen in allen Projekten an konsistenter Stelle erscheinen.
- Freie, unstrukturierte Platzierung projektspezifischer Controls ist nicht erlaubt.
- Der Bereich `Methods` ist für algorithmusspezifische Parameter reserviert.
- Der Bereich `Parameter Tuning / Job List` ist für Sweep-Definition, Job-Verwaltung und Sweep-Ausführung reserviert.

## Methoden-Bereich
Der Methods-Bereich muss die algorithmusspezifischen Parameter editierbar machen.

Pflichtregeln:
- Unterstützte Algorithmen sollen in klar getrennten Unterbereichen dargestellt werden.
- Für mehrere freigeschaltete Algorithmen ist ein `ttk.Notebook` mit einem Tab pro Algorithmus die bevorzugte Standardlösung.
- Jeder Algorithmus-Tab enthält nur die für diesen Algorithmus fachlich relevanten Parameter.
- Gemeinsame Parameter dürfen in einem separaten gemeinsamen Bereich gepflegt werden, dürfen aber nicht unklar mit algorithmusspezifischen Feldern vermischt werden.
- Die GUI muss einen aktiven Algorithmus für `single_run` explizit auswählbar machen.

## Parameter Tuning / Job List
Die GUI muss Sweep-Läufe über eine explizite Job List unterstützen.

Pflichtbestandteile:
- Auswahl des Ziel-Algorithmus
- Auswahl des Zielparameters
- Eingabe oder Auswahl des Zielwerts
- Aktion zum Hinzufügen eines Jobs
- sichtbare Job List
- Aktion zum Entfernen ausgewählter Jobs
- Aktion zum Leeren aller Jobs
- Start-Button für `sweep_run`

Regeln:
- Jeder Job muss in der GUI klar lesbar dargestellt werden.
- Die Job List muss so aufgebaut sein, dass der Nutzer Algorithmus, Parameter und Zielwert pro Job nachvollziehen kann.
- Die GUI darf zusätzliche Metadaten wie `display_label` oder Seed-Override unterstützen.
- Die Reihenfolge der Jobs muss stabil bleiben, sofern das Projekt nichts anderes festlegt.

## Pflicht-Controls
Die GUI muss mindestens folgende Controls enthalten:
- Start (ein Button) + Run-Modus-Selektor (RadioButtons: Single / Compare / Sweep)
- Pause
- Resume
- Cancel
- Reset
- Save Config
- Load Config
- Animation Window"-Button ist nur aktiv wenn Animation konfiguriert ist
- Export Plot
- **Trainingslimit-Felder (beide Pflicht im Training-Bereich):**
  - `total_timesteps`: Spinbox, Default projektspezifisch, Wert `0` = ignorieren
  - `total_episodes`: Spinbox, Default projektspezifisch, Wert `0` = ignorieren
  - Hinweis-Label: „Training endet beim ersten erreichten Limit; 0 = ignorieren"
  - Beide Felder müssen gleichwertig nebeneinander angeboten werden.
    Das Projekt legt die Defaults fest; die 0-Semantik ist global verbindlich
    (siehe `workbench_logic.md` → CRITICAL RULE: Laufzeitgrenzen).

Zusätzliche Regeln:
- Button-Zustände müssen den aktuellen Laufzustand widerspiegeln.
- Nicht sinnvolle Aktionen müssen während eines Zustandswechsels deaktiviert sein.
- Cancel und Pause müssen auf alle aktiven Worker der aktuellen Session wirken.
- Save Config und Load Config dürfen während eines aktiven Laufs deaktiviert werden.
- Single ist der Default-Modus und immer ohne vorherige Auswahl ausführbar. Compare und Sweep müssen per Modus-Selektor explizit aktiviert werden. Der Start-Button löst immer den aktuell gewählten Modus aus.

### Reset-Semantik
Reset setzt die GUI in den Initialzustand zurück:
- alle Parameter werden auf projektspezifische Defaults zurückgesetzt
- die Job List wird geleert oder auf projektspezifische Defaults zurückgesetzt
- der Live-Plot wird geleert
- der Current-Run-Bereich zeigt `Status: idle`
- ein laufender Lauf muss vor Reset erst explizit abgebrochen werden; Reset während eines aktiven Laufs ist zu deaktivieren oder löst einen Cancel aus, bevor Reset wirkt

### Export-Plot-Button
- Der Export-Plot-Button speichert den aktuellen Live-Reward-Plot als PNG nach plots/ mit Zeitstempel im Dateinamen. Er ist aktiv, sobald Plotdaten vorhanden sind — unabhängig vom Laufzustand. Nach dem Export zeigt die GUI eine kurze Bestätigung mit dem Exportpfad.


## Initialzustand
Beim Programmstart gilt:
- alle Parameter sind mit projektspezifischen Defaults vorausgefüllt
- Start ist aktiv, Modus-Selektor zeigt Single
- Save Config und Load Config sind aktiv
- Pause, Resume und Cancel sind deaktiviert
- Export Plot ist aktiv, sofern Plotdaten vorhanden
- der Current-Run-Bereich zeigt `Status: idle`
- das Environment-Panel zeigt eine statische Vorschau, einen Platzhalter oder ist leer, aber nicht fehlerhaft
- der Live-Plot ist leer und bereit
- die Job List ist leer oder projektspezifisch vorbelegt, aber konsistent darstellbar
- die Animation kann eingebettet oder in einem separaten Fenster angeboten werden

## Standardisierte Eingabetypen
Verwende einheitliche Eingabetypen:
- Checkbox für Bool-Werte
- Entry oder Spinbox für numerische Werte
- Dropdown für diskrete Optionen
- read-only Label für abgeleitete oder nicht editierbare Werte

Empfehlungen:
- numerische Felder sollen validiert werden
- diskrete Werte sollen bevorzugt als Dropdown dargestellt werden
- projektspezifische Spezialfelder müssen nach demselben Muster eingeordnet werden
- Das Learning-Rate-Schedule-Dropdown muss mindestens folgende Optionen unterstützen:
  `constant`, `linear`, `inverse_time`. Projektspezifische Erweiterungen sind zulässig. Default ist `constant`.

## Projektspezifische Controls
Projektspezifische Controls sind erlaubt, aber nur unter folgenden Bedingungen:
- sie werden einem bestehenden Pflichtbereich zugeordnet
- ihre Semantik ist aus der projektspezifischen Datei ableitbar
- sie verletzen nicht die globale Layout- oder Bedienlogik
- sie dürfen Standard-Controls nicht ersetzen, sondern nur ergänzen oder präzisieren

## Run-Modi in der GUI

### `Run`
- startet genau einen ausgewählten Algorithmus

### `Compare`
- Die Auswahl der zu vergleichenden Algorithmen muss über einzelne Checkboxen oder eine gleichwertig klare Mehrfachauswahl erfolgen.
- Der Compare-Lauf startet alle ausgewählten Algorithmen **parallel** als separate Hintergrund-Worker-Threads.
- Das Live-Plot-Fenster zeichnet die Ergebnisse aller ausgewählten Algorithmen übereinander, farblich getrennt und mit Legende.
- Der Plot wird fortlaufend durch die asynchron eintreffenden Events aktualisiert.

### `Sweep`
- startet alle Jobs der aktuellen Job List
- jeder Job wird als eigener Lauf dargestellt
- die GUI muss Sweep-Jobs im Plot und Statuskontext unterscheidbar halten

## Event-Pump und Worker-Bridge
Verwende eine Queue-/Event-Bridge zwischen Workern und GUI mit `after()`-Polling im Main-Thread.

Pflichtregeln:
- Die Event-Pump muss in der Lage sein, eingehende Events von **mehreren parallel laufenden Workern** simultan zu verarbeiten.
- Die Worker müssen mindestens über `algorithm_name`, `display_label` oder `run_id` unterscheidbar sein.
- Die GUI muss Events aus `single_run`, `algo_compare` und `sweep_run` mit demselben Pump-Mechanismus verarbeiten können.
- Die Queue darf in der Event-Pump nicht durch eine unbegrenzte `while True`-Schleife geleert werden; sie muss auf eine maximale Batch-Größe begrenzt werden, um UI-Freezes zu verhindern.
- Plot-Aktualisierungen müssen zeitlich gedrosselt werden, da Matplotlib-Redraws den Main-Thread massiv belasten.
- veröffentliche strukturierte Events vom Typ `step`, `episode`, `episode_aux`, `training_done`, `error`
- markiere von Workern stammende Events in der GUI-seitigen Worker-Bridge mit `session_id`
- ignoriere veraltete Session-Events in der Event-Pump
- halte das Register aktiver Worker thread-sicher
- registriere Worker vor dem Start von Jobs, damit Pause sofort wirken kann
- die Event-Pump muss während des Trainings fortlaufend Plot- und Animationsupdates verarbeiten statt diese bis zum Laufende aufzuschieben
- die GUI muss pro `run_id` einen stabilen Anzeigeeintrag für Plot, Status und Abschlussdaten führen können

## Event-Verarbeitung je Typ
Die GUI verarbeitet Events nach dem gemeinsamen Event-Vertrag.

### `step`
- optional
- für feingranulare Statusanzeige, Diagnose und step-nahe Animation
- kann zur Aktualisierung des Environment-Panels oder Animationsfensters verwendet werden
- darf nie Voraussetzung für korrekte GUI-Funktion sein
- soll bei hoher Last throttled verarbeitet werden

### `episode`
- primäres UI-Event
- aktualisiert Fortschritt, Statusfelder und leichte Plotdaten
- wird bevorzugt schnell verarbeitet
- darf keine schweren Payloads transportieren
- muss den sichtbaren Live-Plot während des Runs fortschreiben

### `episode_aux`
- verarbeitet schwere Payloads wie `frames` oder umfangreichere `eval_points`
- darf zeitversetzt verarbeitet werden
- darf den primären Fortschrittspfad nicht blockieren
- soll Rollout-Frames möglichst schon während des laufenden Trainings anzeigen statt erst nach `training_done`

### `training_done`
- finalisiert den Laufzustand in der GUI
- wird immer verarbeitet, auch bei Cancel
- setzt Abschlussstatus, reaktiviert Buttons in geeigneter Weise und übernimmt Abschlussmetriken oder Exporthinweise
- darf keine verspätete Erst-Darstellung des gesamten Trainingsverlaufs ersetzen

### `error`
- zeigt strukturierte Fehlermeldungen an
- trennt benutzerfreundliche Meldung und technische Details
- kann vor einem abschließenden `training_done` auftreten

## Current-Run-Bereich
Der Current-Run-Bereich muss mindestens anzeigen:
- aktuellen Status
- aktuelle Episode und Gesamtanzahl
- aktuellen Reward
- Moving Average
- Best Reward
- Total Steps (kumulierte Schritte des laufenden Laufs)
- aktiven Algorithmus oder Anzeige-Label
- aktiven Run-Modus, falls relevant
- aktuelle `run_id`
- optional Job-Kontext bei Sweep-Läufen

Regeln:
- Die Anzeige muss primär auf `episode`-Events basieren.
- Alle live angezeigten Metriken — einschließlich `Total Steps` — müssen
  mit jedem `episode`-Event aktualisiert werden und dürfen nicht bis
  `training_done` aufgeschoben werden.
- Abschlussdaten dürfen bei `training_done` final überschrieben oder ergänzt werden.
- Fehlerzustände müssen klar sichtbar sein.

- Layout-Regel: Die Status-Felder werden in einem 4-spaltigen grid dargestellt (2 Label+Value-Paare pro Zeile). Das reduziert den Höhenbedarf des mittleren Panels auf ca. 3 Zeilen.

- Pflichtfelder im Hauptfenster (die restlichen nur im Status-Popup):
Status, Episode, Step Reward, Episode Reward, Moving Average, Best Reward, Total Steps, Episode Steps, Active Algorithm, Configured Algorithm, Message, Animation.

- Ins Status-Popup ausgelagert (nicht im Hauptfenster): Session ID, Run ID, Last Update, Completion Reason.

Fortschrittsanzeige (Pflicht):
Der Current-Run-Bereich muss eine ttk.Progressbar enthalten.  
- Platzierung: unterhalb des Status-Grids, über die volle Breite des Current-Run-Frames
- Modus: determinate, wenn total_episodes oder total_timesteps > 0; sonst indeterminate
- Wert: (aktuelle_episode / total_episodes) * 100 bzw. (total_steps / total_timesteps) * 100 — projektspezifisch, welche Größe bevorzugt wird
- Im Compare-Modus: Fortschritt = Maximum aller aktiven Worker (nicht Durchschnitt)
- Bei `trainingdone` oder Cancel: Balken auf 100% bzw. auf den erreichten Wert einfrieren
- Bei Reset: Balken auf 0 zurücksetzen
- Die Progressbar darf keine eigene Zeile im 4-Spalten-Status-Grid belegen; sie liegt strukturell außerhalb des Grids als separates Widget

## Live-Plot-Regeln
Der Live-Plot muss leichtgewichtig aktualisiert werden.

Pflichtregeln visuelle Darstellung:
- Die Kurven für einzelne Episoden (Rohdaten) müssen mit starker Transparenz gezeichnet werden.
- Die Moving-Average-Linie muss opak und mit höherer Linienstärke dargestellt werden, um den Trend klar hervorzuheben.

Weitere Plot-Regeln:
- primäre Plot-Aktualisierung erfolgt über `episode`
- schwere oder umfangreichere Datenaktualisierungen dürfen über `episode_aux` ergänzt werden
- Compare- und Sweep-Läufe müssen grafisch sauber trennbar sein
- verschiedene Algorithmen oder Jobs müssen eindeutig unterscheidbar sein
- der Plot muss während des laufenden Trainings sichtbar wachsen und darf nicht erst nach Run-Ende gezeichnet werden
- die GUI soll Plotdaten inkrementell fortschreiben statt am Ende aus einer Gesamtliste neu aufbauen
- optionale projektspezifische Erweiterungen sind erlaubt, sofern der Hauptplot nicht unlesbar wird

## Environment-Animation
Die Environment-Darstellung muss als echte Live-Animation ausgelegt sein.

Pflichtregeln:
- Die Animation darf eingebettet im Hauptfenster oder in einem separaten Animationsfenster umgesetzt werden.
- Das Environment-Panel oder Animationsfenster muss während des Runs fortlaufend aktualisiert werden, sofern Animation aktiviert ist.
- Nicht nur erfolgreiche Rollouts, sondern alle Versuche sollen live darstellbar sein, sofern Rendering aktiviert ist.
- Die GUI darf nicht nur den letzten erfolgreichen Pfad nachträglich anzeigen.
- step-basierte Einzelbilder oder frame-basierte Chunks müssen inkrementell verarbeitet werden.
- Bei hoher Update-Last darf die Anzeige gedrosselt werden, aber nicht auf reine Nachlaufdarstellung zurückfallen.
- Die zuletzt sichtbare Darstellung darf nach Run-Ende bestehen bleiben, ersetzt aber nicht die Live-Anzeige während des Runs.

### Animation-Schalter
- Die GUI muss einen Animation-Schalter bereitstellen.
- Änderungen an diesem Schalter müssen live wirken, ohne einen laufenden Run zu unterbrechen.
- Die GUI übermittelt den neuen Animationszustand unmittelbar an die Logik-Schicht.
- Wenn Animation deaktiviert wird, stoppt die Anzeige sofort; der zuletzt sichtbare Frame bleibt stehen oder die Anzeige zeigt einen Platzhalter.
- Wenn Animation aktiviert wird, nimmt die Anzeige mit dem nächsten eintreffenden Frame wieder auf.
- Ein separates Animationsfenster darf eigene Controls wie Öffnen, Schließen oder lokalen Anzeige-Toggle besitzen, solange die globale Semantik konsistent bleibt.
- Animation ist Startkonfiguration (wie GPU), kein Runtime-Toggle; Fenster öffnet automatisch beim Start wenn aktiviert
- "Animation enabled"-Checkbox und "Use GPU" werden während eines laufenden Runs deaktiviert

## Session- und Run-Handling
Pause, Resume und Cancel müssen alle aktiven Worker-Trainer der aktuellen Session steuern.

Pflichtregeln:
- aktives Worker-Register ist thread-sicher mit Lock
- veraltete Session-Events werden verworfen
- Compare- und Sweep-Läufe werden pro `run_id` eindeutig verfolgt
- `single_run`, `algo_compare` und `sweep_run` müssen in Status, Plot und Exportdarstellung unterscheidbar sein
- **Paralleles Compare:** `algo_compare` arbeitet zwingend parallel
- Sweep-Läufe müssen mit derselben Session-Logik kompatibel bleiben

## Skalierung und kleine Displays
Die GUI muss auch bei kleineren Fenstern benutzbar bleiben.

Regeln:
- zentrale Informationen dürfen nicht außerhalb des sichtbaren Bereichs verschwinden
- das Parameter-Panel bleibt scrollbar
- Bedienelemente müssen erreichbar bleiben
- Plot und Current-Run-Bereich müssen sinnvoll schrumpfen oder den verfügbaren Raum flexibel nutzen
- Mindestgrößen und Resize-Verhalten sind so zu wählen, dass keine Kernfunktion verloren geht

## Plot-Darstellung und Farbschema

Der Live-Reward-Plot verwendet ein verbindliches Dark-Theme mit folgenden
exakten Farbwerten:

### Hintergrund und Achsen
- Figure-Hintergrund: `#0f111a`
- Axes-Hintergrund: `#0f111a`
- Tick-Farben: `#b5b5b5`
- Achsen-Labels (X und Y): `#b5b5b5`
- Grid: Farbe `#2a2f3a`, gestrichelt, Alpha `0.5`

### Linien-Darstellung
- **Raw-Episoden-Linie (erste):** Farbe `#4cc9f0`, Alpha `0.35`,
  Linienbreite `1.0` — im Hintergrund
- **Moving-Average-Linie (erste):** Farbe `#4cc9f0`, Alpha `1.0`,
  Linienbreite `2.5` — im Vordergrund
- **Weitere Algorithmen (Compare/Sweep):** Gleicher Stil (Raw: Alpha 0.35,
  LW 1.0; Average: Alpha 1.0, LW 2.5), aber mit kontrastierenden Farben
  (z. B. `#f72585`, `#7209b7`, `#3a0ca3`, `#4361ee`, `#4cc9f0` als Palette)

### Legende
- Facecolor: `#0f111a`
- Edgecolor: `#2a2f3a`
- Labelcolor: `#e6e6e6`
- Inhalt: Algorithmus-Name (`algorithm_name` oder `display_label`);
  bei Sweep-Läufen zusätzlich Parameter-Name und Wert

### Regeln
- Raw-Daten werden als dünne Linie im Hintergrund gezeichnet
- Moving Average wird als dicke Linie im Vordergrund gezeichnet
- Das Farbschema darf projektspezifisch um weitere Farben erweitert,
  aber nicht durch ein abweichendes Theme ersetzt werden
- PNG-Exporte müssen dasselbe Farbschema verwenden wie der Live-Plot

## Status- und Fehlerdarstellung
Status- und Fehlermeldungen müssen konsistent sein.

Regeln:
- Statusmeldungen sollen klar und knapp sein
- technische Fehlerdetails dürfen von der nutzerfreundlichen Anzeige getrennt werden
- GUI-Zustand muss nach `training_done` immer deterministisch abgeschlossen sein
- Fehlerzustände dürfen nicht zu hängenden oder widersprüchlichen Button-Zuständen führen
- bei `error_stage: env_build` muss die GUI eine benutzerfreundliche Fehlermeldung anzeigen, den Button-Zustand auf idle zurücksetzen und eine erneute Konfiguration ermöglichen

## GUI-Tests
Die GUI-Tests müssen mindestens prüfen:
- grundlegenden Aufbau der Hauptbereiche
- Verfügbarkeit der Pflicht-Controls
- Verfügbarkeit von Run, Compare, Sweep Run, Save Config und Load Config
- korrekten Initialzustand beim Programmstart
- Verarbeitung von `episode`, `episode_aux`, `training_done` und `error`
- korrekte Aktualisierung von Statusanzeigen
- Reaktion auf Pause, Resume und Cancel
- Session-Isolation gegenüber veralteten Events
- saubere Behandlung paralleler Compare-Läufe
- saubere Behandlung von `single_run`, `algo_compare` und `sweep_run`
- korrekte Darstellung und Manipulation der Job List
- Wiederherstellung eines gespeicherten Konfigurationszustands in der GUI
- Stabilität bei kleineren Fenstergrößen oder Resize-Situationen
- inkrementelle Live-Aktualisierung des Plots während eines laufenden Runs
- inkrementelle Live-Aktualisierung der Environment-Animation statt reiner Nachlaufdarstellung
- korrektes Verhalten des Reset-Buttons
- Live-Wirkung des Animation-Schalters ohne Unterbrechung eines laufenden Runs
- korrekte Unterstützung eines separaten Animationsfensters, sofern diese Variante verwendet wird
- eindeutige Zuordnung von Plot- und Statusdaten über `algorithm_name`, `display_label` und `run_id`
- Korrektes Verhalten des Run-Modus-Selektors (Default Single, Start löst richtigen Handler aus)
- Export-Plot-Button: erzeugt PNG, zeigt Bestätigung
- Checkboxen für Startkonfiguration (Animation, GPU) sind während Training deaktiviert
- korrekte Aktualisierung der Progressbar bei episode-Events und Reset
- korrekte Progressbar-Berechnung im Compare-Modus (Maximum aller Worker)
- korrekte Enddarstellung bei trainingdone und Cancel

## Recent Critical Architecture Rules

**CRITICAL RULES: Compare Mode, Multithreading & Teardown**
- **Animation im Compare-Modus:** Bei parallelen Compare-Läufen darf die Animation nur für einen ausgewählten Algorithmus oder eine ausgewählte Quelle sichtbar geführt werden. Dies verhindert visuelles Flackern und konkurrierende Render-Updates.
- **Fortschrittsanzeige im Parallelbetrieb:** Die Fortschrittsanzeige muss auch bei parallelen Läufen aktualisiert werden und darf nicht blockieren oder einfrieren. → Implementierungsregel: siehe Abschnitt „Current-Run-Bereich – Fortschrittsanzeige"
- **Sauberes Beenden:** Beim Schließen des Hauptfensters (`WM_DELETE_WINDOW` / `on_closing`) muss die UI über das Register aller aktiven Worker iterieren und diese explizit stoppen (`cancel()`), damit keine Hintergrund-Threads als Zombies weiterlaufen.