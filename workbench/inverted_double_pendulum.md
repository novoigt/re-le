# <project_name>.md

## Project Name
`<project_name>` = "inverted_double_pendulum"

## Ziel und Kurzbeschreibung
Beschreibe kurz:
- welches RL-Projekt erstellt werden soll
- welches Lernziel, Analyseziel oder Demonstrationsziel das Projekt hat
- welche Besonderheiten das Projekt fachlich von anderen Projekten unterscheiden

## Referenzen und externe Regeln
https://gymnasium.farama.org/environments/mujoco/inverted_double_pendulum/

Beispiele:
- offizielle Gymnasium-Dokumentation des Environments
- papers, falls fachlich nötig
- zusätzliche bibliotheksbezogene Regeln

## Environment Definition
Definiere das Ziel-Environment eindeutig.

Pflichtangaben:
- Environment-Name in `gymnasium.make("InvertedDoublePendulum-v5")`
- relevante Initialisierungsargumente
- gewünschter `render_mode`, falls benötigt
- zusätzliche Bibliotheken oder Rendering-Anforderungen, falls erforderlich

Beispielstruktur:
- `gymnasium.make("<env-id>", render_mode="...")`
- zusätzliche Rendering- oder Anzeigeanforderungen

## Environment Parameters
Liste alle projektspezifisch editierbaren Environment-Parameter auf.

Für jeden Parameter angeben:
- Name
- Typ
- Defaultwert
- zulässige Werte oder Wertebereich
- kurze Bedeutung
- ob er in der GUI editierbar sein muss

Empfohlene Struktur:
- `<parameter_name>`
  - type:
  - default:
  - allowed:
  - description:
  - gui_editable:

## Policies
Liste alle für das Projekt bereitzustellenden Policies auf.

Für jede Policy angeben:
- Anzeigename
- interner Name, falls notwendig
- Policy-Klasse oder Verfahrenstyp
- ob sie im Compare-Modus zugelassen ist
- kurze Beschreibung

Beispiel:
- Policy: `Q-Learning`
  - internal_name:
  - family: `tabular`
  - compare_allowed: `true`
  - description:

## Gemeinsame Hyperparameter
Liste alle projektweit relevanten gemeinsamen Hyperparameter auf.

Für jeden Hyperparameter angeben:
- Name
- Typ
- Defaultwert
- zulässiger Wertebereich oder diskrete Werte
- Beschreibung
- ob im Compare-`benchmark_mode` gemeinsam verwendet werden soll
- ob im Compare-`tuned_mode` überschrieben werden darf
- GUI-Darstellungstyp

Beispiel:
- `gamma`
  - type:
  - default:
  - allowed:
  - description:
  - compare_benchmark_shared:
  - compare_tuned_override_allowed:
  - gui_widget:

## Policy-spezifische Hyperparameter
Liste pro Policy die speziellen Hyperparameter auf, die nicht für alle Policies gelten.

Für jeden Parameter angeben:
- Policy-Name
- Parametername
- Typ
- Defaultwert
- zulässige Werte
- Beschreibung
- ob Compare-Override erlaubt ist
- wie inkompatible Overrides behandelt werden sollen
- GUI-Darstellungstyp

Regel:
- Inkompatible Overrides müssen sicher ignoriert oder nachvollziehbar gemeldet werden.

## Compare-Vorgaben
Definiere projektspezifische Regeln für Compare.

Pflichtangaben:
- welche Policies verglichen werden dürfen
- ob `benchmark_mode` unterstützt wird
- ob `tuned_mode` unterstützt wird
- ob gemeinsame Seeds verwendet werden sollen oder optional sind
- welche Metriken im Compare besonders relevant sind

Empfohlene Felder:
- compare_enabled:
- supported_compare_modes:
- default_compare_mode:
- shared_seed_supported:
- compare_metrics:

## GUI-Ausnahmen und projektspezifische Controls
Beschreibe alle projektspezifischen GUI-Erweiterungen.

Für jedes Element angeben:
- zugehörige Pflichtgruppe aus `workbench_ui.md`
- Control-Typ
- Zweck
- betroffene Parameter oder Zustände
- spezielle Validierungsregeln

Regeln:
- keine freie Platzierung außerhalb der definierten GUI-Gruppen
- Standard-Controls werden nicht ersetzt, sondern ergänzt

## Logik-Ausnahmen
Beschreibe projektspezifische Abweichungen oder Erweiterungen der generischen Logik.

Beispiele:
- besondere Reward-Interpretation
- spezielle Evaluationslogik
- abweichende Episode-Ende-Regeln
- projektbezogene Exportzusätze

Regel:
- Diese Ausnahmen dürfen globale Architektur- oder Event-Verträge nicht brechen.

## Validierungsregeln
Definiere projektspezifische Validierungsregeln.

Mögliche Inhalte:
- zulässige Parameterkombinationen
- unzulässige Kombinationen
- projektspezifische Plausibilitätsgrenzen
- Pflichtfelder für bestimmte Policies
- spezielle Compare-Einschränkungen

## Projekt-Ausgaben oder besondere Exporte
Definiere zusätzliche projektspezifische Ausgaben, falls notwendig.

Beispiele:
- zusätzliche CSV-Dateien
- besondere Plot-Typen
- gespeicherte Rollouts
- projektspezifische Diagnosedateien

## Projekthinweise
Freier Bereich für wichtige Hinweise, die sich keiner anderen Kategorie sauber zuordnen lassen.

## Pflichtschema-Zusammenfassung
Jede projektspezifische Datei muss mindestens enthalten:
- `Project Name`
- `Ziel und Kurzbeschreibung`
- `Referenzen und externe Regeln`
- `Environment Definition`
- `Environment Parameters`
- `Policies`
- `Gemeinsame Hyperparameter`
- `Policy-spezifische Hyperparameter`
- `Compare-Vorgaben`
- `GUI-Ausnahmen und projektspezifische Controls`
- `Logik-Ausnahmen`
- `Validierungsregeln`
- `Projekt-Ausgaben oder besondere Exporte`
- `Projekthinweise`
