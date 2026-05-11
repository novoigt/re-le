# inverted_double_pendulum_REQUIREMENTS_MATRIX.md

**Projekt:** inverted_double_pendulum  
**Version:** 1.0.0  
**Datum:** 2026-05-05  
**Workbench-Version:** 2.0  

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Vollständig implementiert und testbar |
| ⚠️ | Teilweise implementiert — bekannte Einschränkung dokumentiert |
| ❌ | Offen — noch nicht implementiert |

**Zieldatei-Kürzel:**

| Kürzel | Datei |
|--------|-------|
| `LOGIC` | `inverted_double_pendulum_logic.py` |
| `UI` | `inverted_double_pendulum_ui.py` |
| `APP` | `inverted_double_pendulum_app.py` |
| `T-LOGIC` | `tests/test_inverted_double_pendulum_logic.py` |
| `T-GUI` | `tests/test_inverted_double_pendulum_gui.py` |

---

## Abschnitt 1: Anforderungen aus `workbench.md`

| # | Anforderung | Quelle | Zieldatei(en) | Status | Anmerkung |
|---|-------------|--------|---------------|--------|-----------|
| 1.01 | Ausgabedatei `<project_name>_app.py` vorhanden | `workbench.md` | `APP` | ✅ | |
| 1.02 | Ausgabedatei `<project_name>_logic.py` vorhanden | `workbench.md` | `LOGIC` | ✅ | |
| 1.03 | Ausgabedatei `<project_name>_ui.py` vorhanden | `workbench.md` | `UI` | ✅ | |
| 1.04 | Ausgabedatei `<project_name>_REQUIREMENTS_MATRIX.md` vorhanden | `workbench.md` | diese Datei | ✅ | |
| 1.05 | Ausgabedatei `tests/test_<project_name>_logic.py` vorhanden | `workbench.md` | `T-LOGIC` | ✅ | |
| 1.06 | Ausgabedatei `tests/test_<project_name>_gui.py` vorhanden | `workbench.md` | `T-GUI` | ✅ | |
| 1.07 | Ausgabedatei `requirements.txt` vorhanden | `workbench.md` | `requirements.txt` | ⚠️ | Wird als nächste Datei erstellt |
| 1.08 | Ausgabedatei `README.md` vorhanden | `workbench.md` | `README.md` | ⚠️ | Wird als nächste Datei erstellt |
| 1.09 | Ausgabeordner `plots/` angelegt | `workbench.md` | `APP`, `LOGIC` | ✅ | `ensure_project_dirs()` + `ExportHelper` |
| 1.10 | Ausgabeordner `configs/` angelegt | `workbench.md` | `APP`, `LOGIC` | ✅ | `ensure_project_dirs()` + `ConfigState` |
| 1.11 | Ausgabeordner `models/` angelegt | `workbench.md` | `APP`, `LOGIC` | ✅ | `ensure_project_dirs()` + `ExportHelper` |
| 1.12 | Dateinamen exakt und konsistent nach `<project_name>` | `workbench.md` | alle | ✅ | `project_name = "inverted_double_pendulum"` durchgängig |
| 1.13 | `<project_name>` aus Dateiname der projektspezifischen Datei (snake_case) | `workbench.md` | alle | ✅ | Abgeleitet aus `inverted_double_pendulum.md` |
| 1.14 | Einheitlich `algorithm_name` statt `policy_name` | `workbench.md` | `LOGIC`, `UI`, `T-LOGIC`, `T-GUI` | ✅ | Keine `policy_name`-Verwendung im Projekt |
| 1.15 | Seeds explizit unterstützt | `workbench.md` | `LOGIC`, `UI` | ✅ | `seed`-Parameter in Config und GUI |
| 1.16 | Konfigurationsdateien nur unter `configs/` gespeichert | `workbench.md` | `LOGIC`, `UI` | ✅ | `ConfigState.CONFIG_DIR = "configs"` |
| 1.17 | Plots nur unter `plots/` gespeichert | `workbench.md` | `LOGIC`, `UI` | ✅ | `ExportHelper.PLOTS_DIR = "plots"` |
| 1.18 | Modell-Checkpoints nur unter `models/` gespeichert | `workbench.md` | `LOGIC` | ✅ | `ExportHelper.MODELS_DIR = "models"` |
| 1.19 | Vollständiger, lauffähiger Code (keine TODO-Platzhalter) | `workbench.md` | alle | ✅ | |
| 1.20 | Klare Trennung zwischen Logik und GUI | `workbench.md` | `LOGIC`, `UI` | ✅ | Keine GUI-Importe in `LOGIC` |
| 1.21 | Tests für Logik und GUI vorhanden | `workbench.md` | `T-LOGIC`, `T-GUI` | ✅ | 15 Logik- + 26 GUI-Tests |
| 1.22 | Serialisierbare Konfigurationszustände | `workbench.md` | `LOGIC`, `UI` | ✅ | `ConfigState.to_dict()` / `from_dict()` |
| 1.23 | Strukturierte Exporte nach `results_csv/` und `plots/` | `workbench.md` | `LOGIC` | ✅ | `ExportHelper.export_csv()`, `export_plot_data()` |
| 1.24 | GUI-blockierendes Training verboten | `workbench.md` | `LOGIC`, `UI` | ✅ | Training in Hintergrund-Thread, Event-Pump via `after()` |
| 1.25 | Fehlender Abschlusszustand nach Cancel/Fehler verboten | `workbench.md` | `LOGIC` | ✅ | `training_done` immer emittiert (finally-Block) |
| 1.26 | Stille Behandlung inkompatibler Overrides verboten | `workbench.md` | `LOGIC` | ✅ | `error`-Event mit `recoverable=True` bei inkompatiblem Override |

---

## Abschnitt 2: Anforderungen aus `workbench_logic.md`

| # | Anforderung | Quelle | Zieldatei(en) | Status | Anmerkung |
|---|-------------|--------|---------------|--------|-----------|
| 2.01 | Klare Trennung: EnvironmentWrapper / Agent / TrainLoop / Orchestrator | `workbench_logic.md` | `LOGIC` | ✅ | 8 Sections, je klar abgegrenzte Klasse |
| 2.02 | EnvironmentWrapper kapselt `gymnasium.make()` | `workbench_logic.md` | `LOGIC` | ✅ | `EnvironmentWrapper.build()` |
| 2.03 | Neubau der Umgebung bei geänderten Parametern | `workbench_logic.md` | `LOGIC` | ✅ | `EnvironmentWrapper.rebuild()` |
| 2.04 | `render_mode` konfigurierbar (`rgb_array` oder `None`) | `workbench_logic.md` | `LOGIC` | ✅ | Aus `animation_enabled` abgeleitet beim Build |
| 2.05 | `set_animation_enabled()` thread-sicher, kein Rebuild mid-run | `workbench_logic.md` | `LOGIC` | ✅ | `threading.Event._animation_enabled` |
| 2.06 | Animation mid-run: nur Frame-Emission unterdrückt | `workbench_logic.md` | `LOGIC` | ✅ | `render()` gibt `None` zurück wenn Flag nicht gesetzt |
| 2.07 | Wechsel von `None` → `rgb_array` mid-run nicht unterstützt | `workbench_logic.md` | `LOGIC` | ✅ | Dokumentiert in Logik-Ausnahmen |
| 2.08 | SB3 als RL-Bibliothek, PyTorch als Backend | `workbench_logic.md` | `LOGIC` | ✅ | SAC, TD3, TQC via SB3 / sb3-contrib |
| 2.09 | Keras und TensorFlow nicht zulässig | `workbench_logic.md` | `LOGIC` | ✅ | Nicht importiert |
| 2.10 | Dynamische Hardware-Beschleunigung (CPU/CUDA/MPS) | `workbench_logic.md` | `LOGIC` | ✅ | `get_device(use_gpu)` mit Fallback auf CPU |
| 2.11 | Trainingsdaten als `float32` | `workbench_logic.md` | `LOGIC` | ✅ | Mock-Env und SB3-interne Verarbeitung |
| 2.12 | Netzarchitektur `[256, 256]` einheitlich für SAC/TD3/TQC | `workbench_logic.md` | `LOGIC` | ✅ | `NET_ARCH_MAP`, `policy_kwargs` |
| 2.13 | `TrainLoop`-Ebene orchestriert Episodenstart, Steps, Stop | `workbench_logic.md` | `LOGIC` | ✅ | `TrainingCallback` als SB3-`BaseCallback` |
| 2.14 | Laufzeitgrenzen `total_timesteps` ODER `total_episodes` | `workbench_logic.md` | `LOGIC` | ✅ | `_check_limits()` im Callback; `0` = ignorieren |
| 2.15 | Stop/Pause/Resume/Cancel thread-sicher | `workbench_logic.md` | `LOGIC` | ✅ | `threading.Event` Polling in `_on_step()` |
| 2.16 | `run_episode()` gibt tatsächlich ausgeführte Steps zurück | `workbench_logic.md` | `LOGIC` | ✅ | Rückgabe `int steps` |
| 2.17 | `train()` headless und GUI-gekoppelt nutzbar | `workbench_logic.md` | `LOGIC` | ✅ | Kein GUI-Import in `LOGIC` |
| 2.18 | `evaluate_policy()` gibt mean, std, n zurück | `workbench_logic.md` | `LOGIC` | ✅ | Separates eval_env, unabhängig vom Haupttraining |
| 2.19 | `evaluate_policy()` blockiert nicht das Haupttraining | `workbench_logic.md` | `LOGIC` | ✅ | Eigenes eval_env, deterministisch |
| 2.20 | Trainer eindeutig über `run_id` und `algorithm_name` | `workbench_logic.md` | `LOGIC` | ✅ | `uuid4()` pro Lauf |
| 2.21 | Gemeinsame Pflichtfelder in jedem Event vorhanden | `workbench_logic.md` | `LOGIC` | ✅ | `build_event()` sichert: type, session_id, run_id, timestamp, source, status, algorithm_name |
| 2.22 | `session_id` GUI-seitig vergeben | `workbench_logic.md` | `UI` | ✅ | `IDPApp._session_id = uuid4()` bei Start |
| 2.23 | `episode`-Event als primäres UI-Event | `workbench_logic.md` | `LOGIC` | ✅ | Alle Pflichtfelder vorhanden |
| 2.24 | `episode_aux` für schwere Payloads (Frames, eval_points) | `workbench_logic.md` | `LOGIC` | ✅ | Frames und Eval-Checkpoints via `episode_aux` |
| 2.25 | `training_done` immer emittiert (auch bei Cancel/Fehler) | `workbench_logic.md` | `LOGIC` | ✅ | `finally`-Block in `IDPTrainer.train()` |
| 2.26 | `training_done` Pflichtfelder vollständig | `workbench_logic.md` | `LOGIC` | ✅ | completion_reason, episodes_completed, episodes_planned, run_mode |
| 2.27 | `error`-Event mit Pflichtfeldern | `workbench_logic.md` | `LOGIC` | ✅ | error_code, error_message, error_stage |
| 2.28 | `error_stage` standardisierte Werte | `workbench_logic.md` | `LOGIC` | ✅ | env_build, config, train_loop, evaluate, export |
| 2.29 | `training_done` nach `error` mit `status=failed` | `workbench_logic.md` | `LOGIC` | ✅ | `_emit_error()` + `_emit_training_done("error")` |
| 2.30 | Drei getrennte Update-Takte: Metrik / Frame / Eval | `workbench_logic.md` | `LOGIC` | ✅ | Episode-Takt, Frame-Throttle (50ms), Eval-Checkpoint-Kadenz |
| 2.31 | Live-Animation wird gedrosselt (throttled) | `workbench_logic.md` | `LOGIC` | ✅ | `FRAME_THROTTLE_INTERVAL = 0.05s` im Callback |
| 2.32 | Statusübergänge deterministisch | `workbench_logic.md` | `LOGIC` | ✅ | idle→running→paused→running→completed/cancelled/failed |
| 2.33 | Fehlgeschlagener Build → `idle`-Zustand danach | `workbench_logic.md` | `LOGIC` | ✅ | `_emit_training_done("error")` + Env-Close in `finally` |
| 2.34 | `single_run`: genau ein Algorithmus, eine `run_id` | `workbench_logic.md` | `LOGIC` | ✅ | `Orchestrator.run_single()` |
| 2.35 | `algo_compare`: zwingend parallel, je eigener Thread | `workbench_logic.md` | `LOGIC` | ✅ | `Orchestrator.run_compare()` mit je einem `threading.Thread` |
| 2.36 | `algo_compare`: Parameter-Isolation zwischen Algorithmen | `workbench_logic.md` | `LOGIC` | ✅ | Separate Config-Dicts, kein gemeinsamer Zustand |
| 2.37 | `sweep_run`: explizite Job-Liste, je eigene `run_id` | `workbench_logic.md` | `LOGIC` | ✅ | `Orchestrator.run_sweep()` |
| 2.38 | Sweep: Jobs aus Base-Config + Override-Satz | `workbench_logic.md` | `LOGIC` | ✅ | `dict(base_config)` + Override mit Typ-Erhaltung |
| 2.39 | Sweep: inkompatible Overrides sicher gemeldet | `workbench_logic.md` | `LOGIC` | ✅ | `error`-Event, `recoverable=True`, Job wird übersprungen |
| 2.40 | `training_done` pro Sweep-Job separat emittiert | `workbench_logic.md` | `LOGIC` | ✅ | Je `IDPTrainer`-Instanz pro Job |
| 2.41 | `job_index` / `job_count` in `training_done` bei Sweep | `workbench_logic.md` | `LOGIC` | ✅ | `IDPTrainer.__init__` empfängt und weitergibt |
| 2.42 | PNG-Export nach `plots/` | `workbench_logic.md` | `LOGIC` | ✅ | `ExportHelper.export_plot_data()` mit Light-Theme |
| 2.43 | Exportnamen enthalten `algorithm_name`, `run_id`, Timestamp | `workbench_logic.md` | `LOGIC` | ✅ | Dateinamen-Schema in `ExportHelper` |
| 2.44 | `config_state` vollständig serialisierbar | `workbench_logic.md` | `LOGIC` | ✅ | `ConfigState.to_dict()` / `from_dict()` / `save()` / `load()` |
| 2.45 | Sweep-Jobs aus Base-`config_state` + Override ableitbar | `workbench_logic.md` | `LOGIC` | ✅ | `Orchestrator.run_sweep()` |
| 2.46 | Smoke-Tests: headless Loop startet/terminiert | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestSmoke.test_headless_train_starts_and_terminates` |
| 2.47 | Smoke-Tests: `training_done` wird emittiert | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestSmoke.test_training_done_always_emitted_on_cancel` |
| 2.48 | Smoke-Tests: `run_episode()` gibt Steps zurück | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestSmoke.test_run_episode_returns_steps` |
| 2.49 | Regression: Pause/Resume/Cancel-Übergänge | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_pause_resume_cycle` |
| 2.50 | Regression: `training_done` bei Cancel | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_cancel_emits_training_done_with_cancelled_status` |
| 2.51 | Regression: Live-Metriken während Run, nicht erst am Ende | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_episode_events_emitted_before_training_done` |
| 2.52 | Regression: `error`-Event bei `env_build`-Fehler | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_error_event_on_env_build_failure` |
| 2.53 | Regression: Compare mit isolierten `run_id`s | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_algo_compare_isolated_run_ids` |
| 2.54 | Regression: `training_done` pro Sweep-Job | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_sweep_training_done_per_job` |
| 2.55 | Regression: Config-State Roundtrip ohne Feldverlust | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestRegression.test_config_state_save_load_roundtrip` |
| 2.56 | Edge: Inkompatibler Override gemeldet | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestEdgeCases.test_incompatible_sweep_override_reported` |
| 2.57 | Edge: Parameter-Isolation Compare | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestEdgeCases.test_algo_compare_parameter_isolation` |
| 2.58 | Edge: Animation-Toggle mid-run, kein Rebuild | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestEdgeCases.test_animation_toggle_mid_run_no_rebuild` |
| 2.59 | Edge: Sweep-Job von Base-Config abgeleitet | `workbench_logic.md` | `T-LOGIC` | ✅ | `TestEdgeCases.test_sweep_job_derived_from_base_config` |
| 2.60 | Performance-Optimierungsrunde nach Erst-Implementierung | `workbench_logic.md` | `LOGIC` | ⚠️ | Vorgesehen nach Algorithmus-Verifikationsprotokoll |
| 2.61 | Algorithmus-Verifikationsprotokoll durchgeführt | `workbench_logic.md` | `LOGIC` | ⚠️ | Nach lokaler Ausführung durch Nutzer durchzuführen |

---

## Abschnitt 3: Anforderungen aus `workbench_ui.md`

| # | Anforderung | Quelle | Zieldatei(en) | Status | Anmerkung |
|---|-------------|--------|---------------|--------|-----------|
| 3.01 | Zentrale GUI-Klasse mit allen Hauptpanels | `workbench_ui.md` | `UI` | ✅ | `IDPApp(tk.Tk)` |
| 3.02 | Verschiebbare Trennbalken (`ttk.PanedWindow`) | `workbench_ui.md` | `UI` | ✅ | Vertikales Haupt-PanedWindow + horizontales oberes PanedWindow |
| 3.03 | Startgewichte: Oben=6, Mitte=1, Unten=3 | `workbench_ui.md` | `UI` | ✅ | `weight=6/1/3` im vertikalen PanedWindow |
| 3.04 | Parameter-Panel scrollbar + Mausrad | `workbench_ui.md` | `UI` | ✅ | Canvas + Scrollbar + `<MouseWheel>` / `<Button-4/5>` |
| 3.05 | Gruppe Environment (row=0, col=0) | `workbench_ui.md` | `UI` | ✅ | `_build_group_environment()` |
| 3.06 | Gruppe Training / General (row=1, col=0) | `workbench_ui.md` | `UI` | ✅ | `_build_group_training()` |
| 3.07 | Gruppe Presets / Common Parameters (row=0, col=1, rowspan=2) | `workbench_ui.md` | `UI` | ✅ | `_build_group_presets()` |
| 3.08 | Gruppe Algorithms (row=2, col=0) — projektspezifisch "Algorithms" statt "Methods" | `workbench_ui.md` / `inverted_double_pendulum.md` | `UI` | ✅ | `_build_group_algorithms()` mit `ttk.Notebook` |
| 3.09 | Gruppe Parameter Tuning / Job List (row=2, col=1) | `workbench_ui.md` | `UI` | ✅ | `_build_group_sweep()` |
| 3.10 | Checkbox für Bool-Werte | `workbench_ui.md` | `UI` | ✅ | Animation, use_gpu |
| 3.11 | Spinbox für numerische Werte | `workbench_ui.md` | `UI` | ✅ | Alle numerischen Parameter |
| 3.12 | Dropdown für diskrete Optionen | `workbench_ui.md` | `UI` | ✅ | net_arch, lr_schedule, ent_coef, Algorithmus-Selektor |
| 3.13 | LR-Schedule-Dropdown: constant, linear, inverse_time | `workbench_ui.md` | `UI` | ✅ | `_build_group_presets()` |
| 3.14 | Run-Modi: Single, Compare, Sweep per RadioButton | `workbench_ui.md` | `UI` | ✅ | `_run_mode_var` in Control Bar |
| 3.15 | Compare: alle ausgewählten Algorithmen parallel | `workbench_ui.md` | `UI` | ✅ | `_start_compare()` → `Orchestrator.run_compare()` |
| 3.16 | Compare: Plot farblich getrennt mit Legende | `workbench_ui.md` | `UI` | ✅ | `ALGO_COLORS`, je `run_id` eigene Linien |
| 3.17 | Sweep: Jobs aus Job List, je eigener Lauf | `workbench_ui.md` | `UI` | ✅ | `_start_sweep()` → `Orchestrator.run_sweep()` |
| 3.18 | Event-Pump: `after()`-Polling, max. Batch-Größe | `workbench_ui.md` | `UI` | ✅ | `PUMP_BATCH_SIZE = 20`, `PUMP_INTERVAL_MS = 50` |
| 3.19 | Event-Pump verarbeitet Events mehrerer paralleler Worker | `workbench_ui.md` | `UI` | ✅ | Session-Filter + run_id-Zuordnung |
| 3.20 | Session-Filterung veralteter Events | `workbench_ui.md` | `UI` | ✅ | `event.get("session_id") != self._session_id` → verwerfen |
| 3.21 | Plot-Aktualisierung throttled | `workbench_ui.md` | `UI` | ✅ | `PLOT_REDRAW_INTERVAL_MS = 200` |
| 3.22 | Live-Plot fortlaufend während des Runs aktualisiert | `workbench_ui.md` | `UI` | ✅ | Inkrementelle `set_data()` pro Episode-Event |
| 3.23 | `training_done` setzt GUI in deterministischen Abschlusszustand | `workbench_ui.md` | `UI` | ✅ | `_handle_training_done()` |
| 3.24 | `error`-Event wird strukturiert verarbeitet | `workbench_ui.md` | `UI` | ✅ | `_handle_error()` mit `messagebox.showerror()` |
| 3.25 | Animationsfenster als separates Toplevel | `workbench_ui.md` | `UI` | ✅ | `AnimationWindow(tk.Toplevel)` |
| 3.26 | Initialzustand: alle Defaults vorausgefüllt | `workbench_ui.md` | `UI` | ✅ | `_set_initial_state()` + alle `tk.Variable`-Defaults |
| 3.27 | Initialzustand: Start aktiv, Pause/Resume/Cancel deaktiviert | `workbench_ui.md` | `UI` | ✅ | `_set_initial_state()` → `_update_button_states("idle")` |
| 3.28 | Initialzustand: Status zeigt `idle` | `workbench_ui.md` | `UI` | ✅ | `_var_status.set("idle")` |
| 3.29 | Config Save/Load über Dateidialog | `workbench_ui.md` | `UI` | ✅ | `_on_save_config()` / `_on_load_config()` |
| 3.30 | GUI-Test: Smoke — App startet ohne Fehler | `workbench_ui.md` | `T-GUI` | ✅ | `TestSmoke.test_app_starts_without_error` |
| 3.31 | GUI-Test: Button-Initialzustand korrekt | `workbench_ui.md` | `T-GUI` | ✅ | `TestSmoke.test_initial_button_states` |
| 3.32 | GUI-Test: Status-Feld `idle` im Initialzustand | `workbench_ui.md` | `T-GUI` | ✅ | `TestSmoke.test_initial_status_field_is_idle` |
| 3.33 | GUI-Test: Alle Algo-Tabs vorhanden | `workbench_ui.md` | `T-GUI` | ✅ | `TestParameterPanel.test_all_algorithm_tabs_present` |
| 3.34 | GUI-Test: Default-Werte korrekt | `workbench_ui.md` | `T-GUI` | ✅ | `TestParameterPanel.test_default_values_match_spec` |
| 3.35 | GUI-Test: `_collect_config_state()` vollständig | `workbench_ui.md` | `T-GUI` | ✅ | `TestParameterPanel.test_collect_config_state_complete` |
| 3.36 | GUI-Test: Config-Roundtrip | `workbench_ui.md` | `T-GUI` | ✅ | `TestParameterPanel.test_apply_config_state_roundtrip` |
| 3.37 | GUI-Test: Button-Zustände je UI-State | `workbench_ui.md` | `T-GUI` | ✅ | `TestButtonStates` (4 Tests) |
| 3.38 | GUI-Test: Event-Pump verarbeitet Episode-Events korrekt | `workbench_ui.md` | `T-GUI` | ✅ | `TestEventPump.test_episode_event_updates_status_fields` |
| 3.39 | GUI-Test: Session-Filter | `workbench_ui.md` | `T-GUI` | ✅ | `TestEventPump.test_session_filter_rejects_stale_events` |
| 3.40 | GUI-Test: Mehrere run_ids im Compare | `workbench_ui.md` | `T-GUI` | ✅ | `TestEventPump.test_multiple_run_ids_in_compare_mode` |
| 3.41 | GUI-Test: Display-Guard für CI | `workbench_ui.md` | `T-GUI` | ✅ | `pytestmark = pytest.mark.skip` ohne DISPLAY |

---

## Abschnitt 4: Anforderungen aus `inverted_double_pendulum.md`

| # | Anforderung | Quelle | Zieldatei(en) | Status | Anmerkung |
|---|-------------|--------|---------------|--------|-----------|
| 4.01 | Environment: `gymnasium.make("InvertedDoublePendulum-v5")` | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `ENV_ID = "InvertedDoublePendulum-v5"` |
| 4.02 | render_mode `rgb_array` oder `None` je Animation-Zustand | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `EnvironmentWrapper.build()` |
| 4.03 | `healthy_reward` editierbar (default 10.0) | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Config-Parameter + Spinbox in GUI |
| 4.04 | `reset_noise_scale` editierbar (default 0.1) | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Config-Parameter + Spinbox in GUI |
| 4.05 | Algorithmus SAC implementiert | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `IDPTrainer.build_model()` mit SB3-SAC |
| 4.06 | Algorithmus TD3 implementiert | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `IDPTrainer.build_model()` mit SB3-TD3 |
| 4.07 | Algorithmus TQC implementiert | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `IDPTrainer.build_model()` mit sb3-contrib-TQC |
| 4.08 | SAC Default learning_rate=0.0003 | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Config-Default + GUI-Spinbox |
| 4.09 | TD3 Default learning_rate=0.0003 (reduziert von SB3-Standard) | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Projektspezifisch aus Hyperparameter-Guide |
| 4.10 | TQC Default learning_rate=0.001 (erhöht von SB3-Standard) | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Projektspezifisch aus Hyperparameter-Guide |
| 4.11 | TD3 Default policy_noise=0.15 (reduziert von 0.2) | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | Projektspezifisch aus Hyperparameter-Guide |
| 4.12 | Einheitliche Netzarchitektur `[256, 256]` für alle Algorithmen | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | `NET_ARCH_MAP`, GUI-Dropdown |
| 4.13 | `ent_coef=auto` als Default für SAC und TQC | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | GUI-Dropdown mit `auto` als erstem Wert |
| 4.14 | Compare-Modus aktiviert für alle drei Algorithmen | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | `run_compare()` mit SAC, TD3, TQC |
| 4.15 | Compare und Single gleichrangige Projektschwerpunkte | `inverted_double_pendulum.md` | `UI` | ✅ | RadioButtons gleichwertig, kein Default auf Single erzwungen |
| 4.16 | Reward Threshold = 9100.0 | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | `REWARD_THRESHOLD = 9100.0`, Threshold-Linie im Plot |
| 4.17 | Solved-Ankündigung bei Erreichen des Thresholds | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `_solved_announced` Flag + `message`-Feld im Episode-Event |
| 4.18 | Animation mid-run toggle ohne Env-Rebuild | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | `set_animation_enabled()` delegiert an `EnvironmentWrapper` |
| 4.19 | Animationsfenster als separates Toplevel-Fenster | `inverted_double_pendulum.md` | `UI` | ✅ | `AnimationWindow(tk.Toplevel)` |
| 4.20 | GUI-Ausnahme: Gruppenbezeichnung "Algorithms" (nicht "Methods") | `inverted_double_pendulum.md` | `UI` | ✅ | `ttk.LabelFrame(text="Algorithms")` |
| 4.21 | GUI-Ausnahme: `ttk.Notebook` mit Tabs SAC/TD3/TQC | `inverted_double_pendulum.md` | `UI` | ✅ | `_algo_notebook` |
| 4.22 | Projektspezifisches Light-Mode-Farbschema | `inverted_double_pendulum.md` | `LOGIC`, `UI` | ✅ | `THEME`-Dict in `UI`, Light-Theme in `ExportHelper.export_plot_data()` |
| 4.23 | Plot-Hintergrund `#ffffff`, Achsen `#333333`, Grid `#cccccc` | `inverted_double_pendulum.md` | `UI`, `LOGIC` | ✅ | `THEME`-Konstanten in `UI`; identisch in `ExportHelper` |
| 4.24 | Threshold-Linie Farbe `#f57c00` | `inverted_double_pendulum.md` | `UI`, `LOGIC` | ✅ | `THEME["threshold"] = "#f57c00"` |
| 4.25 | Algorithmusfarben: SAC=#1a73e8, TD3=#e53935, TQC=#2e7d32 | `inverted_double_pendulum.md` | `UI` | ✅ | `ALGO_COLORS[0..2]` |
| 4.26 | Validierungsregel: TD3 lr > 0.001 → WARNING | `inverted_double_pendulum.md` | `LOGIC`, `T-LOGIC` | ✅ | `validate_config()` + `TestEdgeCases.test_validate_config_errors_and_warnings` |
| 4.27 | Validierungsregel: TQC top_q_drop >= 3 → WARNING | `inverted_double_pendulum.md` | `LOGIC`, `T-LOGIC` | ✅ | `validate_config()` + Test |
| 4.28 | Validierungsregel: beide Limits = 0 → ERROR | `inverted_double_pendulum.md` | `LOGIC`, `T-LOGIC` | ✅ | `validate_config()` + Test |
| 4.29 | CSV-Export nach `results_csv/` | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `ExportHelper.export_csv()` |
| 4.30 | Modell-Export nach `models/` | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `ExportHelper.export_model()` |
| 4.31 | `summary_metrics` in `training_done` enthält `solved`-Flag | `inverted_double_pendulum.md` | `LOGIC` | ✅ | `solved: best >= REWARD_THRESHOLD` |
| 4.32 | `episode_aux` Felder `diagnostics` projektspezifisch deklariert | `inverted_double_pendulum.md` | `LOGIC` | ✅ | reward_survive, distance_penalty, velocity_penalty |

---

## Abschnitt 5: Zusammenfassung

| Kategorie | Gesamt | ✅ Vollständig | ⚠️ Teilweise | ❌ Offen |
|-----------|--------|---------------|--------------|---------|
| `workbench.md` (1.xx) | 26 | 24 | 2 | 0 |
| `workbench_logic.md` (2.xx) | 61 | 59 | 2 | 0 |
| `workbench_ui.md` (3.xx) | 41 | 41 | 0 | 0 |
| `inverted_double_pendulum.md` (4.xx) | 32 | 32 | 0 | 0 |
| **Gesamt** | **160** | **156** | **4** | **0** |

### Offene Punkte (⚠️ teilweise)

| # | Anforderung | Grund | Nächster Schritt |
|---|-------------|-------|-----------------|
| 1.07 | `requirements.txt` | Noch nicht erstellt | Als nächste Datei erzeugen |
| 1.08 | `README.md` | Noch nicht erstellt | Als nächste Datei erzeugen |
| 2.60 | Performance-Optimierungsrunde | Erfordert lokale Trainingsläufe | Nach Algorithmus-Verifikation durch Nutzer |
| 2.61 | Algorithmus-Verifikationsprotokoll | Erfordert echte MuJoCo-Ausführung | Lokal durch Nutzer nach Erstinstallation |
