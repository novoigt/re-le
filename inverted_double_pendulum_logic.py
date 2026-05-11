"""
inverted_double_pendulum_logic.py
Trainingslogik für das Projekt "Inverted Double Pendulum"
Workbench v2.0 — compatible with workbench_logic.md v2.0
"""

# =============================================================================
# SECTION 1: Imports & Konstanten
# =============================================================================

from __future__ import annotations

import csv
import json
import os
import threading
import time
import traceback
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

# SB3 / SB3-Contrib — Importfehler werden beim Programmstart gemeldet
try:
    import stable_baselines3 as sb3
    from stable_baselines3 import SAC, TD3
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.noise import NormalActionNoise
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    SB3_IMPORT_ERROR = "stable-baselines3 nicht installiert. Bitte: pip install stable-baselines3"

try:
    from sb3_contrib import TQC
    TQC_AVAILABLE = True
except ImportError:
    TQC_AVAILABLE = False
    TQC_IMPORT_ERROR = "sb3-contrib nicht installiert. Bitte: pip install sb3-contrib"

try:
    import gymnasium as gym
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

# Projektspezifische Konstanten
REWARD_THRESHOLD = 9100.0
ENV_ID = "InvertedDoublePendulum-v5"
PROJECT_NAME = "inverted_double_pendulum"

NET_ARCH_MAP: Dict[str, List[int]] = {
    "[64, 64]":    [64, 64],
    "[128, 128]":  [128, 128],
    "[256, 256]":  [256, 256],
    "[400, 300]":  [400, 300],
    "[512, 512]":  [512, 512],
}

SUPPORTED_ALGORITHMS = ["SAC", "TD3", "TQC"]

# Validierungsregeln
VALIDATION_RULES = {
    "td3_lr_warning_threshold": 0.001,
    "tqc_drop_warning_threshold": 3,
    "batch_buffer_ratio_warning": 10,
}


# =============================================================================
# SECTION 2: Hilfsfunktionen
# =============================================================================

def make_lr_schedule(schedule: str, lr: float) -> Callable[[float], float]:
    """Erzeugt ein SB3-kompatibles LR-Schedule-Callable (progress: 1→0)."""
    if schedule == "linear":
        return lambda progress: lr * progress
    elif schedule == "inverse_time":
        return lambda progress: lr / (1.0 + 9.0 * (1.0 - progress))
    else:
        return lambda progress: lr


def parse_net_arch(net_arch_str: str) -> List[int]:
    """Konvertiert den GUI-String '[256, 256]' in eine Liste."""
    return NET_ARCH_MAP.get(net_arch_str, [256, 256])


def get_device(use_gpu: bool) -> str:
    """Bestimmt das Rechengerät; fällt bei fehlendem GPU auf CPU zurück."""
    if not use_gpu:
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def build_event(event_type: str, base_meta: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Erzeugt ein vollständiges Event-Dict gemäß Event-Vertrag."""
    event = {
        "type": event_type,
        "session_id": base_meta.get("session_id", ""),
        "run_id": base_meta.get("run_id", ""),
        "timestamp": datetime.utcnow().isoformat(),
        "source": PROJECT_NAME + "_logic",
        "status": base_meta.get("status", "running"),
        "algorithm_name": base_meta.get("algorithm_name", ""),
        "run_mode": base_meta.get("run_mode", "single_run"),
        "display_label": base_meta.get("display_label", base_meta.get("algorithm_name", "")),
    }
    event.update(kwargs)
    return event


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    Prüft die Konfiguration auf Validierungsregeln aus inverted_double_pendulum.md.
    Gibt eine Liste von Warnungs-/Fehlermeldungen zurück.
    Fehler beginnen mit 'ERROR:', Warnungen mit 'WARNING:'.
    """
    messages = []
    ts = config.get("total_timesteps", 0)
    te = config.get("total_episodes", 0)
    if ts == 0 and te == 0:
        messages.append("ERROR: Mindestens ein Trainingslimit muss > 0 sein "
                        "(total_timesteps oder total_episodes).")

    algo = config.get("algorithm_name", "")
    lr = config.get("learning_rate", 0.0003)
    if algo == "TD3" and lr > VALIDATION_RULES["td3_lr_warning_threshold"]:
        messages.append(f"WARNING: TD3: Lernrate > {VALIDATION_RULES['td3_lr_warning_threshold']} "
                        "kann zu Instabilität führen.")

    drop = config.get("top_quantiles_to_drop_per_net", 2)
    if algo == "TQC" and drop >= VALIDATION_RULES["tqc_drop_warning_threshold"]:
        messages.append(f"WARNING: TQC: top_quantiles_to_drop_per_net >= "
                        f"{VALIDATION_RULES['tqc_drop_warning_threshold']} kann die Leistung "
                        "stark verschlechtern.")

    batch = config.get("batch_size", 256)
    buf = config.get("buffer_size", 1_000_000)
    if buf > 0 and batch > buf / VALIDATION_RULES["batch_buffer_ratio_warning"]:
        messages.append("WARNING: Batch-Größe ist relativ zum Buffer sehr groß — "
                        "mögliche Überanpassung an frühe Erfahrungen.")

    return messages


# =============================================================================
# SECTION 3: EnvironmentWrapper
# =============================================================================

class EnvironmentWrapper:
    """
    Kapselt die Gymnasium-Umgebung InvertedDoublePendulum-v5.
    Verwaltet Aufbau, Reset, Step, Rendering und Animation-Toggle.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._env = None
        self._animation_enabled = threading.Event()
        if config.get("animation_enabled", False):
            self._animation_enabled.set()
        self._lock = threading.Lock()

    def build(self) -> None:
        """Baut die Gymnasium-Umgebung auf."""
        render_mode = "rgb_array" if self._config.get("animation_enabled", False) else None
        healthy_reward = float(self._config.get("healthy_reward", 10.0))
        reset_noise_scale = float(self._config.get("reset_noise_scale", 0.1))
        self._env = gym.make(
            ENV_ID,
            render_mode=render_mode,
            healthy_reward=healthy_reward,
            reset_noise_scale=reset_noise_scale,
        )

    def rebuild(self, config: Dict[str, Any]) -> None:
        """Schließt die alte Umgebung und baut mit neuer Konfiguration neu auf."""
        self.close()
        self._config = config
        if config.get("animation_enabled", False):
            self._animation_enabled.set()
        else:
            self._animation_enabled.clear()
        self.build()

    def reset(self, seed: Optional[int] = None):
        """Setzt die Umgebung zurück; gibt (obs, info) zurück."""
        kwargs = {}
        if seed and seed > 0:
            kwargs["seed"] = seed
        return self._env.reset(**kwargs)

    def step(self, action):
        """Führt einen Schritt aus; gibt (obs, reward, terminated, truncated, info) zurück."""
        return self._env.step(action)

    def render(self) -> Optional[np.ndarray]:
        """Gibt den aktuellen Frame zurück, wenn Animation aktiviert und env gebaut."""
        if not self._animation_enabled.is_set():
            return None
        if self._env is None:
            return None
        try:
            return self._env.render()
        except Exception:
            return None

    def set_animation_enabled(self, enabled: bool) -> None:
        """Thread-sicherer Mid-Run-Toggle der Frame-Emission."""
        with self._lock:
            if enabled:
                self._animation_enabled.set()
            else:
                self._animation_enabled.clear()

    def is_animation_enabled(self) -> bool:
        return self._animation_enabled.is_set()

    def close(self) -> None:
        if self._env is not None:
            try:
                self._env.close()
            except Exception:
                pass
            self._env = None

    @property
    def env(self):
        return self._env


# =============================================================================
# SECTION 4: TrainingCallback (SB3 BaseCallback)
# =============================================================================

class TrainingCallback(BaseCallback):
    """
    SB3-Callback, der als TrainLoop-Takt fungiert.
    Emittiert episode-, episode_aux- und step-Events in die Event-Queue.
    Verwaltet Pause/Cancel, Laufzeitgrenzen und Frame-Streaming.
    """

    FRAME_THROTTLE_INTERVAL = 0.05  # Sekunden zwischen Frame-Emissionen

    def __init__(
        self,
        env_wrapper: EnvironmentWrapper,
        config: Dict[str, Any],
        event_queue,
        run_meta: Dict[str, Any],
        pause_event: threading.Event,
        cancel_event: threading.Event,
        verbose: int = 0,
    ):
        super().__init__(verbose)
        self._env_wrapper = env_wrapper
        self._config = config
        self._queue = event_queue
        self._meta = run_meta
        self._pause_event = pause_event
        self._cancel_event = cancel_event

        # Episode-Tracking
        self._episode_count = 0
        self._episode_rewards: List[float] = []
        self._current_ep_reward = 0.0
        self._current_ep_steps = 0
        self._total_steps = 0
        self._best_reward = float("-inf")
        self._moving_avg_window = int(config.get("moving_average_window", 20))
        self._reward_buffer: deque = deque(maxlen=self._moving_avg_window)

        # Laufzeitgrenzen
        self._total_timesteps_limit = int(config.get("total_timesteps", 500_000))
        self._total_episodes_limit = int(config.get("total_episodes", 0))

        # Evaluations-Checkpoint
        self._eval_interval = int(config.get("eval_interval", 10))
        self._eval_episodes = int(config.get("eval_episodes", 5))

        # Frame-Throttle
        self._last_frame_time = 0.0

        # Solved-Flag
        self._solved_announced = False

    def _on_training_start(self) -> None:
        self._meta["status"] = "running"

    def _on_step(self) -> bool:
        """Wird nach jedem Umgebungsschritt aufgerufen."""
        # Pause-Polling
        while self._pause_event.is_set():
            self._meta["status"] = "paused"
            time.sleep(0.1)
            if self._cancel_event.is_set():
                break
        self._meta["status"] = "running"

        # Cancel
        if self._cancel_event.is_set():
            return False

        self._current_ep_reward += self.locals.get("rewards", [0])[0]
        self._current_ep_steps += 1
        self._total_steps += 1

        # Frame-Emission (throttled)
        now = time.monotonic()
        if (self._env_wrapper.is_animation_enabled()
                and now - self._last_frame_time >= self.FRAME_THROTTLE_INTERVAL):
            frame = self._env_wrapper.render()
            if frame is not None:
                self._queue.put(build_event(
                    "episode_aux",
                    self._meta,
                    episode=self._episode_count,
                    frames=[frame],
                ))
                self._last_frame_time = now

        # Episode abgeschlossen?
        dones = self.locals.get("dones", [False])
        if dones[0]:
            self._on_episode_end()
            # Laufzeitgrenzen prüfen
            if not self._check_limits():
                return False

        return True

    def _on_episode_end(self) -> None:
        self._episode_count += 1
        ep_reward = self._current_ep_reward
        self._episode_rewards.append(ep_reward)
        self._reward_buffer.append(ep_reward)

        if ep_reward > self._best_reward:
            self._best_reward = ep_reward

        moving_avg = float(np.mean(self._reward_buffer)) if self._reward_buffer else ep_reward

        # Solved-Ankündigung
        solved_msg = None
        if moving_avg >= REWARD_THRESHOLD and not self._solved_announced:
            self._solved_announced = True
            solved_msg = f"✓ Solved! Episode {self._episode_count}"

        # episode-Event
        total_ep_limit = self._total_episodes_limit if self._total_episodes_limit > 0 else 0
        self._queue.put(build_event(
            "episode",
            self._meta,
            episode=self._episode_count,
            episodes=total_ep_limit,
            reward=round(ep_reward, 4),
            moving_average=round(moving_avg, 4),
            steps=self._current_ep_steps,
            best_reward=round(self._best_reward, 4),
            total_steps=self._total_steps,
            lr=self._config.get("learning_rate", 0.0003),
            seed=self._config.get("seed", 42),
            message=solved_msg,
        ))

        # Evaluations-Checkpoint
        if self._eval_interval > 0 and self._episode_count % self._eval_interval == 0:
            self._emit_eval_checkpoint()

        # Diagnose-Daten (episode_aux)
        info_list = self.locals.get("infos", [{}])
        info = info_list[0] if info_list else {}
        if any(k in info for k in ("reward_survive", "distance_penalty", "velocity_penalty")):
            self._queue.put(build_event(
                "episode_aux",
                self._meta,
                episode=self._episode_count,
                diagnostics={
                    "reward_survive": info.get("reward_survive"),
                    "distance_penalty": info.get("distance_penalty"),
                    "velocity_penalty": info.get("velocity_penalty"),
                },
            ))

        # Reset Episode-Zähler
        self._current_ep_reward = 0.0
        self._current_ep_steps = 0

    def _emit_eval_checkpoint(self) -> None:
        """Führt eine leichte Evaluationsphase durch und emittiert episode_aux."""
        try:
            eval_env = gym.make(ENV_ID, render_mode=None)
            rewards = []
            for _ in range(self._eval_episodes):
                obs, _ = eval_env.reset()
                done = False
                ep_r = 0.0
                while not done:
                    action, _ = self.model.predict(obs, deterministic=True)
                    obs, r, terminated, truncated, _ = eval_env.step(action)
                    ep_r += r
                    done = terminated or truncated
                rewards.append(ep_r)
            eval_env.close()
            mean_r = float(np.mean(rewards))
            std_r = float(np.std(rewards))
            self._queue.put(build_event(
                "episode_aux",
                self._meta,
                episode=self._episode_count,
                eval_points={
                    "eval_mean_reward": round(mean_r, 4),
                    "eval_std_reward": round(std_r, 4),
                    "eval_n_episodes": self._eval_episodes,
                    "at_episode": self._episode_count,
                },
            ))
        except Exception:
            pass

    def _check_limits(self) -> bool:
        """
        Prüft Laufzeitgrenzen (ODER-Bedingung).
        Gibt False zurück, wenn Training beendet werden soll.
        """
        if (self._total_episodes_limit > 0
                and self._episode_count >= self._total_episodes_limit):
            return False
        # total_timesteps wird von SB3 intern verwaltet
        return True

    def get_episode_count(self) -> int:
        return self._episode_count

    def get_total_steps(self) -> int:
        return self._total_steps

    def get_best_reward(self) -> float:
        return self._best_reward

    def get_episode_rewards(self) -> List[float]:
        return list(self._episode_rewards)


# =============================================================================
# SECTION 5: IDPTrainer
# =============================================================================

class IDPTrainer:
    """
    Trainer für InvertedDoublePendulum-v5.
    Orchestriert EnvironmentWrapper, SB3-Modell und TrainingCallback.
    Headless und GUI-gekoppelt nutzbar.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_queue,
        run_id: str,
        session_id: str,
        run_mode: str = "single_run",
        job_index: Optional[int] = None,
        job_count: Optional[int] = None,
    ):
        self._config = config
        self._queue = event_queue
        self._run_id = run_id
        self._session_id = session_id
        self._run_mode = run_mode
        self._job_index = job_index
        self._job_count = job_count

        algo = config.get("algorithm_name", "SAC")
        self._run_meta: Dict[str, Any] = {
            "session_id": session_id,
            "run_id": run_id,
            "algorithm_name": algo,
            "display_label": config.get("display_label", algo),
            "run_mode": run_mode,
            "status": "idle",
        }

        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._status = "idle"
        self._lock = threading.Lock()

        self._env_wrapper: Optional[EnvironmentWrapper] = None
        self._model = None
        self._callback: Optional[TrainingCallback] = None

    # ------------------------------------------------------------------
    # Öffentliche Steuer-Primitive
    # ------------------------------------------------------------------

    def pause(self) -> None:
        with self._lock:
            if self._status == "running":
                self._pause_event.set()
                self._status = "paused"
                self._run_meta["status"] = "paused"

    def resume(self) -> None:
        with self._lock:
            if self._status == "paused":
                self._pause_event.clear()
                self._status = "running"
                self._run_meta["status"] = "running"

    def cancel(self) -> None:
        with self._lock:
            self._cancel_event.set()
            self._pause_event.clear()
            self._status = "cancelled"
            self._run_meta["status"] = "cancelled"

    def set_animation_enabled(self, enabled: bool) -> None:
        if self._env_wrapper is not None:
            self._env_wrapper.set_animation_enabled(enabled)

    @property
    def status(self) -> str:
        return self._status

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def algorithm_name(self) -> str:
        return self._config.get("algorithm_name", "SAC")

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------

    def build_env(self) -> None:
        """Baut den EnvironmentWrapper auf."""
        self._env_wrapper = EnvironmentWrapper(self._config)
        self._env_wrapper.build()

    def build_model(self) -> None:
        """Baut das SB3-Modell gemäß algorithm_name und Config."""
        algo = self._config.get("algorithm_name", "SAC")
        device = get_device(self._config.get("use_gpu", False))
        net_arch = parse_net_arch(self._config.get("net_arch", "[256, 256]"))
        lr_schedule = make_lr_schedule(
            self._config.get("learning_rate_schedule", "constant"),
            float(self._config.get("learning_rate", 0.0003)),
        )
        gamma = float(self._config.get("gamma", 0.99))
        tau = float(self._config.get("tau", 0.005))
        buffer_size = int(self._config.get("buffer_size", 1_000_000))
        batch_size = int(self._config.get("batch_size", 256))
        learning_starts = int(self._config.get("learning_starts", 1000))
        policy_kwargs = dict(net_arch=net_arch)

        env = self._env_wrapper.env

        if algo == "SAC":
            ent_coef = self._config.get("ent_coef", "auto")
            self._model = SAC(
                "MlpPolicy", env,
                learning_rate=lr_schedule,
                gamma=gamma, tau=tau,
                buffer_size=buffer_size, batch_size=batch_size,
                learning_starts=learning_starts,
                ent_coef=ent_coef,
                policy_kwargs=policy_kwargs,
                device=device, verbose=0,
            )

        elif algo == "TD3":
            action_dim = env.action_space.shape[0]
            action_noise = NormalActionNoise(
                mean=np.zeros(action_dim),
                sigma=float(self._config.get("policy_noise", 0.15)) * np.ones(action_dim),
            )
            self._model = TD3(
                "MlpPolicy", env,
                learning_rate=lr_schedule,
                gamma=gamma, tau=tau,
                buffer_size=buffer_size, batch_size=batch_size,
                learning_starts=learning_starts,
                action_noise=action_noise,
                policy_delay=int(self._config.get("policy_delay", 2)),
                target_policy_noise=float(self._config.get("policy_noise", 0.15)),
                target_noise_clip=float(self._config.get("noise_clip", 0.5)),
                policy_kwargs=policy_kwargs,
                device=device, verbose=0,
            )

        elif algo == "TQC":
            if not TQC_AVAILABLE:
                raise ImportError(TQC_IMPORT_ERROR)
            ent_coef = self._config.get("ent_coef", "auto")
            self._model = TQC(
                "MlpPolicy", env,
                learning_rate=lr_schedule,
                gamma=gamma, tau=tau,
                buffer_size=buffer_size, batch_size=batch_size,
                learning_starts=learning_starts,
                ent_coef=ent_coef,
                top_quantiles_to_drop_per_net=int(
                    self._config.get("top_quantiles_to_drop_per_net", 2)
                ),
                n_quantiles=int(self._config.get("n_quantiles", 25)),
                n_critics=int(self._config.get("n_critics", 2)),
                policy_kwargs=policy_kwargs,
                device=device, verbose=0,
            )
        else:
            raise ValueError(f"Unbekannter Algorithmus: {algo}")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self) -> None:
        """
        Haupttraining via model.learn() + TrainingCallback.
        Emittiert strukturierte Events. Headless und GUI-tauglich.
        """
        self._status = "running"
        self._run_meta["status"] = "running"
        completion_reason = "finished"

        try:
            # Environment aufbauen
            try:
                self.build_env()
            except Exception as exc:
                self._status = "failed"
                self._run_meta["status"] = "failed"
                completion_reason = "error"
                self._emit_error("env_build",
                                 f"Umgebung konnte nicht aufgebaut werden: {exc}", exc)
                return

            # Modell aufbauen
            try:
                self.build_model()
            except Exception as exc:
                self._status = "failed"
                self._run_meta["status"] = "failed"
                completion_reason = "error"
                self._emit_error("config",
                                 f"Modell konnte nicht aufgebaut werden: {exc}", exc)
                return

            # Callback aufbauen
            self._callback = TrainingCallback(
                env_wrapper=self._env_wrapper,
                config=self._config,
                event_queue=self._queue,
                run_meta=self._run_meta,
                pause_event=self._pause_event,
                cancel_event=self._cancel_event,
            )

            # Timesteps-Limit (0 = sehr groß)
            ts_limit = int(self._config.get("total_timesteps", 500_000))
            if ts_limit <= 0:
                ts_limit = int(1e9)

            # Training
            try:
                self._model.learn(
                    total_timesteps=ts_limit,
                    callback=self._callback,
                    reset_num_timesteps=True,
                )
            except Exception as exc:
                if self._cancel_event.is_set():
                    completion_reason = "cancel_requested"
                else:
                    self._emit_error("train_loop",
                                     f"Fehler im Trainingsloop: {exc}", exc)
                    completion_reason = "error"

            if self._cancel_event.is_set():
                completion_reason = "cancel_requested"
                self._status = "cancelled"
            else:
                self._status = "completed"

        except Exception as exc:
            self._emit_error("train_loop", f"Unerwarteter Fehler: {exc}", exc)
            completion_reason = "error"
            self._status = "failed"

        finally:
            episodes_done = self._callback.get_episode_count() if self._callback else 0
            # Modell speichern bei erfolgreichem Abschluss
            if completion_reason == "finished":
                self._save_model_on_done()
            self._emit_training_done(completion_reason, episodes_done)
            if self._env_wrapper:
                self._env_wrapper.close()

    def run_episode(self, collect_frames: bool = False) -> int:
        """
        Führt eine einzelne Episode headless durch.
        Gibt die tatsächlich ausgeführten Schritte zurück.
        """
        if self._env_wrapper is None or self._model is None:
            return 0
        obs, _ = self._env_wrapper.reset(seed=self._config.get("seed", 42))
        done = False
        steps = 0
        while not done:
            action, _ = self._model.predict(obs, deterministic=True)
            obs, _, terminated, truncated, _ = self._env_wrapper.step(action)
            done = terminated or truncated
            steps += 1
        return steps

    def evaluate_policy(self, n_episodes: int = 5) -> Dict[str, Any]:
        """
        Evaluiert die aktuelle Policy über n_episodes deterministische Episoden.
        Gibt dict(mean, std, n) zurück.
        """
        if self._model is None:
            return {"mean": 0.0, "std": 0.0, "n": 0}
        rewards = []
        eval_env = None
        try:
            eval_env = gym.make(ENV_ID, render_mode=None)
            for _ in range(n_episodes):
                obs, _ = eval_env.reset()
                done = False
                ep_r = 0.0
                while not done:
                    action, _ = self._model.predict(obs, deterministic=True)
                    obs, r, terminated, truncated, _ = eval_env.step(action)
                    ep_r += r
                    done = terminated or truncated
                rewards.append(ep_r)
        except Exception as exc:
            self._emit_error("evaluate", f"Evaluationsfehler: {exc}", exc)
        finally:
            if eval_env is not None:
                eval_env.close()

        if not rewards:
            return {"mean": 0.0, "std": 0.0, "n": 0}
        return {
            "mean": float(np.mean(rewards)),
            "std": float(np.std(rewards)),
            "n": len(rewards),
        }

    # ------------------------------------------------------------------
    # Interne Event-Emission
    # ------------------------------------------------------------------

    def _emit_training_done(self, completion_reason: str, episodes_completed: int) -> None:
        ep_limit = int(self._config.get("total_episodes", 0))
        best = self._callback.get_best_reward() if self._callback else float("-inf")
        total_steps = self._callback.get_total_steps() if self._callback else 0
        rewards = self._callback.get_episode_rewards() if self._callback else []
        ma_final = float(np.mean(rewards[-20:])) if len(rewards) >= 1 else 0.0

        final_status = {
            "finished": "completed",
            "cancel_requested": "cancelled",
            "error": "failed",
            "early_stop": "completed",
        }.get(completion_reason, "completed")

        self._run_meta["status"] = final_status

        export_paths = {}
        # CSV-Export
        if rewards:
            csv_path = ExportHelper.export_csv(
                run_id=self._run_id,
                algorithm_name=self.algorithm_name,
                rows=[{"episode": i + 1, "reward": r} for i, r in enumerate(rewards)],
            )
            if csv_path:
                export_paths["csv"] = csv_path

        event = build_event(
            "training_done",
            self._run_meta,
            completion_reason=completion_reason,
            episodes_completed=episodes_completed,
            episodes_planned=ep_limit,
            run_mode=self._run_mode,
            best_reward=round(best, 4) if best != float("-inf") else None,
            moving_average_final=round(ma_final, 4),
            total_steps_completed=total_steps,
            export_paths=export_paths,
            summary_metrics={
                "algorithm_name": self.algorithm_name,
                "run_id": self._run_id,
                "seed": self._config.get("seed", 42),
                "run_mode": self._run_mode,
                "best_reward": round(best, 4) if best != float("-inf") else None,
                "episodes_completed": episodes_completed,
                "reward_threshold": REWARD_THRESHOLD,
                "solved": best >= REWARD_THRESHOLD,
            },
        )
        if self._job_index is not None:
            event["job_index"] = self._job_index
        if self._job_count is not None:
            event["job_count"] = self._job_count
        self._queue.put(event)

    def _emit_error(self, stage: str, message: str, exc: Exception) -> None:
        self._run_meta["status"] = "failed"
        self._queue.put(build_event(
            "error",
            self._run_meta,
            error_code=type(exc).__name__,
            error_message=message,
            error_stage=stage,
            details=str(exc),
            exception_type=type(exc).__name__,
            traceback=traceback.format_exc(),
            recoverable=False,
        ))

    def _save_model_on_done(self) -> Optional[str]:
        if self._model is None:
            return None
        try:
            return ExportHelper.export_model(
                model=self._model,
                run_id=self._run_id,
                algorithm_name=self.algorithm_name,
            )
        except Exception:
            return None


# =============================================================================
# SECTION 6: Orchestrator
# =============================================================================

class Orchestrator:
    """
    Orchestriert single_run, algo_compare und sweep_run.
    Verwaltet aktive Trainer thread-sicher.
    """

    def __init__(self):
        self._active_trainers: List[IDPTrainer] = []
        self._lock = threading.Lock()

    def _register(self, trainer: IDPTrainer) -> None:
        with self._lock:
            self._active_trainers.append(trainer)

    def _unregister(self, trainer: IDPTrainer) -> None:
        with self._lock:
            if trainer in self._active_trainers:
                self._active_trainers.remove(trainer)

    def _clear(self) -> None:
        with self._lock:
            self._active_trainers.clear()

    def run_single(
        self,
        config: Dict[str, Any],
        event_queue,
        session_id: str,
    ) -> IDPTrainer:
        """Startet einen einzelnen Trainingslauf in einem Hintergrund-Thread."""
        run_id = str(uuid.uuid4())
        trainer = IDPTrainer(
            config=config,
            event_queue=event_queue,
            run_id=run_id,
            session_id=session_id,
            run_mode="single_run",
        )
        self._register(trainer)

        def _run():
            try:
                trainer.train()
            finally:
                self._unregister(trainer)

        t = threading.Thread(target=_run, daemon=True,
                             name=f"trainer-single-{run_id[:8]}")
        t.start()
        return trainer

    def run_compare(
        self,
        configs: List[Dict[str, Any]],
        event_queue,
        session_id: str,
    ) -> List[IDPTrainer]:
        """
        Startet alle Algorithmen parallel.
        Jeder Algorithmus läuft in eigenem Thread mit eigener run_id.
        Parameter-Isolation ist durch separate Config-Dicts gewährleistet.
        """
        trainers = []
        for cfg in configs:
            run_id = str(uuid.uuid4())
            algo = cfg.get("algorithm_name", "SAC")
            trainer = IDPTrainer(
                config=cfg,
                event_queue=event_queue,
                run_id=run_id,
                session_id=session_id,
                run_mode="algo_compare",
            )
            self._register(trainer)
            trainers.append(trainer)

            def _run(t=trainer):
                try:
                    t.train()
                finally:
                    self._unregister(t)

            thread = threading.Thread(target=_run, daemon=True,
                                      name=f"trainer-compare-{algo}-{run_id[:8]}")
            thread.start()

        return trainers

    def run_sweep(
        self,
        job_list: List[Dict[str, Any]],
        base_config: Dict[str, Any],
        event_queue,
        session_id: str,
    ) -> None:
        """
        Führt Sweep-Jobs sequentiell aus.
        Jeder Job ist ein eigenständiger Lauf mit eigener run_id.
        Jobs werden aus base_config + Override-Satz abgeleitet.
        Inkompatible Overrides werden gemeldet und übersprungen.
        """
        job_count = len(job_list)

        def _sweep_runner():
            for job_index, job in enumerate(job_list):
                if not job:
                    continue

                # Config aus Basis + Override ableiten
                job_config = dict(base_config)
                algo = job.get("algorithm_name", base_config.get("algorithm_name", "SAC"))
                job_config["algorithm_name"] = algo

                param = job.get("parameter")
                value = job.get("value")
                display_label = job.get("display_label",
                                       f"{algo} {param}={value}")

                # Inkompatible Overrides prüfen
                if param == "policy_delay" and algo == "TD3":
                    event_queue.put(build_event(
                        "error",
                        {
                            "session_id": session_id,
                            "run_id": "sweep-validation",
                            "algorithm_name": algo,
                            "run_mode": "sweep_run",
                            "status": "failed",
                        },
                        error_code="IncompatibleOverride",
                        error_message=(f"Job {job_index + 1}: policy_delay kann nicht "
                                       "per Sweep überschrieben werden."),
                        error_stage="config",
                        recoverable=True,
                    ))
                    continue

                if param and value is not None:
                    try:
                        # Typ-Erhaltung
                        existing = job_config.get(param)
                        if isinstance(existing, float):
                            job_config[param] = float(value)
                        elif isinstance(existing, int):
                            job_config[param] = int(value)
                        elif isinstance(existing, bool):
                            job_config[param] = bool(value)
                        else:
                            job_config[param] = value
                    except (ValueError, TypeError) as exc:
                        event_queue.put(build_event(
                            "error",
                            {
                                "session_id": session_id,
                                "run_id": "sweep-validation",
                                "algorithm_name": algo,
                                "run_mode": "sweep_run",
                                "status": "failed",
                            },
                            error_code="OverrideCastError",
                            error_message=(f"Job {job_index + 1}: Parameter '{param}' "
                                           f"konnte nicht gesetzt werden: {exc}"),
                            error_stage="config",
                            recoverable=True,
                        ))
                        continue

                job_config["display_label"] = display_label

                run_id = str(uuid.uuid4())
                trainer = IDPTrainer(
                    config=job_config,
                    event_queue=event_queue,
                    run_id=run_id,
                    session_id=session_id,
                    run_mode="sweep_run",
                    job_index=job_index,
                    job_count=job_count,
                )
                self._register(trainer)
                try:
                    trainer.train()
                finally:
                    self._unregister(trainer)

        t = threading.Thread(target=_sweep_runner, daemon=True, name="sweep-runner")
        t.start()

    def pause_all(self) -> None:
        with self._lock:
            for trainer in self._active_trainers:
                trainer.pause()

    def resume_all(self) -> None:
        with self._lock:
            for trainer in self._active_trainers:
                trainer.resume()

    def cancel_all(self) -> None:
        with self._lock:
            for trainer in list(self._active_trainers):
                trainer.cancel()

    def set_animation_enabled_all(self, enabled: bool) -> None:
        with self._lock:
            for trainer in self._active_trainers:
                trainer.set_animation_enabled(enabled)

    @property
    def active_trainers(self) -> List[IDPTrainer]:
        with self._lock:
            return list(self._active_trainers)

    def has_active_trainers(self) -> bool:
        with self._lock:
            return len(self._active_trainers) > 0


# =============================================================================
# SECTION 7: ConfigState
# =============================================================================

class ConfigState:
    """
    Serialisierung und Persistenz von GUI-/Trainingskonfigurationen.
    Speichert und lädt JSON-Dateien unter configs/.
    """

    CONFIG_DIR = "configs"

    @staticmethod
    def to_dict(gui_state: Dict[str, Any]) -> Dict[str, Any]:
        """Erzeugt einen serialisierbaren config_state aus dem GUI-Zustand."""
        return {
            "project": PROJECT_NAME,
            "version": "1.0",
            "saved_at": datetime.utcnow().isoformat(),
            "config": dict(gui_state),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validiert und restauriert einen config_state.
        Gibt das innere config-Dict zurück.
        """
        if not isinstance(d, dict):
            raise ValueError("Ungültiger config_state: kein Dict.")
        if d.get("project") != PROJECT_NAME:
            raise ValueError(f"config_state gehört nicht zu Projekt '{PROJECT_NAME}'.")
        config = d.get("config", {})
        if not isinstance(config, dict):
            raise ValueError("config_state enthält kein gültiges 'config'-Dict.")
        return config

    @classmethod
    def save(cls, filename: str, gui_state: Dict[str, Any]) -> str:
        """Speichert config_state als JSON unter configs/. Gibt Pfad zurück."""
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        path = os.path.join(cls.CONFIG_DIR, filename)
        state = cls.to_dict(gui_state)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return path

    @classmethod
    def load(cls, path: str) -> Dict[str, Any]:
        """Lädt und validiert einen config_state aus einer JSON-Datei."""
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)

    @classmethod
    def generate_filename(cls, suffix: str = "") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{PROJECT_NAME}_config_{ts}"
        if suffix:
            base += f"_{suffix}"
        return base + ".json"


# =============================================================================
# SECTION 8: ExportHelper
# =============================================================================

class ExportHelper:
    """
    Hilfsfunktionen für Datei-Exporte:
    PNG-Plots, CSV-Ergebnisse, SB3-Modell-Checkpoints.
    """

    PLOTS_DIR = "plots"
    CSV_DIR = "results_csv"
    MODELS_DIR = "models"

    @classmethod
    def export_plot_data(
        cls,
        run_id: str,
        algorithm_name: str,
        rewards: List[float],
        moving_averages: List[float],
        run_mode: str = "single_run",
        display_label: Optional[str] = None,
    ) -> str:
        """
        Exportiert den Reward-Plot als PNG nach plots/.
        Verwendet das projektspezifische Light-Theme.
        Gibt den Exportpfad zurück.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(cls.PLOTS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = display_label or algorithm_name
        filename = f"{PROJECT_NAME}_{algorithm_name}_{run_id[:8]}_{ts}.png"
        path = os.path.join(cls.PLOTS_DIR, filename)

        # Light-Theme (projektspezifisch)
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")
        ax.tick_params(colors="#333333")
        ax.xaxis.label.set_color("#333333")
        ax.yaxis.label.set_color("#333333")
        ax.grid(color="#cccccc", linestyle="--", alpha=0.5)

        algo_colors = ["#1a73e8", "#e53935", "#2e7d32", "#6a1b9a"]
        color = algo_colors[0]

        episodes = list(range(1, len(rewards) + 1))
        ax.plot(episodes, rewards, color=color, alpha=0.3, linewidth=1.0, label=f"{label} (raw)")
        if moving_averages:
            ax.plot(episodes[:len(moving_averages)], moving_averages,
                    color=color, alpha=1.0, linewidth=2.5, label=f"{label} (MA)")

        # Reward Threshold
        ax.axhline(y=REWARD_THRESHOLD, color="#f57c00", linestyle="--",
                   alpha=0.7, linewidth=1.5, label=f"Solved ({REWARD_THRESHOLD})")

        ax.set_xlabel("Episode", color="#333333")
        ax.set_ylabel("Reward", color="#333333")
        ax.set_title(f"{algorithm_name} — Reward über Episoden ({run_mode})", color="#333333")
        legend = ax.legend(facecolor="#ffffff", edgecolor="#cccccc", labelcolor="#333333")

        fig.tight_layout()
        fig.savefig(path, dpi=150, facecolor="#ffffff")
        plt.close(fig)
        return path

    @classmethod
    def export_csv(
        cls,
        run_id: str,
        algorithm_name: str,
        rows: List[Dict[str, Any]],
        display_label: Optional[str] = None,
    ) -> Optional[str]:
        """Exportiert Episodendaten als CSV nach results_csv/."""
        if not rows:
            return None
        os.makedirs(cls.CSV_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{PROJECT_NAME}_{algorithm_name}_{run_id[:8]}_{ts}.csv"
        path = os.path.join(cls.CSV_DIR, filename)
        fieldnames = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    @classmethod
    def export_model(
        cls,
        model,
        run_id: str,
        algorithm_name: str,
    ) -> Optional[str]:
        """Speichert ein SB3-Modell als .zip unter models/."""
        os.makedirs(cls.MODELS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{algorithm_name}_{run_id[:8]}_{ts}"
        path = os.path.join(cls.MODELS_DIR, filename)
        try:
            model.save(path)
            return path + ".zip"
        except Exception:
            return None
