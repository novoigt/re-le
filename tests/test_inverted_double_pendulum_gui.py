"""
tests/test_inverted_double_pendulum_gui.py
GUI-Tests für inverted_double_pendulum_ui.py
Workbench v2.0 — Smoke, Panel, Buttons, Event-Pump, Plot, Config, Jobs, Validierung

Ausführung:
    python -m pytest -q --rootdir . --confcutdir . tests/

Voraussetzung: Display verfügbar (lokal oder Xvfb in CI).
Ohne Display werden alle Tests automatisch übersprungen.
"""

# =============================================================================
# SECTION 1: Imports & Display-Guard
# =============================================================================

from __future__ import annotations

import json
import os
import queue
import sys
import time
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Projektroot erreichbar machen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Display-Guard: CI-safe — überspringt alle Tests wenn kein Display verfügbar
tkinter = pytest.importorskip("tkinter")

_has_display = (
    sys.platform == "win32"
    or sys.platform == "darwin"
    or bool(os.environ.get("DISPLAY"))
    or bool(os.environ.get("WAYLAND_DISPLAY"))
)
if not _has_display:
    pytestmark = pytest.mark.skip(reason="Kein Display verfügbar (DISPLAY/WAYLAND_DISPLAY nicht gesetzt)")

import tkinter as tk
from tkinter import ttk

from inverted_double_pendulum_logic import REWARD_THRESHOLD, ConfigState
from inverted_double_pendulum_ui import IDPApp, AnimationWindow, SUPPORTED_ALGORITHMS


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def _pump(app: IDPApp, n: int = 5) -> None:
    """Verarbeitet ausstehende after()-Callbacks und GUI-Events."""
    for _ in range(n):
        app.update_idletasks()
        app.update()


def _make_episode_event(
    session_id: str,
    run_id: str,
    episode: int = 1,
    reward: float = 5.0,
    moving_average: float = 4.5,
    best_reward: float = 6.0,
    steps: int = 100,
    total_steps: int = 100,
    algorithm_name: str = "SAC",
    display_label: str = "SAC",
    run_mode: str = "single_run",
) -> Dict[str, Any]:
    return {
        "type": "episode",
        "session_id": session_id,
        "run_id": run_id,
        "timestamp": "2026-01-01T00:00:00",
        "source": "inverted_double_pendulum_logic",
        "status": "running",
        "algorithm_name": algorithm_name,
        "display_label": display_label,
        "run_mode": run_mode,
        "episode": episode,
        "episodes": 0,
        "reward": reward,
        "moving_average": moving_average,
        "best_reward": best_reward,
        "steps": steps,
        "total_steps": total_steps,
        "lr": 0.0003,
        "seed": 42,
    }


def _make_training_done_event(
    session_id: str,
    run_id: str,
    completion_reason: str = "finished",
    algorithm_name: str = "SAC",
) -> Dict[str, Any]:
    return {
        "type": "training_done",
        "session_id": session_id,
        "run_id": run_id,
        "timestamp": "2026-01-01T00:00:00",
        "source": "inverted_double_pendulum_logic",
        "status": "completed" if completion_reason == "finished" else "cancelled",
        "algorithm_name": algorithm_name,
        "display_label": algorithm_name,
        "run_mode": "single_run",
        "completion_reason": completion_reason,
        "episodes_completed": 10,
        "episodes_planned": 0,
        "best_reward": 7.5,
        "moving_average_final": 6.8,
        "total_steps_completed": 1000,
        "export_paths": {},
        "summary_metrics": {},
    }


def _make_error_event(
    session_id: str,
    run_id: str,
    stage: str = "train_loop",
) -> Dict[str, Any]:
    return {
        "type": "error",
        "session_id": session_id,
        "run_id": run_id,
        "timestamp": "2026-01-01T00:00:00",
        "source": "inverted_double_pendulum_logic",
        "status": "failed",
        "algorithm_name": "SAC",
        "display_label": "SAC",
        "run_mode": "single_run",
        "error_code": "RuntimeError",
        "error_message": "Testfehler",
        "error_stage": stage,
        "recoverable": False,
    }


# =============================================================================
# SECTION 2: Fixtures
# =============================================================================

@pytest.fixture
def app():
    """
    Erstellt eine IDPApp-Instanz ohne mainloop().
    Dependency-Check und nach() werden via update() manuell gepumpt.
    Teardown: destroy() + plt.close().
    """
    with patch("inverted_double_pendulum_ui.IDPApp._check_dependencies",
               return_value=None):
        instance = IDPApp()
    _pump(instance, 3)
    yield instance
    try:
        import matplotlib.pyplot as plt
        plt.close("all")
        instance.destroy()
    except Exception:
        pass


@pytest.fixture
def mock_orchestrator(app):
    """Ersetzt den Orchestrator der App durch einen MagicMock."""
    mock = MagicMock()
    mock.has_active_trainers.return_value = False
    app._orchestrator = mock
    return mock


# =============================================================================
# SECTION 3: Smoke-Tests
# =============================================================================

class TestSmoke:

    def test_app_starts_without_error(self, app):
        """IDPApp instanziiert ohne Exception; Hauptfenster existiert."""
        assert app.winfo_exists(), "Hauptfenster muss existieren"

    def test_initial_button_states(self, app):
        """Initialzustand: Start/Reset NORMAL, Pause/Resume/Cancel DISABLED."""
        _pump(app)
        assert str(app._btn_start["state"]) == "normal",             "Start muss im Initialzustand NORMAL sein"
        assert str(app._btn_pause["state"]) == "disabled",             "Pause muss im Initialzustand DISABLED sein"
        assert str(app._btn_resume["state"]) == "disabled",             "Resume muss im Initialzustand DISABLED sein"
        assert str(app._btn_cancel["state"]) == "disabled",             "Cancel muss im Initialzustand DISABLED sein"
        assert str(app._btn_reset["state"]) == "normal",             "Reset muss im Initialzustand NORMAL sein"
        assert str(app._btn_export["state"]) == "disabled",             "Export Plot muss im Initialzustand DISABLED sein"

    def test_initial_status_field_is_idle(self, app):
        """Status-Feld zeigt 'idle'; Progressbar ist auf 0."""
        _pump(app)
        assert app._var_status.get() == "idle",             f"Status muss 'idle' sein, ist: {app._var_status.get()}"
        assert float(app._progressbar["value"]) == 0.0,             f"Progressbar muss 0 sein, ist: {app._progressbar['value']}"


# =============================================================================
# SECTION 4: Parameter-Panel-Tests
# =============================================================================

class TestParameterPanel:

    def test_all_algorithm_tabs_present(self, app):
        """Notebook enthält genau die Tabs SAC, TD3, TQC."""
        _pump(app)
        tab_texts = [
            app._algo_notebook.tab(i, "text")
            for i in range(app._algo_notebook.index("end"))
        ]
        for algo in SUPPORTED_ALGORITHMS:
            assert algo in tab_texts,                 f"Tab '{algo}' fehlt im Notebook. Vorhandene Tabs: {tab_texts}"

    def test_default_values_match_spec(self, app):
        """Alle Default-Werte müssen der Spec entsprechen."""
        _pump(app)
        assert app._var_gamma.get() == pytest.approx(0.99),             f"gamma Default muss 0.99 sein, ist: {app._var_gamma.get()}"
        assert app._var_tau.get() == pytest.approx(0.005),             f"tau Default muss 0.005 sein, ist: {app._var_tau.get()}"
        assert app._var_batch_size.get() == 256,             f"batch_size Default muss 256 sein, ist: {app._var_batch_size.get()}"
        assert app._var_sac_lr.get() == pytest.approx(0.0003),             f"SAC lr Default muss 0.0003 sein, ist: {app._var_sac_lr.get()}"
        assert app._var_td3_lr.get() == pytest.approx(0.0003),             f"TD3 lr Default muss 0.0003 sein, ist: {app._var_td3_lr.get()}"
        assert app._var_tqc_lr.get() == pytest.approx(0.001),             f"TQC lr Default muss 0.001 sein, ist: {app._var_tqc_lr.get()}"
        assert app._var_total_timesteps.get() == 500_000,             f"total_timesteps Default muss 500000 sein, ist: {app._var_total_timesteps.get()}"
        assert app._var_seed.get() == 42,             f"seed Default muss 42 sein, ist: {app._var_seed.get()}"

    def test_collect_config_state_complete(self, app):
        """_collect_config_state() liefert Dict mit allen Pflichtfeldern."""
        _pump(app)
        state = app._collect_config_state()
        required_fields = [
            "algorithm_name", "gamma", "tau", "batch_size",
            "buffer_size", "learning_starts", "seed", "use_gpu",
            "total_timesteps", "total_episodes",
            "net_arch", "learning_rate_schedule",
            "sac_learning_rate", "td3_learning_rate", "tqc_learning_rate",
            "animation_enabled", "run_mode",
        ]
        for field in required_fields:
            assert field in state,                 f"Pflichtfeld '{field}' fehlt in _collect_config_state()"

    def test_apply_config_state_roundtrip(self, app):
        """_collect_config_state() → _apply_config_state() → identische Werte."""
        _pump(app)
        # Werte verändern
        app._var_gamma.set(0.95)
        app._var_seed.set(123)
        app._var_batch_size.set(128)
        app._var_sac_lr.set(0.0001)

        state = app._collect_config_state()
        # Werte zurücksetzen
        app._var_gamma.set(0.99)
        app._var_seed.set(42)

        # Wiederherstellen
        app._apply_config_state(state)
        _pump(app)

        assert app._var_gamma.get() == pytest.approx(0.95),             "gamma muss nach Roundtrip 0.95 sein"
        assert app._var_seed.get() == 123,             "seed muss nach Roundtrip 123 sein"
        assert app._var_batch_size.get() == 128,             "batch_size muss nach Roundtrip 128 sein"
        assert app._var_sac_lr.get() == pytest.approx(0.0001),             "SAC lr muss nach Roundtrip 0.0001 sein"


# =============================================================================
# SECTION 5: Button-Zustands-Tests
# =============================================================================

class TestButtonStates:

    def test_update_button_states_running(self, app):
        """State 'running': Start DISABLED, Pause NORMAL, Cancel NORMAL."""
        app._update_button_states("running")
        _pump(app)
        assert str(app._btn_start["state"])  == "disabled"
        assert str(app._btn_pause["state"])  == "normal"
        assert str(app._btn_resume["state"]) == "disabled"
        assert str(app._btn_cancel["state"]) == "normal"
        assert str(app._btn_reset["state"])  == "disabled"

    def test_update_button_states_paused(self, app):
        """State 'paused': Resume NORMAL, Pause DISABLED, Cancel NORMAL."""
        app._update_button_states("paused")
        _pump(app)
        assert str(app._btn_start["state"])  == "disabled"
        assert str(app._btn_pause["state"])  == "disabled"
        assert str(app._btn_resume["state"]) == "normal"
        assert str(app._btn_cancel["state"]) == "normal"

    def test_update_button_states_completed(self, app):
        """State 'completed': Start NORMAL, Pause/Resume/Cancel DISABLED."""
        app._update_button_states("completed")
        _pump(app)
        assert str(app._btn_start["state"])  == "normal"
        assert str(app._btn_pause["state"])  == "disabled"
        assert str(app._btn_resume["state"]) == "disabled"
        assert str(app._btn_cancel["state"]) == "disabled"
        assert str(app._btn_reset["state"])  == "normal"

    def test_animation_checkbox_locked_during_run(self, app):
        """Animation-Checkbox muss während Run DISABLED, in idle NORMAL sein."""
        app._update_button_states("running")
        _pump(app)
        assert str(app._cb_animation["state"]) in ("disabled",),             "Animation-Checkbox muss während Run DISABLED sein"

        app._update_button_states("idle")
        _pump(app)
        assert str(app._cb_animation["state"]) == "normal",             "Animation-Checkbox muss in idle NORMAL sein"


# =============================================================================
# SECTION 6: Event-Pump-Tests
# =============================================================================

class TestEventPump:

    def test_episode_event_updates_status_fields(self, app):
        """episode-Event in Queue → Statusfelder werden korrekt aktualisiert."""
        run_id = str(uuid.uuid4())
        # session_id der App übernehmen
        sid = app._session_id

        event = _make_episode_event(
            session_id=sid,
            run_id=run_id,
            episode=5,
            reward=8.3,
            moving_average=7.1,
            best_reward=9.0,
            steps=200,
            total_steps=500,
        )
        app._event_queue.put(event)

        # Einen Pump-Zyklus durchlaufen
        app._pump_events()
        _pump(app)

        assert app._var_episode.get() == "5",             f"Episode-Feld muss '5' sein, ist: {app._var_episode.get()}"
        assert "8.3" in app._var_ep_reward.get(),             f"Reward-Feld muss '8.3' enthalten, ist: {app._var_ep_reward.get()}"
        assert "7.1" in app._var_moving_avg.get(),             f"MA-Feld muss '7.1' enthalten, ist: {app._var_moving_avg.get()}"
        assert "9.0" in app._var_best_reward.get(),             f"Best-Reward-Feld muss '9.0' enthalten, ist: {app._var_best_reward.get()}"

    def test_session_filter_rejects_stale_events(self, app):
        """Event mit falscher session_id darf Status nicht verändern."""
        stale_sid = str(uuid.uuid4())  # absichtlich andere session_id
        run_id = str(uuid.uuid4())

        event = _make_episode_event(
            session_id=stale_sid,
            run_id=run_id,
            reward=999.9,
        )
        app._event_queue.put(event)
        app._pump_events()
        _pump(app)

        # Status darf nicht auf "running" gewechselt haben
        status = app._var_status.get()
        assert status != "running",             f"Veraltetes Event darf Status nicht ändern, ist: {status}"
        # Reward-Feld darf nicht 999.9 zeigen
        assert "999" not in app._var_ep_reward.get(),             "Veraltetes Event darf Reward-Feld nicht aktualisieren"

    def test_training_done_resets_progressbar(self, app):
        """training_done(reason='finished') → Progressbar determinate / 100."""
        sid = app._session_id
        run_id = str(uuid.uuid4())

        # Zuerst episode-Event, damit Orchestrator-Check greift
        app._event_queue.put(_make_episode_event(sid, run_id))
        app._event_queue.put(_make_training_done_event(
            sid, run_id, completion_reason="finished"))

        app._orchestrator = MagicMock()
        app._orchestrator.has_active_trainers.return_value = False

        app._pump_events()
        _pump(app)

        mode = app._progressbar["mode"]
        value = float(app._progressbar["value"])
        assert str(mode) == "determinate",             f"Progressbar muss nach training_done determinate sein, ist: {mode}"

    def test_error_event_does_not_crash_app(self, app):
        """error-Event darf die App nicht zum Absturz bringen."""
        sid = app._session_id
        run_id = str(uuid.uuid4())

        event = _make_error_event(sid, run_id, stage="train_loop")
        app._event_queue.put(event)

        # messagebox.showerror patchen damit kein Dialog blockiert
        with patch("inverted_double_pendulum_ui.messagebox.showerror",
                   return_value=None):
            try:
                app._pump_events()
                _pump(app)
            except Exception as exc:
                pytest.fail(f"App ist bei error-Event abgestürzt: {exc}")

        assert app._var_status.get() == "ERROR",             f"Status muss nach error-Event 'ERROR' sein, ist: {app._var_status.get()}"

    def test_multiple_run_ids_in_compare_mode(self, app):
        """2 episode-Events mit unterschiedlichen run_ids → 2 _plot_data-Einträge."""
        sid = app._session_id
        run_id_1 = str(uuid.uuid4())
        run_id_2 = str(uuid.uuid4())

        app._event_queue.put(_make_episode_event(
            sid, run_id_1, algorithm_name="SAC", display_label="SAC"))
        app._event_queue.put(_make_episode_event(
            sid, run_id_2, algorithm_name="TD3", display_label="TD3"))

        app._pump_events()
        _pump(app)

        assert len(app._plot_data) == 2,             f"_plot_data muss 2 Einträge haben (einen pro run_id), hat: {len(app._plot_data)}"
        assert run_id_1 in app._plot_data, "run_id_1 fehlt in _plot_data"
        assert run_id_2 in app._plot_data, "run_id_2 fehlt in _plot_data"


# =============================================================================
# SECTION 7: Live-Plot-Tests
# =============================================================================

class TestLivePlot:

    def test_plot_data_grows_with_episode_events(self, app):
        """5 episode-Events → _plot_data[run_id]['episodes'] hat Länge 5."""
        sid = app._session_id
        run_id = str(uuid.uuid4())

        for ep in range(1, 6):
            app._event_queue.put(_make_episode_event(
                sid, run_id, episode=ep, reward=float(ep)))

        app._pump_events()
        _pump(app)

        assert run_id in app._plot_data, "run_id fehlt in _plot_data"
        episodes = app._plot_data[run_id]["episodes"]
        assert len(episodes) == 5,             f"episodes-Liste muss Länge 5 haben, hat: {len(episodes)}"
        rewards = app._plot_data[run_id]["rewards"]
        assert len(rewards) == 5,             f"rewards-Liste muss Länge 5 haben, hat: {len(rewards)}"

    def test_clear_plot_resets_plot_data(self, app):
        """Daten eintragen → _clear_plot() → _plot_data und _plot_lines leer."""
        sid = app._session_id
        run_id = str(uuid.uuid4())

        app._event_queue.put(_make_episode_event(sid, run_id))
        app._pump_events()
        _pump(app)

        assert len(app._plot_data) > 0, "Vorher muss Daten geben"

        app._clear_plot()
        _pump(app)

        assert len(app._plot_data) == 0,             "_plot_data muss nach _clear_plot() leer sein"
        assert len(app._plot_lines) == 0,             "_plot_lines muss nach _clear_plot() leer sein"

    def test_threshold_line_present_in_plot(self, app):
        """ax.lines muss eine Linie bei y=REWARD_THRESHOLD enthalten."""
        _pump(app)
        ax = app._ax
        threshold_lines = [
            line for line in ax.lines
            if hasattr(line, "get_ydata")
            and len(line.get_ydata()) > 0
            and all(abs(y - REWARD_THRESHOLD) < 1.0 for y in line.get_ydata())
        ]
        assert len(threshold_lines) >= 1,             f"Threshold-Linie bei y={REWARD_THRESHOLD} fehlt im Plot"


# =============================================================================
# SECTION 8: Config Save/Load-Tests
# =============================================================================

class TestConfigSaveLoad:

    def test_save_config_creates_file(self, app, tmp_path):
        """_on_save_config() erstellt eine JSON-Datei im gewählten Pfad."""
        _pump(app)
        save_path = str(tmp_path / "test_save.json")

        with patch("inverted_double_pendulum_ui.filedialog.asksaveasfilename",
                   return_value=save_path),              patch("inverted_double_pendulum_ui.ConfigState.CONFIG_DIR",
                   str(tmp_path)),              patch("inverted_double_pendulum_ui.messagebox.showinfo",
                   return_value=None):
            app._on_save_config()

        assert os.path.isfile(save_path),             f"Gespeicherte Datei existiert nicht: {save_path}"

        with open(save_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "config" in data, "JSON muss 'config'-Schlüssel enthalten"

    def test_load_config_applies_values(self, app, tmp_path):
        """Gespeicherte JSON → _on_load_config() → gamma-Variable trägt neuen Wert."""
        _pump(app)

        # JSON mit bekannten Werten schreiben
        config_data = app._collect_config_state()
        config_data["gamma"] = 0.87
        state = ConfigState.to_dict(config_data)
        load_path = str(tmp_path / "test_load.json")
        with open(load_path, "w", encoding="utf-8") as f:
            json.dump(state, f)

        with patch("inverted_double_pendulum_ui.filedialog.askopenfilename",
                   return_value=load_path),              patch("inverted_double_pendulum_ui.messagebox.showinfo",
                   return_value=None):
            app._on_load_config()

        _pump(app)
        assert app._var_gamma.get() == pytest.approx(0.87),             f"gamma muss nach Load 0.87 sein, ist: {app._var_gamma.get()}"


# =============================================================================
# SECTION 9: Job-List-Tests
# =============================================================================

class TestJobList:

    def test_add_job_appends_to_list(self, app):
        """_on_add_job() fügt Job zu _job_list und Listbox hinzu."""
        _pump(app)
        app._var_sweep_algo.set("SAC")
        app._var_sweep_param.set("learning_rate")
        app._var_sweep_value.set("0.001")

        app._on_add_job()
        _pump(app)

        assert len(app._job_list) == 1,             f"_job_list muss 1 Eintrag haben, hat: {len(app._job_list)}"
        assert app._job_list[0]["algorithm_name"] == "SAC"
        assert app._job_list[0]["parameter"] == "learning_rate"
        assert app._job_list[0]["value"] == "0.001"
        assert app._job_listbox.size() == 1,             "Listbox muss 1 Eintrag haben"

    def test_remove_job_removes_selected(self, app):
        """Job hinzufügen → selektieren → _on_remove_job() → Liste leer."""
        _pump(app)
        app._var_sweep_algo.set("TD3")
        app._var_sweep_param.set("batch_size")
        app._var_sweep_value.set("128")
        app._on_add_job()
        _pump(app)

        # Ersten Eintrag selektieren
        app._job_listbox.selection_set(0)
        app._on_remove_job()
        _pump(app)

        assert len(app._job_list) == 0,             "_job_list muss nach Entfernen leer sein"
        assert app._job_listbox.size() == 0,             "Listbox muss nach Entfernen leer sein"

    def test_clear_jobs_empties_list(self, app):
        """3 Jobs hinzufügen → _on_clear_jobs() → alles leer."""
        _pump(app)
        for i in range(3):
            app._var_sweep_algo.set("SAC")
            app._var_sweep_param.set("learning_rate")
            app._var_sweep_value.set(f"0.00{i + 1}")
            app._on_add_job()
        _pump(app)
        assert len(app._job_list) == 3

        app._on_clear_jobs()
        _pump(app)

        assert len(app._job_list) == 0,             "_job_list muss nach _on_clear_jobs() leer sein"
        assert app._job_listbox.size() == 0,             "Listbox muss nach _on_clear_jobs() leer sein"


# =============================================================================
# SECTION 10: Validierungs-Tests
# =============================================================================

class TestValidation:

    def test_validate_before_start_blocks_on_error(self, app):
        """Ungültige Config (beide Limits=0) → _validate_before_start() == False."""
        _pump(app)
        app._var_total_timesteps.set(0)
        app._var_total_episodes.set(0)

        with patch("inverted_double_pendulum_ui.messagebox.showerror",
                   return_value=None):
            result = app._validate_before_start()

        assert result is False,             "_validate_before_start() muss False bei ungültiger Config zurückgeben"

    def test_validate_before_start_passes_on_valid_config(self, app):
        """Gültige Standardwerte → _validate_before_start() == True."""
        _pump(app)
        app._var_total_timesteps.set(500_000)
        app._var_total_episodes.set(0)
        # SAC-Tab sicherstellen
        app._algo_notebook.select(0)

        with patch("inverted_double_pendulum_ui.messagebox.askyesno",
                   return_value=True):
            result = app._validate_before_start()

        assert result is True,             "_validate_before_start() muss True bei gültiger Config zurückgeben"
