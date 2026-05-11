# Inverted Double Pendulum — RL Workbench

Eine grafische Reinforcement-Learning-Workbench für das Environment
`InvertedDoublePendulum-v5` (MuJoCo / Gymnasium). Die Anwendung unterstützt
die Algorithmen **SAC**, **TD3** und **TQC** und ermöglicht Einzel-,
Vergleichs- und Sweep-Läufe mit Live-Plot, Animation und konfigurierbaren
Hyperparametern — alles über eine Tkinter-GUI ohne Kommandozeilen-Kenntnisse.

---

## Inhaltsverzeichnis

1. [Environment](#2-environment)
2. [Unterstützte Algorithmen](#3-unterstützte-algorithmen)
3. [Voraussetzungen & Installation](#4-voraussetzungen--installation)
4. [Starten](#5-starten)
5. [Run-Modi](#6-run-modi)
6. [Wichtige Parameter](#7-wichtige-parameter)
7. [Konfiguration speichern & laden](#8-konfiguration-speichern--laden)
8. [Exporte](#9-exporte)
9. [Tests](#10-tests)
10. [Projektstruktur](#11-projektstruktur)

---

## 2. Environment

| Eigenschaft | Wert |
|---|---|
| Gymnasium-ID | `InvertedDoublePendulum-v5` |
| Observation Space | `Box(9,)` — Gelenkwinkel, Winkelgeschwindigkeiten, Kontaktkräfte |
| Action Space | `Box(1,)` — kontinuierliche Kraft auf den Schiebewagen |
| Reward Threshold | **9100.0** (Gymnasium-Solved-Kriterium) |
| Max. Episode Steps | 1000 (Gymnasium-Default) |
| Physik-Backend | MuJoCo (via `mujoco` Python-Paket) |

Das Environment simuliert einen doppelten Pendulumarm auf einem Schiebewagen.
Ziel ist es, beide Arme durch kontinuierliche Kraftanwendung aufrecht zu halten.
Der Agent erhält pro Zeitschritt eine Belohnung, die aus Überlebensbonus,
Vorwärtsbewegung und Strafabzügen für extreme Auslenkungen besteht.

---

## 3. Unterstützte Algorithmen

| Algorithmus | Bibliothek | Default LR | Besonderheit |
|---|---|---|---|
| **SAC** (Soft Actor-Critic) | `stable-baselines3` | 0.0003 | Entropie-Regularisierung, `ent_coef=auto` |
| **TD3** (Twin Delayed DDPG) | `stable-baselines3` | 0.0003 | Reduziertes `policy_noise=0.15` (projektspezifisch) |
| **TQC** (Truncated Quantile Critics) | `sb3-contrib` | 0.001 | Quantil-basierte Kritik, `top_quantiles_to_drop=2` |

Alle Algorithmen verwenden eine einheitliche Netzarchitektur `[256, 256]`
und unterstützen GPU-Beschleunigung via CUDA oder MPS.

---

## 4. Voraussetzungen & Installation

### Systemanforderungen

- Python **≥ 3.10**
- MuJoCo (wird automatisch via `gymnasium[mujoco]` installiert)
- Tkinter (in CPython-Standard-Distributionen enthalten)
- Optional: NVIDIA-GPU mit CUDA ≥ 12.1 für beschleunigtes Training

### Installation (CPU)

```bash
# 1. Repository klonen oder Projektordner entpacken
cd inverted_double_pendulum

# 2. Virtuelle Umgebung anlegen (empfohlen)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate.bat     # Windows

# 3. Abhängigkeiten installieren
pip install -r requirements.txt
```

### Installation (GPU — CUDA 12.1)

```bash
pip install -r requirements.txt
pip install torch>=2.2.0 --index-url https://download.pytorch.org/whl/cu121
```

### MuJoCo-Hinweis

`gymnasium[mujoco]` installiert das `mujoco` Python-Paket automatisch.
Auf Linux können zusätzliche System-Abhängigkeiten nötig sein:

```bash
sudo apt install -y libgl1 libglfw3 libglew-dev
```

---

## 5. Starten

### GUI-Modus (Standard)

```bash
python inverted_double_pendulum_app.py
```

### Mit gespeicherter Konfiguration laden

```bash
python inverted_double_pendulum_app.py --config configs/meine_config.json
```

### Headless-Modus (CI / Tests)

```bash
python inverted_double_pendulum_app.py --headless
python inverted_double_pendulum_app.py --headless --log-level DEBUG
```

### Alle CLI-Optionen

| Flag | Default | Beschreibung |
|---|---|---|
| `--headless` | `False` | Startet ohne GUI; führt Smoke-Run durch |
| `--log-level` | `INFO` | Log-Level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--config PATH` | — | Pfad zu einer JSON-Konfigurationsdatei |
| `--version` | — | Gibt Versionsnummer aus und beendet |

Logs werden geschrieben nach `logs/inverted_double_pendulum.log`.

---

## 6. Run-Modi

### Single Run
Trainiert genau einen ausgewählten Algorithmus (SAC, TD3 oder TQC) mit den
aktuell eingestellten Hyperparametern. Der Fortschritt wird live im Plot
dargestellt. Start über den **Run**-RadioButton + **Start**-Schaltfläche.

### Compare
Startet alle aktivierten Algorithmen **parallel** als separate Hintergrund-Threads.
Der Live-Plot zeigt die Reward-Kurven aller Algorithmen farblich getrennt
(SAC blau, TD3 rot, TQC grün) mit Legende. Jeder Algorithmus erhält eine
eigene `run_id`, sodass Fortschritt und Abschluss klar zugeordnet werden können.
Start über den **Compare**-RadioButton + **Start**-Schaltfläche.

### Sweep
Führt eine benutzerdefinierte Liste von Trainings-Jobs sequenziell aus.
Jeder Job ist eine Konfigurationsvariante (Algorithmus + ein überschriebener
Parameter + Wert). Jobs werden über das **Parameter Tuning / Job List**-Panel
zusammengestellt. Jeder Job erhält eine eigene `run_id` und ein separates
`training_done`-Event. Start über den **Sweep**-RadioButton + **Start**-Schaltfläche.

**Job hinzufügen:**
1. Algorithmus aus Dropdown wählen (`SAC`, `TD3`, `TQC`)
2. Parameter eingeben (z. B. `learning_rate`)
3. Wert eingeben (z. B. `0.001`)
4. **Add Job** klicken

---

## 7. Wichtige Parameter

### Environment-Parameter

| Parameter | Default | Beschreibung |
|---|---|---|
| `healthy_reward` | 10.0 | Belohnung pro Überlebens-Schritt |
| `reset_noise_scale` | 0.1 | Zufallsrauschen beim Reset der Gelenkpositionen |

### Training / General

| Parameter | Default | Beschreibung |
|---|---|---|
| `total_timesteps` | 500 000 | Maximale Trainings-Schritte (`0` = kein Limit) |
| `total_episodes` | 0 | Maximale Episoden (`0` = kein Limit) |
| `eval_interval` | 10 | Episoden zwischen Evaluierungen |
| `eval_episodes` | 5 | Episoden pro Evaluierung |
| `moving_average_window` | 50 | Fenstergröße für gleitenden Mittelwert |
| `seed` | 42 | Zufallsseed für Reproduzierbarkeit |
| `use_gpu` | False | GPU-Beschleunigung aktivieren |

### Gemeinsame Hyperparameter (Presets / Common)

| Parameter | Default | Beschreibung |
|---|---|---|
| `gamma` | 0.99 | Discount-Faktor |
| `tau` | 0.005 | Soft-Update-Rate für Ziel-Netzwerk |
| `batch_size` | 256 | Batch-Größe für Netz-Updates |
| `buffer_size` | 1 000 000 | Replay-Buffer-Kapazität |
| `learning_starts` | 10 000 | Steps vor erstem Netz-Update |
| `net_arch` | `[256, 256]` | Netzarchitektur (beide Schichten) |
| `lr_schedule` | `constant` | Lernraten-Schedule: `constant`, `linear`, `inverse_time` |

### Algorithmusspezifische Parameter

**SAC:**

| Parameter | Default | Beschreibung |
|---|---|---|
| `learning_rate` | 0.0003 | Lernrate |
| `ent_coef` | `auto` | Entropie-Koeffizient |

**TD3:**

| Parameter | Default | Beschreibung |
|---|---|---|
| `learning_rate` | 0.0003 | Lernrate |
| `policy_delay` | 2 | Policy-Update-Verzögerung |
| `policy_noise` | 0.15 | Zielrauschen (projektspezifisch reduziert) |
| `noise_clip` | 0.5 | Clipping des Zielrauschens |

**TQC:**

| Parameter | Default | Beschreibung |
|---|---|---|
| `learning_rate` | 0.001 | Lernrate (projektspezifisch erhöht) |
| `ent_coef` | `auto` | Entropie-Koeffizient |
| `top_quantiles_to_drop` | 2 | Anzahl verworfener oberer Quantile pro Netz |
| `n_quantiles` | 25 | Quantile pro Kritiker-Kopf |
| `n_critics` | 5 | Anzahl Kritiker-Köpfe |

---

## 8. Konfiguration speichern & laden

Alle GUI-Einstellungen können als JSON gespeichert und später wiederhergestellt
werden. Konfigurationsdateien liegen ausschließlich unter `configs/`.

### Über die GUI

- **Save Config** — öffnet Dateidialog; speichert aktuelle Einstellungen als JSON
- **Load Config** — öffnet Dateidialog; lädt und übernimmt alle Einstellungen

### Über CLI

```bash
python inverted_double_pendulum_app.py --config configs/meine_config.json
```

Die Konfiguration wird beim GUI-Start automatisch geladen.

### Format

```json
{
  "project": "inverted_double_pendulum",
  "version": "1.0.0",
  "saved_at": "2026-05-05T20:00:00",
  "config": {
    "algorithm_name": "SAC",
    "gamma": 0.99,
    "learning_rate": 0.0003,
    ...
  }
}
```

---

## 9. Exporte

Alle Exporte liegen in definierten Projektordnern — keine freien externen Pfade.

| Export | Ordner | Format | Inhalt |
|---|---|---|---|
| Plot (PNG) | `plots/` | `.png` | Reward-Kurven mit Threshold-Linie, Light-Theme |
| Metriken (CSV) | `results_csv/` | `.csv` | Episode, Reward, MA, Steps, Algorithmus, run_id |
| Modell | `models/` | `.zip` | SB3-Modell-Checkpoint (ladbar via `model.load()`) |

Exportdateinamen tragen `algorithm_name`, `run_id` (Kurzform) und Timestamp:

```
plots/SAC_a1b2c3d4_20260505_200000.png
results_csv/SAC_a1b2c3d4_20260505_200000.csv
models/SAC_a1b2c3d4_20260505_200000.zip
```

Export-Schaltfläche **Export Plot** ist in der GUI-Toolbar verfügbar,
sobald Plotdaten vorhanden sind.

---

## 10. Tests

### Ausführung

```bash
# Alle Tests
python -m pytest -q --rootdir . --confcutdir . tests/

# Nur Logik-Tests (kein Display erforderlich)
python -m pytest -q tests/test_inverted_double_pendulum_logic.py

# Nur GUI-Tests (Display erforderlich)
python -m pytest -q tests/test_inverted_double_pendulum_gui.py

# Mit Timeout-Schutz
python -m pytest -q --timeout=60 tests/
```

### Testumfang

| Datei | Tests | Kategorie |
|---|---|---|
| `test_inverted_double_pendulum_logic.py` | 15 | Smoke, Regression, Edge Cases |
| `test_inverted_double_pendulum_gui.py` | 26 | Smoke, Panel, Buttons, Event-Pump, Plot, Config, Jobs, Validierung |

### Display-Guard

GUI-Tests erkennen automatisch ob ein Display verfügbar ist (`DISPLAY` /
`WAYLAND_DISPLAY` unter Linux). Ohne Display werden alle GUI-Tests mit
`pytest.mark.skip` übersprungen — CI-Pipelines ohne Display-Emulation
führen nur die Logik-Tests aus. Mit Xvfb laufen auch GUI-Tests in CI:

```bash
xvfb-run python -m pytest -q tests/
```

### Mock-Strategie

Logik-Tests mocken `gymnasium.make()` und SB3-Modelle vollständig —
kein echtes MuJoCo oder GPU nötig. Alle 15 Tests laufen in unter 10 Sekunden.

---

## 11. Projektstruktur

```
inverted_double_pendulum/
│
├── inverted_double_pendulum_app.py          # Einstiegspunkt, Bootstrap, CLI
├── inverted_double_pendulum_logic.py        # RL-Logik, Trainer, Orchestrator
├── inverted_double_pendulum_ui.py           # Tkinter-GUI
├── inverted_double_pendulum_REQUIREMENTS_MATRIX.md
├── requirements.txt
├── README.md
│
├── tests/
│   ├── test_inverted_double_pendulum_logic.py
│   └── test_inverted_double_pendulum_gui.py
│
├── configs/                                 # JSON-Konfigurationsdateien
├── plots/                                   # PNG-Exporte
├── models/                                  # SB3-Modell-Checkpoints (.zip)
├── results_csv/                             # CSV-Metriken-Exporte
└── logs/                                    # Log-Dateien
```

---

*Projektversion: 1.0.0 — Workbench v2.0*
