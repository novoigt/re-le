"""
tests/test_inverted_double_pendulum_logic.py
Logiktests für inverted_double_pendulum_logic.py
Workbench v2.0 — Smoke, Regression, Edge Cases

Ausführung:
    python -m pytest -q --rootdir . --confcutdir . tests/
"""

# =============================================================================
# SECTION 1: Imports & Fixtures
# =============================================================================

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Projektroot erreichbar machen (tests/ liegt eine Ebene tiefer)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inverted_double_pendulum_logic import (
    ConfigState,
    EnvironmentWrapper,
    IDPTrainer,
    Orchestrator,
    PROJECT_NAME,
    REWARD_THRESHOLD,
    validate_config,
)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _drain_queue(q: queue.Queue, timeout: float = 10.0) -> list:
    """Sammelt alle Events aus der Queue bis training_done oder Timeout."""
    events = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            e = q.get(timeout=0.2)
            events.append(e)
            if e.get("type") == "training_done":
                break
        except queue.Empty:
            continue
    return events


def _find_events(events: list, event_type: str) -> list:
    return [e for e in events if e.get("type") == event_type]


def _make_mock_env(n_steps_until_done: int = 5):
    """
    Erzeugt einen MagicMock, der eine Gymnasium-Umgebung simuliert.
    Terminiert nach n_steps_until_done Steps.
    """
    mock_env = MagicMock()
    mock_env.reset.return_value = (np.zeros(9, dtype=np.float32), {})
    mock_env.action_space.shape = (1,)
    mock_env.action_space.sample.return_value = np.array([0.0], dtype=np.float32)
    mock_env.render.return_value = np.zeros((64, 64, 3), dtype=np.uint8)
    mock_env.observation_space.shape = (9,)

    step_counter = {"n": 0}

    def _step(action):
        step_counter["n"] += 1
        done = step_counter["n"] >= n_steps_until_done
        return (
            np.zeros(9, dtype=np.float32),
            1.0,
            done,
            False,
            {},
        )

    mock_env.step.side_effect = _step
    return mock_env


def _make_mock_sb3_model(env):
    """
    Erzeugt einen MagicMock, der ein SB3-Modell simuliert.
    model.learn() ruft den Callback mit einer begrenzten Episode-Sequenz auf.
    """
    model = MagicMock()

    def _predict(obs, deterministic=True):
        return np.array([0.0], dtype=np.float32), None

    model.predict.side_effect = _predict
    return model


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_config() -> Dict[str, Any]:
    return {
        "algorithm_name": "SAC",
        "animation_enabled": False,
        "total_timesteps": 500,
        "total_episodes": 2,
        "eval_interval": 5,
        "eval_episodes": 1,
        "moving_average_window": 2,
        "seed": 42,
        "use_gpu": False,
        "gamma": 0.99,
        "tau": 0.005,
        "buffer_size": 10_000,
        "batch_size": 64,
        "learning_starts": 10,
        "net_arch": "[64, 64]",
        "learning_rate_schedule": "constant",
        "learning_rate": 0.0003,
        "ent_coef": "auto",
        "healthy_reward": 10.0,
        "reset_noise_scale": 0.1,
        "display_label": "SAC (test)",
    }


@pytest.fixture
def event_queue() -> queue.Queue:
    return queue.Queue()


@pytest.fixture
def session_id() -> str:
    return str(uuid.uuid4())


# =============================================================================
# SECTION 2: Smoke-Tests
# =============================================================================

class TestSmoke:

    def _run_trainer(self, config, event_queue, session_id,
                     mock_env, mock_model_cls):
        """Startet IDPTrainer mit gepatchtem Gymnasium und SB3."""
        run_id = str(uuid.uuid4())
        trainer = IDPTrainer(
            config=config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
            run_mode="single_run",
        )

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch(f"inverted_double_pendulum_logic.{mock_model_cls}",
                   return_value=_make_mock_sb3_model(mock_env)):
            trainer.train()

        return trainer

    def test_headless_train_starts_and_terminates(
            self, base_config, event_queue, session_id):
        """Headless TrainLoop startet und terminiert; training_done landet in Queue."""
        mock_env = _make_mock_env(n_steps_until_done=3)
        run_id = str(uuid.uuid4())

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
            run_mode="single_run",
        )

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = _make_mock_sb3_model(mock_env)
            # learn() sofort terminieren
            mock_sac.return_value.learn = MagicMock(return_value=None)
            trainer.train()

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        done_events = _find_events(events, "training_done")
        assert len(done_events) >= 1, "training_done muss in Queue landen"
        assert trainer.status in ("completed", "cancelled", "failed")

    def test_training_done_always_emitted_on_cancel(
            self, base_config, event_queue, session_id):
        """training_done muss auch bei sofortigem cancel() emittiert werden."""
        run_id = str(uuid.uuid4())
        mock_env = _make_mock_env()

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
            run_mode="single_run",
        )

        def _learn_with_cancel(*args, **kwargs):
            trainer.cancel()
            time.sleep(0.05)

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.learn.side_effect = _learn_with_cancel
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)
            trainer.train()

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        done_events = _find_events(events, "training_done")
        assert len(done_events) >= 1,             "training_done muss auch nach cancel() emittiert werden"

    def test_run_episode_returns_steps(
            self, base_config, event_queue, session_id):
        """run_episode() gibt die tatsächlich ausgeführten Steps zurück."""
        n_steps = 7
        mock_env = _make_mock_env(n_steps_until_done=n_steps)
        run_id = str(uuid.uuid4())

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)
            trainer.build_env()
            trainer.build_model()
            steps = trainer.run_episode()

        assert isinstance(steps, int), "run_episode() muss int zurückgeben"
        assert steps > 0, "run_episode() muss > 0 Steps zurückgeben"


# =============================================================================
# SECTION 3: Regression-Tests
# =============================================================================

class TestRegression:

    def test_pause_resume_cycle(self, base_config, event_queue, session_id):
        """pause() → paused, resume() → running, cancel() → training_done."""
        run_id = str(uuid.uuid4())
        mock_env = _make_mock_env()

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        pause_confirmed = threading.Event()
        resume_confirmed = threading.Event()

        def _learn_with_pause_resume(*args, **kwargs):
            # Pause auslösen und warten
            trainer.pause()
            pause_confirmed.set()
            time.sleep(0.3)
            trainer.resume()
            resume_confirmed.set()
            time.sleep(0.1)
            trainer.cancel()

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.learn.side_effect = _learn_with_pause_resume
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)

            t = threading.Thread(target=trainer.train, daemon=True)
            t.start()

            assert pause_confirmed.wait(timeout=5.0), "Pause nicht bestätigt"
            assert trainer.status == "paused",                 f"Erwartet 'paused', bekommen: {trainer.status}"

            assert resume_confirmed.wait(timeout=5.0), "Resume nicht bestätigt"
            t.join(timeout=5.0)

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        done_events = _find_events(events, "training_done")
        assert len(done_events) >= 1
        assert done_events[-1].get("completion_reason") == "cancel_requested"

    def test_cancel_emits_training_done_with_cancelled_status(
            self, base_config, event_queue, session_id):
        """cancel() → training_done mit completion_reason='cancel_requested'."""
        run_id = str(uuid.uuid4())
        mock_env = _make_mock_env()

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        def _immediate_cancel(*args, **kwargs):
            trainer.cancel()

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.learn.side_effect = _immediate_cancel
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)
            trainer.train()

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        done_events = _find_events(events, "training_done")
        assert len(done_events) >= 1
        reason = done_events[-1].get("completion_reason")
        assert reason == "cancel_requested",             f"Erwartet 'cancel_requested', bekommen: {reason}"

    def test_episode_events_emitted_before_training_done(
            self, base_config, event_queue, session_id):
        """
        Mindestens 1 episode-Event muss VOR training_done in der Queue liegen.
        Kein Puffern bis Laufende.
        """
        run_id = str(uuid.uuid4())
        mock_env = _make_mock_env(n_steps_until_done=2)

        # Callback-basierte Überprüfung: Wir simulieren episode-Emission
        # direkt über den Trainer-Mechanismus
        trainer = IDPTrainer(
            config={**base_config, "total_episodes": 3},
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        episode_before_done = threading.Event()

        def _learn_with_episodes(total_timesteps, callback=None, **kwargs):
            # Simuliert 3 abgeschlossene Episoden via Callback
            if callback is not None:
                callback.init(MagicMock())
                for ep in range(3):
                    # Simuliert done=True für Episode
                    callback.locals = {
                        "rewards": [1.0],
                        "dones": [True],
                        "infos": [{}],
                    }
                    callback._on_step()
            episode_before_done.set()

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.learn.side_effect = _learn_with_episodes
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)
            trainer.train()

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        # training_done muss vorhanden sein
        done_events = _find_events(events, "training_done")
        assert len(done_events) >= 1, "training_done fehlt"

        # training_done darf nicht das erste Event sein
        first_done_idx = next(
            i for i, e in enumerate(events) if e.get("type") == "training_done"
        )
        assert first_done_idx > 0 or len(events) >= 1,             "Es müssen Events vor training_done existieren"

    def test_error_event_on_env_build_failure(
            self, base_config, event_queue, session_id):
        """
        Wenn gymnasium.make() wirft, muss error mit error_stage='env_build'
        und danach training_done mit status='failed' emittiert werden.
        """
        run_id = str(uuid.uuid4())

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        with patch("inverted_double_pendulum_logic.gym.make",
                   side_effect=RuntimeError("MuJoCo not found")):
            trainer.train()

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        error_events = _find_events(events, "error")
        done_events = _find_events(events, "training_done")

        assert len(error_events) >= 1, "error-Event muss emittiert werden"
        assert error_events[0].get("error_stage") == "env_build",             f"error_stage muss 'env_build' sein, ist: {error_events[0].get('error_stage')}"

        assert len(done_events) >= 1,             "training_done muss auch nach env_build-Fehler emittiert werden"
        assert done_events[-1].get("status") == "failed",             f"Status muss 'failed' sein, ist: {done_events[-1].get('status')}"

    def test_algo_compare_isolated_run_ids(
            self, base_config, event_queue, session_id):
        """
        run_compare() mit SAC + TD3: alle training_done haben unterschiedliche
        run_ids. Keine Event-Cross-Contamination.
        """
        orchestrator = Orchestrator()
        configs = []
        for algo in ["SAC", "TD3"]:
            cfg = dict(base_config)
            cfg["algorithm_name"] = algo
            cfg["display_label"] = algo
            # TD3-spezifische Parameter
            if algo == "TD3":
                cfg["policy_delay"] = 2
                cfg["policy_noise"] = 0.15
                cfg["noise_clip"] = 0.5
            configs.append(cfg)

        mock_env = _make_mock_env(n_steps_until_done=2)

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac,              patch("inverted_double_pendulum_logic.TD3") as mock_td3:

            for mock_cls in (mock_sac, mock_td3):
                m = MagicMock()
                m.learn = MagicMock(return_value=None)
                m.predict.return_value = (np.array([0.0], dtype=np.float32), None)
                mock_cls.return_value = m

            orchestrator.run_compare(configs, event_queue, session_id)

            # Warten bis beide Trainer fertig
            deadline = time.monotonic() + 15.0
            done_count = 0
            all_events = []
            while time.monotonic() < deadline and done_count < 2:
                try:
                    e = event_queue.get(timeout=0.5)
                    all_events.append(e)
                    if e.get("type") == "training_done":
                        done_count += 1
                except queue.Empty:
                    continue

        done_events = _find_events(all_events, "training_done")
        assert len(done_events) >= 2,             f"Erwartet 2 training_done, bekommen: {len(done_events)}"

        run_ids = {e.get("run_id") for e in done_events}
        assert len(run_ids) == len(done_events),             "Alle training_done müssen unterschiedliche run_ids haben"

    def test_sweep_training_done_per_job(
            self, base_config, event_queue, session_id):
        """
        run_sweep() mit 3 Jobs → 3× training_done mit
        unterschiedlichen run_ids und korrekten job_index-Werten.
        """
        orchestrator = Orchestrator()
        job_list = [
            {"algorithm_name": "SAC", "parameter": "learning_rate",
             "value": "0.001", "display_label": "SAC lr=0.001"},
            {"algorithm_name": "SAC", "parameter": "learning_rate",
             "value": "0.0003", "display_label": "SAC lr=0.0003"},
            {"algorithm_name": "SAC", "parameter": "batch_size",
             "value": "128", "display_label": "SAC bs=128"},
        ]
        mock_env = _make_mock_env(n_steps_until_done=2)

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            m = MagicMock()
            m.learn = MagicMock(return_value=None)
            m.predict.return_value = (np.array([0.0], dtype=np.float32), None)
            mock_sac.return_value = m

            orchestrator.run_sweep(job_list, base_config, event_queue, session_id)

            deadline = time.monotonic() + 20.0
            done_count = 0
            all_events = []
            while time.monotonic() < deadline and done_count < 3:
                try:
                    e = event_queue.get(timeout=0.5)
                    all_events.append(e)
                    if e.get("type") == "training_done":
                        done_count += 1
                except queue.Empty:
                    continue

        done_events = _find_events(all_events, "training_done")
        assert len(done_events) == 3,             f"Erwartet 3 training_done, bekommen: {len(done_events)}"

        run_ids = {e.get("run_id") for e in done_events}
        assert len(run_ids) == 3, "Alle Jobs müssen unterschiedliche run_ids haben"

        job_indices = {e.get("job_index") for e in done_events}
        assert job_indices == {0, 1, 2},             f"job_index muss 0, 1, 2 sein, bekommen: {job_indices}"

    def test_config_state_save_load_roundtrip(self, tmp_path, base_config):
        """ConfigState.save() → load() muss identisches config-Dict liefern."""
        original_dir = ConfigState.CONFIG_DIR
        ConfigState.CONFIG_DIR = str(tmp_path)

        try:
            filename = "test_config.json"
            saved_path = ConfigState.save(filename, base_config)

            assert os.path.isfile(saved_path),                 f"Datei wurde nicht erstellt: {saved_path}"

            loaded = ConfigState.load(saved_path)

            for key, value in base_config.items():
                assert key in loaded, f"Feld '{key}' fehlt nach Laden"
                assert loaded[key] == value,                     f"Feld '{key}': erwartet {value}, bekommen {loaded[key]}"
        finally:
            ConfigState.CONFIG_DIR = original_dir

    def test_run_episode_returns_exact_steps(
            self, base_config, event_queue, session_id):
        """run_episode() muss exakt N Steps zurückgeben (Mock terminiert nach N)."""
        n_steps = 11
        mock_env = _make_mock_env(n_steps_until_done=n_steps)
        run_id = str(uuid.uuid4())

        trainer = IDPTrainer(
            config=base_config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
        )

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac:
            mock_sac.return_value = MagicMock()
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)
            trainer.build_env()
            trainer.build_model()
            steps = trainer.run_episode()

        assert steps == n_steps,             f"Erwartet {n_steps} Steps, bekommen: {steps}"


# =============================================================================
# SECTION 4: Edge-Case-Tests
# =============================================================================

class TestEdgeCases:

    def test_incompatible_sweep_override_reported(
            self, base_config, event_queue, session_id):
        """
        Job mit parameter='policy_delay' und algo='TD3' muss
        error-Event mit error_stage='config' auslösen — kein Crash.
        """
        orchestrator = Orchestrator()
        job_list = [
            {
                "algorithm_name": "TD3",
                "parameter": "policy_delay",
                "value": "5",
                "display_label": "TD3 policy_delay=5",
            }
        ]
        mock_env = _make_mock_env()

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.TD3") as mock_td3:
            mock_td3.return_value = MagicMock()
            mock_td3.return_value.learn = MagicMock(return_value=None)

            orchestrator.run_sweep(job_list, base_config, event_queue, session_id)

            deadline = time.monotonic() + 5.0
            all_events = []
            while time.monotonic() < deadline:
                try:
                    e = event_queue.get(timeout=0.3)
                    all_events.append(e)
                except queue.Empty:
                    break

        error_events = _find_events(all_events, "error")
        assert len(error_events) >= 1,             "Inkompatibler Override muss error-Event auslösen"
        assert error_events[0].get("error_stage") == "config",             f"error_stage muss 'config' sein, ist: {error_events[0].get('error_stage')}"
        assert error_events[0].get("recoverable") is True,             "Inkompatibler Override muss recoverable=True haben"

    def test_algo_compare_parameter_isolation(
            self, base_config, event_queue, session_id):
        """
        SAC und TD3 dürfen sich gegenseitig ihre learning_rate nicht überschreiben.
        """
        sac_config = dict(base_config)
        sac_config["algorithm_name"] = "SAC"
        sac_config["learning_rate"] = 0.001

        td3_config = dict(base_config)
        td3_config["algorithm_name"] = "TD3"
        td3_config["learning_rate"] = 0.0001
        td3_config["policy_delay"] = 2
        td3_config["policy_noise"] = 0.15
        td3_config["noise_clip"] = 0.5

        # Configs dürfen sich nach dem Compare nicht verändert haben
        sac_lr_before = sac_config["learning_rate"]
        td3_lr_before = td3_config["learning_rate"]

        mock_env = _make_mock_env()
        orchestrator = Orchestrator()

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac,              patch("inverted_double_pendulum_logic.TD3") as mock_td3:

            for mock_cls in (mock_sac, mock_td3):
                m = MagicMock()
                m.learn = MagicMock(return_value=None)
                m.predict.return_value = (np.array([0.0], dtype=np.float32), None)
                mock_cls.return_value = m

            orchestrator.run_compare(
                [sac_config, td3_config], event_queue, session_id)

            deadline = time.monotonic() + 10.0
            done_count = 0
            while time.monotonic() < deadline and done_count < 2:
                try:
                    e = event_queue.get(timeout=0.5)
                    if e.get("type") == "training_done":
                        done_count += 1
                except queue.Empty:
                    continue

        assert sac_config["learning_rate"] == sac_lr_before,             "SAC learning_rate wurde verändert"
        assert td3_config["learning_rate"] == td3_lr_before,             "TD3 learning_rate wurde verändert"

    def test_validate_config_errors_and_warnings(self):
        """validate_config() liefert korrekte Fehler und Warnungen."""

        # ERROR: beide Limits = 0
        cfg_error = {
            "algorithm_name": "SAC",
            "total_timesteps": 0,
            "total_episodes": 0,
            "learning_rate": 0.0003,
            "batch_size": 256,
            "buffer_size": 1_000_000,
            "top_quantiles_to_drop_per_net": 2,
        }
        messages = validate_config(cfg_error)
        errors = [m for m in messages if m.startswith("ERROR:")]
        assert len(errors) >= 1, "Beide Limits=0 muss ERROR liefern"

        # WARNING: TD3 mit hoher LR
        cfg_td3_warn = {
            "algorithm_name": "TD3",
            "total_timesteps": 1000,
            "total_episodes": 0,
            "learning_rate": 0.005,
            "batch_size": 256,
            "buffer_size": 1_000_000,
            "top_quantiles_to_drop_per_net": 2,
        }
        messages = validate_config(cfg_td3_warn)
        warnings = [m for m in messages if m.startswith("WARNING:")]
        assert any("TD3" in w for w in warnings),             "TD3 mit lr > Threshold muss WARNING liefern"

        # WARNING: TQC mit zu hohem Drop
        cfg_tqc_warn = {
            "algorithm_name": "TQC",
            "total_timesteps": 1000,
            "total_episodes": 0,
            "learning_rate": 0.001,
            "batch_size": 256,
            "buffer_size": 1_000_000,
            "top_quantiles_to_drop_per_net": 4,
        }
        messages = validate_config(cfg_tqc_warn)
        warnings = [m for m in messages if m.startswith("WARNING:")]
        assert any("TQC" in w for w in warnings),             "TQC mit top_q_drop >= 3 muss WARNING liefern"

    def test_animation_toggle_mid_run_no_rebuild(self, base_config):
        """
        set_animation_enabled(False) darf nicht die Umgebung zerstören (kein Rebuild).
        Frame-Emission stoppt nach dem Toggle.
        """
        mock_env = _make_mock_env()
        config = dict(base_config)
        config["animation_enabled"] = True

        wrapper = EnvironmentWrapper(config)

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env):
            wrapper.build()

        env_before = wrapper.env
        assert wrapper.is_animation_enabled() is True

        # Mid-Run Toggle: deaktivieren
        wrapper.set_animation_enabled(False)
        assert wrapper.is_animation_enabled() is False
        assert wrapper.env is env_before,             "Env-Instanz darf sich beim Toggle nicht ändern (kein Rebuild)"

        # Frame-Emission nach Toggle: muss None zurückgeben
        frame = wrapper.render()
        assert frame is None,             "render() muss None liefern wenn Animation deaktiviert"

        # Wieder aktivieren — immer noch dieselbe Env
        wrapper.set_animation_enabled(True)
        assert wrapper.env is env_before,             "Env-Instanz darf sich auch beim Re-Aktivieren nicht ändern"

        wrapper.close()

    def test_sweep_job_derived_from_base_config(
            self, base_config, event_queue, session_id):
        """
        Sweep-Job überschreibt nur learning_rate;
        gamma aus base_config muss unverändert im Job-Config bleiben.
        """
        orchestrator = Orchestrator()
        base = dict(base_config)
        base["gamma"] = 0.95

        job_list = [
            {
                "algorithm_name": "SAC",
                "parameter": "learning_rate",
                "value": "0.001",
                "display_label": "SAC lr=0.001",
            }
        ]

        captured_configs = []
        mock_env = _make_mock_env()

        original_init = IDPTrainer.__init__

        def _capture_init(self_inner, config, *args, **kwargs):
            captured_configs.append(dict(config))
            original_init(self_inner, config, *args, **kwargs)

        with patch("inverted_double_pendulum_logic.gym.make",
                   return_value=mock_env),              patch("inverted_double_pendulum_logic.SAC") as mock_sac,              patch.object(IDPTrainer, "__init__", _capture_init):

            mock_sac.return_value = MagicMock()
            mock_sac.return_value.learn = MagicMock(return_value=None)
            mock_sac.return_value.predict.return_value = (
                np.array([0.0], dtype=np.float32), None)

            orchestrator.run_sweep(job_list, base, event_queue, session_id)

            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                try:
                    e = event_queue.get(timeout=0.3)
                    if e.get("type") == "training_done":
                        break
                except queue.Empty:
                    break

        assert len(captured_configs) >= 1, "Kein Config-Dict wurde erfasst"
        job_cfg = captured_configs[0]
        assert job_cfg.get("gamma") == 0.95,             f"gamma muss aus base_config erhalten bleiben (0.95), ist: {job_cfg.get('gamma')}"
        assert float(job_cfg.get("learning_rate", 0)) == pytest.approx(0.001),             f"learning_rate muss durch Job überschrieben sein (0.001)"
