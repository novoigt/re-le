# inverted_double_pendulum.md

version: 1.0
last_updated: 2026-05-05
compatible_with:
  workbench: "2.0"
  workbench_logic: "2.0"
  workbench_ui: "2.0"

## Project Name

`<project_name>` = "inverted_double_pendulum"

---

## Ziel und Kurzbeschreibung

Dieses Projekt implementiert einen RL-Agenten, der die Aufgabe
"Inverted Double Pendulum" in der MuJoCo-Simulationsumgebung löst.

**Lernziel:** Der Agent soll durch kontinuierliche Kraftanwendung auf einen
Wagen ein doppeltes inverses Pendel (zwei hintereinander angeordnete Stäbe)
dauerhaft im Gleichgewicht halten.

**Analyseziel:** Vergleich der Off-Policy-Algorithmen SAC, TD3 und TQC
hinsichtlich Lernstabilität, Konvergenzgeschwindigkeit und erreichtem Reward
auf `InvertedDoublePendulum-v5`.

**Projektschwerpunkte — alle drei gleichrangig:**
- Einzeltraining (`single_run`): Interaktives Training eines einzelnen
  Algorithmus mit Live-Visualisierung
- Algorithmenvergleich (`algo_compare`): Paralleler Vergleich von SAC, TD3
  und TQC unter gleichen oder individuell optimierten Bedingungen
- Hyperparameter-Tuning (`sweep_run`): Systematische Exploration von
  Parametervarianten über eine konfigurierbare Job List

**Besonderheiten:**
- Kontinuierlicher Aktionsraum (1D, [-1, 1])
- Beobachtungsraum: 9 Dimensionen (Position, sin/cos der Winkel,
  Geschwindigkeiten, Constraint Forces) — v5 reduziert von 11 auf 9
- Belohnungsstruktur: alive_bonus (max. 10) minus Distanz- und
  Geschwindigkeitsstrafe
- Reward Threshold zum "Lösen" der Umgebung: 9100.0
- Alle drei Algorithmen (SAC, TD3, TQC) sind direkt vergleichbar,
  da TQC auf SAC aufbaut und TD3 deterministisch arbeitet
- MuJoCo-basiert: erfordert `mujoco >= 2.3.3`

---

## Referenzen und externe Regeln

- Gymnasium-Dokumentation:
  https://gymnasium.farama.org/environments/mujoco/inverted_double_pendulum/
- Stable Baselines 3:
  https://stable-baselines3.readthedocs.io/
- SB3-Contrib (TQC):
  https://sb3-contrib.readthedocs.io/
- rl-baselines3-zoo (Hyperparameter-Referenz):
  https://github.com/DLR-RM/rl-baselines3-zoo

---

## Environment Definition

```python
import gymnasium as gym

env = gym.make(
    "InvertedDoublePendulum-v5",
    render_mode="rgb_array",   # wenn Animation aktiviert; sonst None
    healthy_reward=10.0,       # GUI-editierbar
    reset_noise_scale=0.1,     # GUI-editierbar
)
```

- **Environment-ID:** `InvertedDoublePendulum-v5`
- **render_mode:** `"rgb_array"` wenn Animation als Startkonfiguration
  aktiviert, sonst `None`.
  - Animation ist Startkonfiguration: Ein Wechsel von `None` → `rgb_array`
    mid-run ist nicht möglich (erfordert Env-Rebuild).
  - Wurde die Umgebung mit `render_mode="rgb_array"` gestartet, kann
    Animation mid-run jederzeit deaktiviert und wieder aktiviert werden.
    Die Logik steuert dabei ausschließlich die Frame-Emission via
    `set_animation_enabled()` — kein Rebuild der Umgebung ist erforderlich.
    Frame-Emission stoppt sofort bei Deaktivierung; bei Reaktivierung läuft
    sie ab dem nächsten verfügbaren Frame wieder an.
  - Zweck des Mid-Run-Toggles: Ressourcenschonung während intensiver
    Trainingsphasen; Aktivierung zur Inspektion des aktuellen Lernzustands.
- **Zusatzbibliotheken:** `mujoco >= 2.3.3`, `gymnasium[mujoco]`
- **Rendering:** PIL/Pillow für Frame-Konvertierung (RGB-Array → Tkinter-Image)
- **Animationsfenster:** Separates `Toplevel`-Fenster (ausgelagertes
  Animationsfenster). Öffnet automatisch beim Trainingsstart, wenn Animation
  als Startkonfiguration aktiviert ist.

---

## Environment Parameters

Alle Parameter werden beim `gymnasium.make()`-Aufruf übergeben.
Änderungen erfordern einen Neubau der Umgebung (nicht mid-run).

- `healthy_reward`
  - type: float
  - default: 10.0
  - allowed: [0.1, 100.0]
  - description: Konstanter Belohnungswert pro gesundem Zeitschritt.
    Höhere Werte betonen das Überleben stärker gegenüber den Strafterms.
  - gui_editable: true
  - gui_widget: Spinbox (step=0.5)

- `reset_noise_scale`
  - type: float
  - default: 0.1
  - allowed: [0.0, 1.0]
  - description: Skalierung der Zufallsperturbation der Startposition und
    -geschwindigkeit. Größere Werte erzeugen anspruchsvollere Starts.
  - gui_editable: true
  - gui_widget: Spinbox (step=0.01)

---

## Policies

Drei Off-Policy-Algorithmen auf Basis von Stable Baselines 3 / SB3-Contrib.
Alle drei nutzen dieselbe Netzwerkarchitektur als gemeinsamen Standard: `[256, 256]`.

- Policy: `SAC`
  - internal_name: "SAC"
  - display_label: "SAC"
  - family: neural_network
  - sb3_class: stable_baselines3.SAC
  - compare_allowed: true
  - description: Soft Actor-Critic. Maximiert Reward + Entropie (Exploration).
    Robustester Startpunkt; automatische Entropie-Regulierung via `ent_coef=auto`.
    Empfohlen für schnelle, stabile Ergebnisse ohne viel Tuning.

- Policy: `TD3`
  - internal_name: "TD3"
  - display_label: "TD3"
  - family: neural_network
  - sb3_class: stable_baselines3.TD3
  - compare_allowed: true
  - description: Twin Delayed DDPG. Deterministisch, reduziert Überschätzung
    durch zwei Critic-Netzwerke und verzögerte Policy-Updates.
    Sensitiv gegenüber learning_rate — Anpassung auf 0.0003 zwingend empfohlen.

- Policy: `TQC`
  - internal_name: "TQC"
  - display_label: "TQC"
  - family: neural_network
  - sb3_class: sb3_contrib.TQC
  - compare_allowed: true
  - description: Truncated Quantile Critics. Baut auf SAC auf, nutzt
    Verteilungskritik und Quantilstrunkatur zur Überschätzungsreduktion.
    State-of-the-Art für diese Umgebung; höhere learning_rate empfohlen.

---

## Gemeinsame Hyperparameter

Gelten für alle drei Algorithmen gleichermaßen.

- `learning_rate_schedule`
  - type: str (enum)
  - default: "constant"
  - allowed: ["constant", "linear", "inverse_time"]
  - description: Schedule für die Lernrate über den Trainingsverlauf.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Dropdown

- `gamma`
  - type: float
  - default: 0.99
  - allowed: [0.9, 0.9999]
  - description: Diskontierungsfaktor. Steuert die Gewichtung zukünftiger
    Belohnungen. 0.99 ist optimal für diese Aufgabe.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Spinbox (step=0.001)

- `tau`
  - type: float
  - default: 0.005
  - allowed: [0.001, 0.1]
  - description: Soft-Update-Koeffizient für Zielnetzwerke. Kleine Werte
    sorgen für stabile Zielnetzwerke.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Spinbox (step=0.001)

- `buffer_size`
  - type: int
  - default: 1000000
  - allowed: [10000, 2000000]
  - description: Größe des Replay Buffers. Großer Wert ist essenziell,
    um seltene, wertvolle Trajektorien zu behalten.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: false
  - gui_widget: Spinbox (step=10000)

- `batch_size`
  - type: int
  - default: 256
  - allowed: [64, 1024]
  - description: Anzahl der Stichproben pro Update-Schritt.
    256 ist robuster Standard für alle drei Algorithmen.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Spinbox (step=64)

- `learning_starts`
  - type: int
  - default: 1000
  - allowed: [100, 50000]
  - description: Anzahl Timesteps mit zufälligen Aktionen vor dem ersten
    Lernschritt (Replay Buffer initial befüllen).
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Spinbox (step=100)

- `net_arch`
  - type: str (enum)
  - default: "[256, 256]"
  - allowed: ["[64, 64]", "[128, 128]", "[256, 256]", "[400, 300]",
              "[512, 512]"]
  - description: Netzwerkarchitektur für Actor und Critic.
    [256, 256] ist der gemeinsame Standard für einen fairen Vergleich
    aller drei Algorithmen.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: true
  - gui_widget: Dropdown

- `seed`
  - type: int
  - default: 42
  - allowed: [0, 2147483647]
  - description: Zufalls-Seed für Reproduzierbarkeit.
    Wert 0 = kein Seed gesetzt (nichtdeterministisch).
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: false
  - gui_widget: Spinbox (step=1)

- `use_gpu`
  - type: bool
  - default: false
  - description: Aktiviert CUDA/MPS-Beschleunigung, wenn verfügbar.
    Startkonfiguration — nicht während eines laufenden Runs änderbar.
    Bei fehlendem Device automatischer Fallback auf CPU mit Warnung.
  - compare_benchmark_shared: true
  - compare_tuned_override_allowed: false
  - gui_widget: Checkbox

- `total_timesteps`
  - type: int
  - default: 500000
  - allowed: [0, 10000000]
  - description: Maximale Anzahl Umgebungsschritte. 0 = ignorieren.
    Training endet beim ersten erreichten Limit (ODER-Bedingung mit
    total_episodes).
  - gui_widget: Spinbox (step=10000)

- `total_episodes`
  - type: int
  - default: 0
  - allowed: [0, 100000]
  - description: Maximale Episodenanzahl. 0 = ignorieren.
    Training endet beim ersten erreichten Limit (ODER-Bedingung mit
    total_timesteps).
  - gui_widget: Spinbox (step=10)

- `eval_interval`
  - type: int
  - default: 10
  - allowed: [1, 1000]
  - description: Alle N Episoden wird eine Evaluationsphase durchgeführt.
  - gui_widget: Spinbox (step=1)

- `eval_episodes`
  - type: int
  - default: 5
  - allowed: [1, 50]
  - description: Anzahl der Episoden pro Evaluations-Checkpoint.
  - gui_widget: Spinbox (step=1)

- `moving_average_window`
  - type: int
  - default: 20
  - allowed: [5, 200]
  - description: Fenstergröße für den gleitenden Durchschnitt des Rewards
    im Live-Plot.
  - gui_widget: Spinbox (step=5)

---

## Policy-spezifische Hyperparameter

### SAC

- `learning_rate` (SAC)
  - type: float
  - default: 0.0003
  - allowed: [0.000001, 0.01]
  - description: Lernrate für Actor, Critic und Entropie-Koeffizient.
    0.0003 ist robuster Standard; hohe Sensitivität gegenüber Fehlwerten.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=0.00001)

- `ent_coef` (SAC)
  - type: str or float
  - default: "auto"
  - allowed: ["auto", "0.0", "0.1", "0.2", "0.5", "1.0"]
  - description: Entropie-Koeffizient. "auto" = automatisches Lernen des
    Werts; empfohlen für diese Umgebung.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Dropdown

---

### TD3

- `learning_rate` (TD3)
  - type: float
  - default: 0.0003
  - allowed: [0.000001, 0.01]
  - description: KRITISCH — SB3-Default (0.001) führt zu Destabilisierung.
    Zwingend auf 0.0003 reduziert. Sehr hohe Sensitivität.
    Werte > 0.001 lösen eine Warnung aus.
  - compare_override_allowed: true
  - incompatible_override_handling: log and warn
  - gui_widget: Spinbox (step=0.00001)

- `policy_delay` (TD3)
  - type: int
  - default: 2
  - allowed: [1, 10]
  - description: Frequenz der Policy-Updates (Delayed Policy Updates).
    Algorithmus-definierender Parameter — Änderung nicht empfohlen.
  - compare_override_allowed: false
  - incompatible_override_handling: reject with warning
  - gui_widget: Spinbox (step=1)

- `policy_noise` (TD3)
  - type: float
  - default: 0.15
  - allowed: [0.0, 0.5]
  - description: Ziel-Policy-Smoothing-Rauschen. 0.15 leicht reduziert
    gegenüber SB3-Default (0.2); passender für v5-Belohnungsstruktur.
    Standard 0.2 bleibt sicherer Ausgangspunkt bei Unsicherheit.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=0.01)

- `noise_clip` (TD3)
  - type: float
  - default: 0.5
  - allowed: [0.0, 1.0]
  - description: Obere Schranke für policy_noise-Clipping.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=0.05)

---

### TQC

- `learning_rate` (TQC)
  - type: float
  - default: 0.001
  - allowed: [0.000001, 0.01]
  - description: Erhöhte Lernrate (0.001) für schnelleres Lernen.
    Muss überwacht werden — Destabilisierungsgefahr bei zu hohem Wert.
    Sehr hohe Sensitivität.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=0.00001)

- `n_quantiles` (TQC)
  - type: int
  - default: 25
  - allowed: [5, 100]
  - description: Anzahl der geschätzten Quantile pro Critic-Netzwerk.
    25 ist Standard aus dem Original-Paper; Erhöhung bringt hier
    keinen klaren Vorteil.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=5)

- `n_critics` (TQC)
  - type: int
  - default: 2
  - allowed: [1, 5]
  - description: Anzahl der Critic-Netzwerke im Ensemble.
    Mehr Kritiker erhöhen die Rechenlast ohne klaren Vorteil für diese
    Umgebung.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Spinbox (step=1)

- `top_quantiles_to_drop_per_net` (TQC)
  - type: int
  - default: 2
  - allowed: [0, 5]
  - description: Anzahl verworfener höchster Quantile pro Netzwerk.
    Zentraler TQC-Mechanismus zur Überschätzungsreduktion.
    WARNUNG: Werte >= 3 können die Leistung massiv verschlechtern.
  - compare_override_allowed: true
  - incompatible_override_handling: log and warn
  - gui_widget: Spinbox (step=1)

- `ent_coef` (TQC)
  - type: str or float
  - default: "auto"
  - allowed: ["auto", "0.0", "0.1", "0.2", "0.5", "1.0"]
  - description: Entropie-Koeffizient (geerbt von SAC-Basis).
    "auto" empfohlen.
  - compare_override_allowed: true
  - incompatible_override_handling: log and ignore
  - gui_widget: Dropdown

---

## Compare-Vorgaben

- compare_enabled: true

- supported_compare_modes:
  - benchmark_mode: Alle Algorithmen mit denselben gemeinsamen
    Hyperparametern; nur algorithmus-spezifische Parameter differieren.
    Dient dem fairen, kontrollierten Vergleich.
  - tuned_mode: Jeder Algorithmus mit seinen individuell optimierten
    Defaults (SAC: lr=0.0003, TD3: lr=0.0003, TQC: lr=0.001).
    Dient dem praxisnahen Leistungsvergleich.

- default_compare_mode: "tuned_mode"

- default_compare_selection: ["SAC", "TD3", "TQC"]
  (alle drei vorausgewählt; Nutzer kann einzeln deaktivieren)

- shared_seed_supported: true
  Gemeinsamer Seed für fairen Direktvergleich empfohlen; default: 42.
  Bei seed=0 im Compare-Modus: Hinweis ausgeben
  ("Kein Seed gesetzt — Vergleichbarkeit eingeschränkt").

- compare_metrics:
  - primary: episode_reward (Moving Average)
  - secondary: best_reward, total_steps_to_threshold
  - threshold_reward: 9100.0 (Reward Threshold v5)
  - note: "training_done.summary_metrics muss seed, algorithm_name
           und run_mode enthalten."

- animation_in_compare_mode:
  - Nur für einen Algorithmus gleichzeitig aktiv, um visuelles
    Flackern und konkurrierende Render-Updates zu verhindern.
  - Standard: erster alphabetisch aktiver Algorithmus.
  - GUI darf einen Selector anbieten, um den angezeigten Algorithmus
    zu wechseln.
  - Mid-Run-Toggle (Frame-Emission ein/aus) gilt auch im Compare-Modus.

- run_mode_note: >
    Alle drei Run-Modi (single_run, algo_compare, sweep_run) sind
    gleichrangige Projektschwerpunkte. Kein Modus ist Nebenfunktion.
    Die Implementierung muss alle drei Modi vollständig und stabil
    unterstützen.

---

## GUI-Ausnahmen und projektspezifische Controls

### Gruppenbezeichnung: "Algorithms" statt "Methods"
Die GUI-Gruppe `Methods / Specific` aus workbench_ui.md wird in
diesem Projekt durchgängig als **`Algorithms`** bezeichnet.
Die Semantik (algorithmusspezifische Parameter, ttk.Notebook mit
einem Tab pro Algorithmus) bleibt unverändert.
Diese Umbenennung gilt konsistent für alle Beschriftungen in GUI,
Dokumentation und Tests.

---

### Gruppe: Environment
- `healthy_reward` — Spinbox, default 10.0, step 0.5
- `reset_noise_scale` — Spinbox, default 0.1, step 0.01
- `Animation aktivieren` — Checkbox (Startkonfiguration;
  deaktiviert während laufendem Run für den rgb_array/None-Wechsel)
- `Frame interval (ms)` — Spinbox, default 10, nur aktiv wenn Animation an

### Gruppe: Training / General
- `total_timesteps` — Spinbox, default 500000, step 10000
- `total_episodes` — Spinbox, default 0, step 10
- Hinweis-Label: "Training endet beim ersten erreichten Limit; 0 = ignorieren"
- `eval_interval` — Spinbox, default 10, step 1
- `eval_episodes` — Spinbox, default 5, step 1
- `moving_average_window` — Spinbox, default 20, step 5
- `seed` — Spinbox, default 42, step 1
- `use_gpu` — Checkbox, default false
  (deaktiviert während laufendem Run)

### Gruppe: Presets / Common Parameters
- `gamma` — Spinbox, default 0.99, step 0.001
- `tau` — Spinbox, default 0.005, step 0.001
- `buffer_size` — Spinbox, default 1000000, step 10000
- `batch_size` — Spinbox, default 256, step 64
- `learning_starts` — Spinbox, default 1000, step 100
- `net_arch` — Dropdown, default "[256, 256]"
- `learning_rate_schedule` — Dropdown, default "constant"

### Gruppe: Algorithms (projektspezifisch umbenannt)
- ttk.Notebook mit drei Tabs: **SAC** | **TD3** | **TQC**
- Tab SAC:
  - `learning_rate` — Spinbox, default 0.0003, step 0.00001
  - `ent_coef` — Dropdown, default "auto"
- Tab TD3:
  - `learning_rate` — Spinbox, default 0.0003, step 0.00001
  - `policy_delay` — Spinbox, default 2, step 1
  - `policy_noise` — Spinbox, default 0.15, step 0.01
  - `noise_clip` — Spinbox, default 0.5, step 0.05
- Tab TQC:
  - `learning_rate` — Spinbox, default 0.001, step 0.00001
  - `n_quantiles` — Spinbox, default 25, step 5
  - `n_critics` — Spinbox, default 2, step 1
  - `top_quantiles_to_drop_per_net` — Spinbox, default 2, step 1
  - `ent_coef` — Dropdown, default "auto"

### Gruppe: Parameter Tuning / Job List
- Standard-Sweep-Controls gemäß workbench_ui.md
- Algorithmus-Selector: ["SAC", "TD3", "TQC"]
- Sweep-Parameter: alle policy-spezifischen + gemeinsamen Parameter

### Projektspezifische Plot-Erweiterungen
- **Reward-Threshold-Linie:** Horizontale gestrichelte Linie bei y=9100.0.
  Farbe: `#f57c00` (Orange), Alpha 0.7, Linienbreite 1.5,
  Label: "Solved (9100)".
  Immer sichtbar, solange der Plot aktiv ist.
- **Solved-Hinweis:** Wenn der Moving Average erstmals 9100.0 überschreitet,
  zeigt der Current-Run-Bereich: "✓ Solved! Episode {n}".

---

## Logik-Ausnahmen

### Animation Mid-Run Toggle
Wurde die Umgebung mit `render_mode="rgb_array"` gestartet, kann
`set_animation_enabled(enabled: bool)` mid-run aufgerufen werden:
- `False`: Frame-Emission stoppt sofort; kein Env-Rebuild erforderlich.
  Frei gewordene Ressourcen stehen dem Trainingsdurchlauf zur Verfügung.
- `True`: Frame-Emission wird ab dem nächsten verfügbaren Frame wieder
  aufgenommen; aktueller Lernzustand wird sofort sichtbar.
Zweck: Ressourcenschonung bei intensiven Trainingsphasen; Sichtprüfung
des Lernzustands bei Bedarf.

### Reward-Interpretation
Die Belohnung setzt sich zusammen aus:
  `reward = alive_bonus - distance_penalty - velocity_penalty`
Das `info`-Dict enthält `reward_survive`, `distance_penalty`,
`velocity_penalty` als Einzelterme. Diese werden optional in
`episode_aux.diagnostics` transportiert (nicht im schnellen
episode-Pfad).

### Episode-Ende
Eine Episode endet durch:
- Termination: y-Koordinate der Pendelspitze <= 1 (Sturz)
- Truncation: 1000 Schritte erreicht
Beide Fälle werden korrekt verarbeitet (`terminated or truncated`).

### SB3-Trainingsintegration
Das Training läuft über `model.learn(total_timesteps=..., callback=...)`.
Ein Custom-Callback übernimmt die Funktion des generischen TrainLoop-
Event-Emitters und emittiert `episode`- und `episode_aux`-Events in
die Queue. `training_done` wird nach `model.learn()` oder bei Cancel
emittiert.

### Modell-Checkpoints
SB3-Modelle werden nach erfolgreichem Abschluss eines Runs unter
`models/` gespeichert:
- Namensschema: `{algorithm_name}_{run_id}_{timestamp}.zip`
- Nur bei `completion_reason = "finished"` oder "early_stop";
  nicht bei "cancel_requested" oder "error".

---

## Validierungsregeln

- `total_timesteps = 0` AND `total_episodes = 0`:
  → Fehler, Training sperren:
  "Mindestens ein Trainingslimit muss > 0 sein."

- `learning_rate` (TD3) > 0.001:
  → Warnung ausgeben:
  "TD3: Lernrate > 0.001 kann zu Instabilität führen."

- `top_quantiles_to_drop_per_net` (TQC) >= 3:
  → Warnung ausgeben:
  "TQC: top_quantiles_to_drop_per_net >= 3 kann die Leistung stark
  verschlechtern."

- `batch_size` > `buffer_size` / 10:
  → Warnung ausgeben:
  "Batch-Größe ist relativ zum Buffer sehr groß — mögliche
  Überanpassung an frühe Erfahrungen."

- `seed = 0` im Compare-Modus:
  → Hinweis ausgeben:
  "Kein Seed gesetzt — Vergleichbarkeit zwischen Algorithmen
  eingeschränkt."

- `use_gpu = true` ohne verfügbarem CUDA/MPS-Device:
  → Automatisch auf CPU zurückfallen, Warnung ausgeben:
  "GPU nicht verfügbar — Training läuft auf CPU."

- `policy_delay` (TD3) wird als Sweep-Override übergeben:
  → Ablehnen mit Warnung:
  "policy_delay ist ein algorithmisch-definierender Parameter und
  kann nicht per Sweep überschrieben werden."

---

## Projekt-Ausgaben und besondere Exporte

### Pflichtordner (für dieses Projekt)
- `plots/` — PNG-Exporte des Live-Reward-Plots
- `configs/` — JSON-Konfigurationszustände (Save/Load Config)
- `models/` — SB3-Modell-Checkpoints (.zip) nach abgeschlossenen Runs

### Optionaler CSV-Export (projektspezifisch aktiviert)
- Pfad: `results_csv/{algorithm_name}_{run_id}_{timestamp}.csv`
- Ordner `results_csv/` wird bei Bedarf angelegt
- Inhalt pro Zeile (Episode):
  - episode, reward, moving_average, best_reward, total_steps,
    eval_mean_reward, eval_std_reward
- Optionale Diagnosespalten (wenn in episode_aux.diagnostics vorhanden):
  - reward_survive, distance_penalty, velocity_penalty

### Plot-Export
- Pfad: `plots/{algorithm_name}_{run_id}_{timestamp}.png`
- Enthält denselben Light-Mode-Plot wie der Live-Plot
- Inklusive Reward-Threshold-Linie (y=9100.0)

---

## Projektspezifisches Farbschema: Light Mode

**Abweichung von workbench_ui.md:** Dieses Projekt verwendet ein
Light-Theme für den Live-Plot und alle PNG-Exporte anstelle des in
workbench_ui.md definierten Dark-Themes. Das Light-Theme ist
verbindlich für dieses Projekt.

### Hintergrund und Achsen
- Figure-Hintergrund: `#ffffff`
- Axes-Hintergrund: `#ffffff`
- Tick-Farben: `#333333`
- Achsen-Labels (X und Y): `#333333`
- Grid: Farbe `#cccccc`, gestrichelt, Alpha 0.5

### Linien-Darstellung
| Algorithmus | Raw-Linie (Alpha 0.3, LW 1.0) | Moving Average (Alpha 1.0, LW 2.5) |
|-------------|-------------------------------|--------------------------------------|
| SAC (1.)    | `#1a73e8` (Blau)             | `#1a73e8`                            |
| TD3 (2.)    | `#e53935` (Rot)              | `#e53935`                            |
| TQC (3.)    | `#2e7d32` (Grün)             | `#2e7d32`                            |
| Weitere     | `#6a1b9a` (Violett)          | `#6a1b9a`                            |

### Reward-Threshold-Linie
- Farbe: `#f57c00` (Orange), gestrichelt, Alpha 0.7, LW 1.5
- Label: "Solved (9100)"

### Legende
- Facecolor: `#ffffff`
- Edgecolor: `#cccccc`
- Labelcolor: `#333333`
- Inhalt: algorithm_name oder display_label; bei Sweep zusätzlich
  Parameter-Name und Wert

### Regeln
- PNG-Exporte verwenden dasselbe Light-Theme wie der Live-Plot
- Das Farbschema darf projektspezifisch um weitere Farben erweitert,
  aber nicht durch ein abweichendes Theme ersetzt werden

---

## Projekthinweise

- **MuJoCo-Abhängigkeit:** `pip install gymnasium[mujoco]` erforderlich.
  Ohne gültige MuJoCo-Installation schlägt `env_build` fehl.
  Die Logik emittiert in diesem Fall `error_stage: env_build` und
  anschließend `training_done` mit `status: failed`.

- **TQC-Abhängigkeit:** `pip install sb3-contrib` erforderlich.
  Fehlt das Paket, muss beim Programmstart ein benutzerfreundlicher
  Fehler ausgegeben werden (nicht erst beim Trainingsstart).

- **Reward Threshold:** 9100.0 (v5-Standard). Im Plot als horizontale
  Linie visualisiert. Wird in summary_metrics und CSV-Export vermerkt.

- **Beobachtungsraum:** 9-dimensional (v5, reduziert von 11 in v4).
  Kein Normalisierungs-Wrapper notwendig — SB3 normalisiert intern
  bei Bedarf.

- **Performance-Erwartungen** (Richtwerte, hardwareabhängig):
  - SAC:  ca. 200.000 Timesteps bis Threshold
  - TQC:  ca. 150.000 Timesteps (State-of-the-Art)
  - TD3:  ca. 300.000 Timesteps (mit lr=0.0003)

- **Pflichteinträge requirements.txt:**
  ```
  gymnasium[mujoco]
  stable-baselines3>=2.0.0
  sb3-contrib>=2.0.0
  torch>=2.0.0
  numpy
  matplotlib
  pillow
  pytest
  ```

---

## Pflichtschema-Zusammenfassung

Alle Pflichtabschnitte gemäß workbench.md sind enthalten:

- [x] Project Name
- [x] Ziel und Kurzbeschreibung
- [x] Referenzen und externe Regeln
- [x] Environment Definition
- [x] Environment Parameters
- [x] Policies
- [x] Gemeinsame Hyperparameter
- [x] Policy-spezifische Hyperparameter
- [x] Compare-Vorgaben
- [x] GUI-Ausnahmen und projektspezifische Controls
- [x] Logik-Ausnahmen
- [x] Validierungsregeln
- [x] Projekt-Ausgaben oder besondere Exporte
- [x] Projekthinweise
