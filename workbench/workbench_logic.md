# workbench_logic.md

version: 2.0
last_updated: 2026-04-30
compatible_with:
  workbench: "2.0"

## Zweck und Geltungsbereich
Diese Datei definiert die generische Logik- und Trainingsarchitektur für Reinforcement-Learning-Projekte mit Gymnasium. Sie enthält projektübergreifende Regeln für Environment-Abstraktion, Agent-/Algorithmus-Abstraktion, Training, Evaluierung, Event-Emission, Run-Modi, Compare-Verhalten, Sweep-Orchestrierung, Exporte und Logiktests.

Diese Datei ist generisch zu halten und darf nicht auf ein einzelnes Environment oder ausschließlich auf tabellarische RL-Verfahren zugeschnitten werden. Die Regeln müssen sowohl für tabellarische Verfahren als auch später für neuronale Netze und optionale SB3-basierte Implementierungen anwendbar bleiben.

## Architekturprinzipien
Implementiere eine klare Trennung zwischen:
- Environment-Abstraktion
- Agent-/Algorithmus-Abstraktion
- Algorithmus-Ebene
- TrainLoop-Ebene
- UI-unabhängiger Orchestrierung

Ziele dieser Trennung:
- Wiederverwendbarkeit für headless Läufe und Tests
- saubere Erweiterbarkeit für tabellarische, neuronale und SB3-nahe Verfahren
- Entkopplung von GUI und Trainingslogik
- deterministisches Laufzeitverhalten und klare Zustandsübergänge

## Environment-Abstraktion
Implementiere eine Wrapper-Klasse für die Umgebung mit mindestens folgenden Verantwortlichkeiten:
- Erzeugung der Gymnasium-Umgebung
- Neubau der Umgebung bei geänderten Parametern
- Aktualisierung der Environment-Konfiguration
- Reset der Umgebung
- Step-Zugriff
- Render-Zugriff
- Seed-Verarbeitung
- optionaler Zugriff auf projektbezogene Hilfsfunktionen

Anforderungen:
- Environment-spezifische Details müssen gegenüber Trainer und GUI gekapselt werden.
- Änderungen an Environment-Parametern müssen reproduzierbar in einen Neubau oder ein Update der Umgebung überführt werden.
- Die Logik muss sowohl interaktive Läufe als auch Tests ohne GUI unterstützen.
- Der Environment-Wrapper muss einen konfigurierbaren `render_mode` unterstützen.
- Beim initialen Build wird `render_mode` aus dem aktuellen Animationszustand übernommen (`"rgb_array"` oder `None`).
- Ein Live-Wechsel des Animationszustands während eines laufenden Trainings erfordert keinen Neubau der Umgebung.
- Stattdessen unterdrückt die Logik die Frame-Emission vollständig, wenn Animation deaktiviert ist, unabhängig davon, ob Gymnasium intern weiter rendert.
- Die Logik muss einen `set_animation(enabled: bool)`-Aufruf oder ein gleichwertiges Steuerprimitiv bereitstellen, das thread-sicher während eines laufenden Runs wirkt.
- Animation ist eine Startkonfiguration. Ein nachträglicher Wechsel von None auf rgb_array mid-run wird nicht unterstützt (erfordert Umgebungs-Rebuild).
- Wurde die Umgebung mit render_mode="rgb_array" gestartet, kann Animation mid-run deaktiviert und wieder aktiviert werden. Die Logik steuert dabei ausschließlich die Frame-Emission via set_animation_enabled(),
  d.h. kein Rebuild der Umgebung ist erforderlich.
- Ob und welche render_mode-Werte ein Environment unterstützt, ist projektspezifisch in <project_name>.md zu deklarieren.

## Agent-/Algorithmus-Abstraktion
Verwende eine generische Agent-/Algorithmus-Abstraktion anstelle einer ausschließlich frameworkspezifischen oder projektspezifischen Lösung.

Die Abstraktion muss folgende Algorithmus-Klassen unterstützen:
- tabellarische Verfahren
- neuronale Netzverfahren
- optionale SB3-basierte Verfahren

Die Agent-/Algorithmus-Abstraktion soll mindestens kapseln:
- Modell-, Tabellen- oder Policy-Konstruktion
- Aktionsauswahl
- Lern-/Update-Primitiven
- algorithmusspezifische Initialisierung
- Laden gemeinsamer und algorithmusspezifischer Hyperparameter
- Bereitstellung einer lesbaren Algorithmus-Bezeichnung für GUI, Exporte, Compare und Sweep
- **GPU-Unterstützung:** Die Implementierungen müssen dynamische Hardware-Beschleunigung (CPU vs. GPU via CUDA/MPS) unterstützen. Die Auswahl erfolgt strikt über die übergebene Konfiguration (`use_gpu: bool`).
- **Framework:** Wenn ein Projekt neuronale Netzwerke verwendet, gilt zwingend:
  - Stable Baselines 3 (SB3) als RL-Bibliothek
  - PyTorch als Backend — Keras und TensorFlow sind nicht zulässig
  - `model.predict()` darf nicht direkt verwendet werden, wenn
    performantere Alternativen verfügbar sind
  - Trainingsdaten müssen als `float32` vorliegen; implizite Casts sind zu vermeiden
  - Updates müssen in sinnvollen Batches durchgeführt werden (Overhead reduzieren)
  - Numpy/Torch-Operationen sind Python-Schleifen vorzuziehen (Vektorisierung)
  - PyTorch-Kompilierung (`torch.compile`) darf projektspezifisch eingesetzt werden, ist aber keine globale Pflicht

Regeln:
- Gemeinsame Hyperparameter dürfen projektübergreifend standardisiert benannt werden.
- Algorithmusabhängige Felder wie epsilon, learning_rate, Netzarchitektur, Replay-, Batch- oder Noise-Parameter bleiben standardisiert benennbar, aber optional.
- Die Abstraktion muss sowohl einen reinen Einzellauf als auch parallele Compare- und Sweep-Läufe ohne gegenseitige Zustandsverschmutzung unterstützen.

## Algorithmus-Ebene
Die Algorithmus-Ebene ist verantwortlich für:
- interne Modell-, Tabellen- oder Policy-Repräsentation
- Aktionsauswahl
- Lernschritt / Update-Regel
- algorithmusspezifische Zustandsführung
- Zugriff auf algorithmusspezifische Metriken

Regel:
- Die Algorithmus-Ebene darf keine GUI-spezifische Logik enthalten.

## TrainLoop-Ebene
Die TrainLoop-Ebene orchestriert:
- Episodenstart und Episodenende
- Step-Ausführung innerhalb einer Episode
- **Laufzeitgrenzen:** Das Trainingsende muss an `total_timesteps` und/oder an einer konfigurierbaren `total_episodes`-Grenze festgemacht werden können (was zuerst erreicht wird)
- Stop-/Pause-/Resume-/Cancel-Behandlung
- Sammeln leichtgewichtiger Metriken
- periodische Evaluations-Checkpoints
- Emission strukturierter Events

Die TrainLoop-Ebene ist verantwortlich für deterministische Statusübergänge und die kontrollierte Emission aller GUI-relevanten Ereignisse.

## Trainer-Schnittstelle
Der Trainer muss mindestens folgende Methoden oder gleichwertige Steuerprimitive bereitstellen:
- `run_episode(...)`
- `train(...)`
- `evaluate_policy(...)` oder eine gleichwertige Evaluationsmethode
- Neubau oder Aktualisierung der Umgebung
- `set_animation(enabled: bool)` oder gleichwertiges Live-Steuerprimitiv
- periodische deterministische Evaluations-Checkpoints

Weitere Regeln:
- `run_episode(...)` muss die tatsächlich ausgeführten Umgebungsschritte zurückgeben, auch wenn Transition-Collection deaktiviert ist.
- `train(...)` muss headless und GUI-gekoppelt nutzbar sein.
- `evaluate_policy(...)` muss unabhängig vom Haupttraining aufrufbar sein.
- `evaluate_policy(...)` muss mindestens zurückgeben: mittlerer Reward über alle Evaluationsepisoden, Standardabweichung des Rewards, Anzahl durchgeführter Evaluationsepisoden.
- `evaluate_policy(...)` darf optional Events emittieren, ist aber nicht verpflichtet dazu. Wenn Events emittiert werden, muss der Typ `episode_aux` verwendet werden.
- `evaluate_policy(...)` darf den primären Trainingsfortschritt nicht blockieren.
- Der Trainer muss in parallelen Läufen über `run_id` und `algorithm_name` eindeutig unterscheidbar bleiben.

## Event- und Datenvertrag
Zwischen Logik und GUI wird ein einheitlicher Event-Vertrag verwendet.

### Gemeinsame Pflichtfelder aller Events
Jedes Event muss mindestens enthalten:
- `type`
- `session_id`
- `run_id`
- `timestamp`
- `source`
- `status`
- `algorithm_name`

Zusätzliche allgemeine optionale Felder:
- `run_mode`
- `display_label`
- `message`

Regeln:
- `session_id` wird in der GUI-seitigen Worker-Bridge ergänzt oder bestätigt, damit veraltete Events aus früheren oder ersetzten Läufen verworfen werden können.
- `run_id` identifiziert einen konkreten Lauf innerhalb einer Session.
- `status` beschreibt maschinenlesbar den aktuellen Laufzustand.
- `algorithm_name` dient der eindeutigen Zuordnung bei Einzel-, Compare- und Sweep-Läufen.
- `display_label` darf für GUI, Plot-Legende und Job-Darstellung verwendet werden und kann vom reinen `algorithm_name` abweichen.
- `run_mode` kennzeichnet, ob ein Event zu `single_run`, `algo_compare` oder `sweep_run` gehört.

### Zulässige Event-Typen
- `step`
- `episode`
- `episode_aux`
- `training_done`
- `error`

### Allgemeine Event-Regeln
- `episode` ist das primäre UI-Event.
- `step` ist optional und dient nur feiner Statusanzeige oder Diagnose.
- schwere Payloads dürfen nicht im schnellen Metrikpfad von `episode` transportiert werden.
- schwere Daten wie `frames` oder umfangreichere `eval_points` müssen bevorzugt über `episode_aux` emittiert werden.
- `training_done` muss immer emittiert werden, auch bei Cancel oder Fehlern, damit die GUI einen deterministischen Abschlusszustand verarbeiten kann.
- Live-Darstellung darf nicht erst nach Episoden- oder Run-Ende erfolgen; relevante visuelle Zwischenstände müssen schon während des laufenden Trainings emittiert werden.
- Wenn Rendering oder Frame-Streaming aktiviert ist, müssen nicht nur erfolgreiche Episoden, sondern alle ausgeführten Versuche live visualisierbar sein.

## Event-Typen im Detail

### `step`
`step` ist optional.

Verwendung:
- feingranulare Statusanzeige
- Diagnosezwecke
- step-nahe visuelle Aktualisierung während laufender Episoden
- Grundlage für throttled Animation oder Zustandsaktualisierung

Empfohlene Felder zusätzlich zu den gemeinsamen Metadaten:
- `step_index`
- `episode`
- `state`
- `action`
- `reward`
- `done`
- `truncated`
- `render_state`
- `frame`

Regeln:
- `step` darf nie Voraussetzung für die korrekte GUI-Funktion sein.
- `step` soll throttled emittiert werden, wenn viele Updates die GUI sonst überlasten würden.
- Wenn Live-Animation aktiviert ist, muss die Logik eine ausreichend dichte Folge von visuellen Updates liefern, damit nicht erst der Endzustand sichtbar wird.

### `episode`
`episode` ist das primäre UI-Event für Fortschritt, Status und Live-Plot.

Pflichtfelder zusätzlich zu den gemeinsamen Metadaten:
- `episode`
- `episodes`
- `reward`
- `moving_average`
- `steps`
- `best_reward`

Optionale standardisierte Felder:
- `eval_points`
- `render_state`
- `epsilon`
- `lr`
- `seed`
- `run_mode`
- `display_label`
- `message`
- `total_steps` 

Semantik:
- `episode` und `episodes` sind GUI-tauglich und 1-basiert.
- `steps` bezeichnet die tatsächlich ausgeführten Schritte dieser Episode.
- `eval_points` in `episode` dürfen nur leichtgewichtige Daten enthalten.
- `render_state` ist für GUI-kompatible Zustandsdarstellung erlaubt, aber optional.
- algorithmusabhängige Felder wie `epsilon` oder `lr` sind nur zu setzen, wenn sie fachlich sinnvoll sind.
- Der Live-Plot muss spätestens mit jedem `episode`-Event fortgeschrieben werden und darf nicht bis zum Laufende gepuffert werden.

### `episode_aux`
`episode_aux` transportiert schwere Zusatzdaten, die nicht im schnellen Metrikpfad verarbeitet werden sollen.

Pflichtfelder zusätzlich zu den gemeinsamen Metadaten:
- `episode`

Optionale Felder:
- `frames`
- `frame`
- `eval_points`
- `render_state`
- `artifacts`
- `diagnostics`
- `message`

Semantik:
- `frames` ist der bevorzugte Schlüssel für Rollout-Frames.
- `frame` bleibt nur als optionaler Kompatibilitätsschlüssel erlaubt.
- umfangreiche Evaluationsdaten oder Rendering-Zusatzdaten gehören in `episode_aux`.
- Die GUI darf `episode_aux` ignorieren, ohne den Kernfortschritt zu verlieren.
- Wenn vollständige Rollouts gesammelt werden, sollen sie möglichst episodenweise oder chunkweise schon während des Runs an die GUI geliefert werden statt erst nach `training_done`.
- Falls Performancegrenzen erreicht werden, sollen Frames chunkweise und throttled gestreamt werden, nicht erst gesammelt und am Ende angezeigt werden.
- Projektspezifische Zusatzfelder in `episode_aux` müssen in der projektspezifischen Datei deklariert werden.
- Undokumentierte Felder gelten als nicht vertragskonform.
- Feldnamen dürfen keine standardisierten Pflichtfelder überschreiben.

### `training_done`
`training_done` ist das verpflichtende Abschlussereignis eines Laufs.

Pflichtfelder zusätzlich zu den gemeinsamen Metadaten:
- `completion_reason`
- `episodes_completed`
- `episodes_planned`
- `run_mode`

Optionale Felder:
- `best_reward`
- `final_reward`
- `moving_average_final`
- `total_steps_completed`
- `eval_summary`
- `export_paths`
- `summary_metrics`
- `job_index`
- `job_count`
- `message`

Regeln:
- `status` muss hier einen finalen Zustand tragen, typischerweise `completed`, `cancelled` oder `failed`.
- `completion_reason` beschreibt die genauere Ursache, zum Beispiel `finished`, `cancel_requested`, `early_stop` oder `error`.
- `training_done` muss auch bei Cancel emittiert werden.
- Nach einem Fehler kann zuerst `error` und anschließend `training_done` mit `status = failed` emittiert werden.
- `training_done` darf keine bis dahin zurückgehaltenen Live-Plot- oder Animationsdaten gesammelt nachliefern, die schon während des Runs hätten sichtbar sein sollen.
- `training_done` muss bei Sweep-Läufen pro Job separat emittiert werden.
- In `sweep_run` darf `job_index` / `job_count` zur GUI-Zuordnung verwendet werden.
- `summary_metrics` soll bei Compare- und Sweep-Läufen Seed-, Job- und Parameterkontext nachvollziehbar enthalten.

### `error`
`error` ist das strukturierte Fehlerereignis.

Pflichtfelder zusätzlich zu den gemeinsamen Metadaten:
- `error_code`
- `error_message`
- `error_stage`

Optionale Felder:
- `details`
- `exception_type`
- `traceback`
- `recoverable`
- `message`

Regeln:
- `status` ist bei `error` immer `failed`.
- `error_message` ist GUI-tauglich und benutzerorientiert.
- technische Details gehören in `details`, `exception_type` und `traceback`.
- `error_stage` muss projektübergreifend vergleichbare Fehlerquellen benennen, zum Beispiel `config`, `env_build`, `train_loop`, `evaluate`, `export` oder `ui_bridge`.

## Laufzeitverhalten
Das Laufzeitverhalten muss deterministisch und UI-freundlich sein.

Pflichtregeln:
- Die Logik muss bei aktivierter Live-Animation den TrainLoop künstlich drosseln (z. B. durch `time.sleep`), damit die Framerate für das menschliche Auge sichtbar bleibt und der GUI-Thread nicht durch CPU-Starvation blockiert wird.
- Training darf die GUI nicht blockieren.
- Pause, Resume, Cancel und Stop müssen sauber und reproduzierbar wirken.
- Statusübergänge müssen eindeutig und testbar sein.
- Ein abgebrochener oder ersetzter Lauf darf keine veralteten Events in einer neuen Session wirksam machen.
- Worker-seitige Aktivitäten müssen mit GUI-seitigem Session-Filtering kombinierbar sein.
- Live-Plot und Environment-Animation müssen während des Runs fortlaufend aktualisiert werden.
- Visuelle Updates dürfen nicht bis zum Laufende zurückgehalten werden.
- Schlägt der Environment-Build fehl, muss die Logik ein `error`-Event mit `error_stage: env_build` emittieren und anschließend `training_done` mit `status: failed` und `completion_reason: error` senden.
- Ein fehlgeschlagener Build darf keinen inkonsistenten Laufzustand hinterlassen.
- Die Logik muss danach in den `idle`-Zustand zurückkehren.

Erwartete Zustandslogik:
- `idle -> running -> paused -> running -> completed`
- `idle -> running -> cancelled`
- `idle -> running -> failed`

## Update-Rate
Die Update-Rate muss getrennt nach Zweck behandelt werden.

Regeln:
- `episode` ist der primäre Takt für GUI-Fortschritt und Plot-Aktualisierung.
- `step` darf optional und throttled verwendet werden.
- Plot- und GUI-Aktualisierung dürfen nicht durch schwere Evaluations- oder Frame-Daten blockiert werden.
- umfangreiche Auswertungen müssen über `episode_aux` oder beim Abschluss transportiert werden.
- Evaluations-Checkpoints müssen deterministisch in definierter Kadenz stattfinden.
- Es muss mindestens drei getrennte Update-Takte geben: Metrik-Takt, Animations-/Frame-Takt und Evaluations-/Schwerlast-Takt.
- Der Metrik-Takt soll eng genug sein, damit der Plot sichtbar live wächst.
- Der Animations-/Frame-Takt soll alle Versuche sichtbar machen, kann aber zur GUI-Stabilität gedrosselt werden.
- Der Evaluations-/Schwerlast-Takt darf den Live-Pfad nicht blockieren.

## Run-Modi
Die Workbench-Logik muss drei generische Laufmodi unterstützen.

### `single_run`
- startet genau einen ausgewählten Algorithmus
- erzeugt genau einen Trainer-Lauf mit eigener `run_id`
- dient dem normalen interaktiven Trainingslauf

### `algo_compare`
- startet mehrere ausgewählte Algorithmen parallel
- jeder Algorithmus läuft in eigenem Worker-Kontext mit eigener `run_id`
- gemeinsame GUI-Session und gemeinsamer Plot-Kontext bleiben erhalten
- Parameter-Isolation zwischen den Algorithmen ist verpflichtend

### `sweep_run`
- startet mehrere vordefinierte Jobs aus einer Job List
- jeder Job ist ein eigenständiger Lauf mit eigener `run_id`
- ein Job besteht mindestens aus `algorithm_name`, Zielparameter und Zielwert
- Jobs dürfen zusätzliche Metadaten wie `display_label`, Seed-Override oder freie Beschriftungen tragen
- Sweep-Ergebnisse müssen pro Job eindeutig identifizierbar und exportierbar sein

Allgemeine Regeln:
- Alle Run-Modi müssen denselben Event-Vertrag verwenden.
- Alle Run-Modi müssen von derselben GUI-Session kontrollierbar sein.
- Pause, Resume und Cancel müssen auf alle aktiven Worker der aktuellen Session wirken können.

## Compare- und Sweep-Orchestrierung

### Algorithmusvergleich
Der Compare-Modus **muss zwingend parallel arbeiten**.

Regeln:
- Standardmodus ist der parallele Algorithmusvergleich (`algo_compare`).
- Jeder zu vergleichende Algorithmus wird in einem eigenen unabhängigen Worker-Thread oder Prozess gestartet.
- Die TrainLoop-Logik muss thread-sicher sein; globale Mutationen, die andere parallele Läufe beeinflussen, sind unzulässig.
- Jeder verglichene Algorithmus muss mit eindeutigem `run_id` und `algorithm_name` verfolgt werden.
- Parameter-Isolation zwischen Algorithmen muss erhalten bleiben.
- Ein gemeinsamer Seed darf verwendet werden, sofern ein fairer Direktvergleich gewünscht ist und der Seed gesetzt ist.
- Seed-Verhalten muss im Export und in `training_done.summary_metrics` nachvollziehbar dokumentiert sein.

### Sweep-Orchestrierung
Sweep-Läufe müssen über eine explizite Job-Liste orchestrierbar sein.

Regeln:
- Jeder Sweep-Job wird aus einem serialisierbaren Konfigurationszustand oder einem deterministisch daraus ableitbaren Override-Satz erzeugt.
- Jobs dürfen algorithmusspezifische Parameter überschreiben.
- Inkompatible Overrides müssen sicher ignoriert oder nachvollziehbar gemeldet werden; stilles Fehlverhalten ist unzulässig.
- Sweep-Jobs müssen hinsichtlich Parameterzustand, Seed und Exportpfaden strikt voneinander isoliert bleiben.
- Sweep kann parallel oder kontrolliert sequentiell ausgeführt werden; das konkrete Projekt darf dies präzisieren, solange der Event-Vertrag und die Job-Isolation eingehalten werden.

## Exporte
Pflicht:
- PNG-Export nach `plots/`

Regeln:
- PNG-Dateinamen enthalten Laufparameter und Zeitstempel.
- Exportnamen und Metadaten sollen `algorithm_name`, `run_id` und wenn relevant `run_mode` nachvollziehbar abbilden.
- Bei Sweep-Läufen sollen Exportnamen zusätzlich Job-Kontext oder `display_label` nachvollziehbar enthalten.
- Exportpfade können über `training_done.export_paths` an die GUI gemeldet werden.

## Konfigurationszustände
Die Logik muss mit serialisierbaren Konfigurationszuständen kompatibel sein.

Regeln:
- Ein `config_state` muss die für Reproduktion und Wiederanwendung relevanten Parameter vollständig beschreiben.
- GUI-seitig gespeicherte Konfigurationen müssen ohne semantischen Bruch wieder in Logik-konforme Konfigurationen überführt werden können.
- Sweep-Jobs dürfen aus einem Basis-`config_state` plus Override-Satz abgeleitet werden.
- Persistierte Konfigurationszustände dürfen keine projektübergreifend standardisierten Feldnamen verfälschen.

## Logiktests
Die Logiktests sind nach Priorität in drei Kategorien gegliedert.

### Smoke-Tests (Pflicht, schnell)
- headless Trainingsschleife startet und terminiert
- `training_done` wird emittiert
- `run_episode(...)` gibt ausgeführte Schritte zurück

### Regression-Tests (Pflicht)
- Pause-/Resume-/Cancel-Übergänge und abschließende Statusmeldung
- deterministische Kadenz von Evaluations-Checkpoints
- fortlaufende Emission von Live-Metriken während eines laufenden Runs statt erst am Ende
- Emission von `training_done` auch bei Cancel
- strukturierte Emission von `error`
- korrekte Rückgabe tatsächlich ausgeführter Schritte durch `run_episode(...)`
- korrekte Event-Zuordnung über `algorithm_name` statt `policy_name`
- paralleler `algo_compare` mit sauber isolierten Läufen
- `training_done` pro Sweep-Job im `sweep_run`
- Wiederanwendung eines gespeicherten Konfigurationszustands ohne Feldverlust

### Edge-Case-Tests (empfohlen)
- sichere Behandlung algorithmusinkompatibler Overrides
- Parameter-Isolation zwischen Algorithmen im Compare
- Parameter- und Job-Isolation im Sweep
- strukturierte `error`-Emission bei Fehler in `env_build`
- Verdrahtung gemeinsamer NN-Parameter und LR-Schedule-Parameter für freigegebene NN-Algorithmen
- Verfügbarkeit von Schritt- oder Frame-basierten visuellen Updates, wenn Rendering aktiviert ist
- korrekte Ableitung von Sweep-Jobs aus Basis-Konfiguration plus Override-Satz

## Performance-Qualität und Algorithmus-Verifikation

Nach der Implementierung aller Algorithmen eines Projekts müssen folgende
Schritte durchgeführt werden:

### Performance-Optimierung
- Implementierte Algorithmen müssen nach der Erst-Implementierung auf
  Performance geprüft und mindestens eine Optimierungsrunde durchlaufen.
- Ziele: Beschleunigung der Algorithmen und Verbesserung des Lernverhaltens.
- Typische Maßnahmen: Batch-Verarbeitung, Vektorisierung, Vermeidung redundanter
  Umgebungs-Rebuilds, effizientes Replay-Buffer-Sampling.

### Algorithmus-Verifikationsprotokoll
Für jeden implementierten RL-Algorithmus ist nach Implementierung folgendes
Protokoll zu durchlaufen:

1. Ist die Implementierung des Algorithmus korrekt umgesetzt?
2. Sind die neuronalen Netze korrekt implementiert (Architektur, Aktivierungen,
   Ausgabeschicht)?
3. Sind Trainingserfolge für die Methode nachweisbar (z. B. steigender
   Moving-Average-Reward)?
4. Sind Optimierungen nötig, um einen Trainingserfolg zu erreichen oder
   zu verbessern?
5. Bietet die UI alle Parameter des Algorithmus zum Editieren an und sind
   sie mit sinnvollen Defaults vorbelegt?
6. Anpassungen aus 1.–4. vornehmen.
7. Prüfen, ob durch 6. UI-Anpassungen nötig wurden, und diese vornehmen.

Dieses Protokoll ist projektspezifisch ausführbar und muss nicht bei jedem
Programmstart wiederholt werden — nur bei Änderungen am Algorithmus.

## Test-Isolation
Verwende dieses Test-Isolations-Setup:
- lokale `pytest.ini` mit `testpaths = tests`
- isolierter Ausführungsbefehl: `python -m pytest -q --rootdir . --confcutdir . tests/...`
- optional lokaler Helfer `run_tests.py`

## Recent Critical Architecture Rules

**CRITICAL RULE: Laufzeitgrenzen (0-Semantik)**
- Die Limits `total_timesteps` und `total_episodes` aus der Config gelten als **ODER-Bedingung**. Der Lauf endet, sobald eines der Limits erreicht ist.
- Ein Wert von `0` bedeutet: Dieses Limit wird ignoriert. Wenn z. B. `total_episodes = 0`, wird rein nach Timesteps beendet.