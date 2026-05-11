"""
inverted_double_pendulum_ui.py
GUI für das Projekt "Inverted Double Pendulum"
Workbench v2.0 — compatible with workbench_ui.md v2.0
"""

# =============================================================================
# SECTION 1: Imports & Konstanten
# =============================================================================

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from inverted_double_pendulum_logic import (
    REWARD_THRESHOLD,
    SUPPORTED_ALGORITHMS,
    ConfigState,
    ExportHelper,
    Orchestrator,
    validate_config,
)

# --- Light-Theme Farbpalette (projektspezifisch) ---
THEME = {
    "bg":          "#ffffff",
    "axes_bg":     "#ffffff",
    "tick":        "#333333",
    "label":       "#333333",
    "grid":        "#cccccc",
    "threshold":   "#f57c00",
    "legend_face": "#ffffff",
    "legend_edge": "#cccccc",
    "legend_text": "#333333",
}
ALGO_COLORS = ["#1a73e8", "#e53935", "#2e7d32", "#6a1b9a", "#00838f"]

# GUI-Farben
GUI_BG        = "#f5f5f5"
GUI_GROUP_BG  = "#ffffff"
GUI_HEADER_BG = "#e8eaf6"
GUI_FONT      = ("Segoe UI", 9)
GUI_FONT_BOLD = ("Segoe UI", 9, "bold")
GUI_FONT_MONO = ("Consolas", 9)

# Event-Pump
PUMP_INTERVAL_MS  = 50
PUMP_BATCH_SIZE   = 20
PLOT_REDRAW_INTERVAL_MS = 200

# Button-Zustände
STATE_IDLE      = "idle"
STATE_RUNNING   = "running"
STATE_PAUSED    = "paused"
STATE_COMPLETED = "completed"
STATE_CANCELLED = "cancelled"


# =============================================================================
# SECTION 2: AnimationWindow
# =============================================================================

class AnimationWindow(tk.Toplevel):
    """Separates Toplevel-Fenster für die Live-Environment-Animation."""

    def __init__(self, parent: tk.Tk, on_close_callback=None):
        super().__init__(parent)
        self.title("Animation — InvertedDoublePendulum-v5")
        self.geometry("520x420")
        self.resizable(True, True)
        self.configure(bg="#111111")
        self._on_close_cb = on_close_callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._label = tk.Label(self, bg="#111111", text="Warte auf ersten Frame…",
                               fg="#aaaaaa", font=GUI_FONT)
        self._label.pack(fill=tk.BOTH, expand=True)
        self._photo: Optional[ImageTk.PhotoImage] = None

    def update_frame(self, frame) -> None:
        """Konvertiert numpy RGB-Array → PIL → ImageTk und zeigt es an."""
        if not PIL_AVAILABLE or frame is None:
            return
        try:
            img = Image.fromarray(frame)
            w = self._label.winfo_width() or 500
            h = self._label.winfo_height() or 400
            img = img.resize((w, h), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self._label.configure(image=self._photo, text="")
        except Exception:
            pass

    def _on_close(self) -> None:
        if self._on_close_cb:
            self._on_close_cb()
        self.destroy()


# =============================================================================
# SECTION 3: StatusPopup
# =============================================================================

class StatusPopup(tk.Toplevel):
    """Zeigt erweiterte Run-Metadaten an (Session ID, Run ID, etc.)."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Run Details")
        self.geometry("460x200")
        self.resizable(False, False)
        self.configure(bg=GUI_BG)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        fields = ["Session ID", "Run ID", "Last Update", "Completion Reason"]
        self._vars: Dict[str, tk.StringVar] = {}
        for i, f in enumerate(fields):
            tk.Label(self, text=f + ":", font=GUI_FONT_BOLD,
                     bg=GUI_BG, anchor="w").grid(row=i, column=0, sticky="w",
                                                  padx=12, pady=3)
            var = tk.StringVar(value="—")
            tk.Label(self, textvariable=var, font=GUI_FONT_MONO,
                     bg=GUI_BG, anchor="w", fg="#333333").grid(
                         row=i, column=1, sticky="w", padx=8, pady=3)
            self._vars[f] = var
        self.withdraw()

    def update_data(self, session_id: str, run_id: str,
                    last_update: str, completion_reason: str) -> None:
        self._vars["Session ID"].set(session_id[:36] if session_id else "—")
        self._vars["Run ID"].set(run_id[:36] if run_id else "—")
        self._vars["Last Update"].set(last_update or "—")
        self._vars["Completion Reason"].set(completion_reason or "—")


# =============================================================================
# SECTION 4: IDPApp
# =============================================================================

class IDPApp(tk.Tk):
    """
    Zentrale GUI-Klasse für InvertedDoublePendulum.
    Verwaltet Layout, Parameter, Event-Pump, Plot und Run-Modi.
    """

    # ------------------------------------------------------------------
    # 4.1 Init & Bootstrapping
    # ------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self.title("Inverted Double Pendulum — RL Workbench")
        self.geometry("1280x820")
        self.minsize(900, 600)
        self.configure(bg=GUI_BG)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Interne Zustände
        self._session_id: str = str(uuid.uuid4())
        self._event_queue: queue.Queue = queue.Queue()
        self._orchestrator: Orchestrator = Orchestrator()
        self._ui_state: str = STATE_IDLE
        self._job_list: List[Dict[str, Any]] = []
        self._run_mode_var = tk.StringVar(value="single")

        # Plot-Daten pro run_id
        self._plot_data: Dict[str, Dict[str, List[float]]] = {}
        self._plot_lines: Dict[str, Dict[str, Any]] = {}
        self._last_redraw_time: float = 0.0
        self._plot_dirty: bool = False

        # Popup-Referenzen
        self._anim_window: Optional[AnimationWindow] = None
        self._status_popup: Optional[StatusPopup] = None

        # Aktuelle Run-Metadaten (für Popup)
        self._last_session_id: str = ""
        self._last_run_id: str = ""
        self._last_update: str = ""
        self._last_completion: str = ""

        # Dependency-Check
        self._check_dependencies()

        # Layout aufbauen
        self._build_layout()
        self._set_initial_state()

        # Event-Pump starten
        self.after(PUMP_INTERVAL_MS, self._pump_events)

    def _check_dependencies(self) -> None:
        """Prüft SB3, TQC und MuJoCo beim Programmstart."""
        missing = []
        try:
            import stable_baselines3
        except ImportError:
            missing.append("stable-baselines3  →  pip install stable-baselines3")
        try:
            import sb3_contrib
        except ImportError:
            missing.append("sb3-contrib  →  pip install sb3-contrib")
        try:
            import gymnasium as gym
            gym.make("InvertedDoublePendulum-v5")
        except Exception:
            missing.append("gymnasium[mujoco]  →  pip install gymnasium[mujoco]")
        if missing:
            msg = "Fehlende Abhängigkeiten: " + ", ".join(missing) + " — Das Programm startet, Training ist jedoch nicht möglich."
            messagebox.showwarning("Abhängigkeiten fehlen", msg)

    # ------------------------------------------------------------------
    # 4.2 Layout-Aufbau
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Vertikales Haupt-PanedWindow: Obere Zone / Steuerleiste / Live-Plot."""
        self._main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self._main_pane.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Obere Zone
        self._upper_frame = ttk.Frame(self._main_pane)
        self._main_pane.add(self._upper_frame, weight=6)
        self._build_upper_zone()

        # Steuerleiste + Current-Run
        self._middle_frame = ttk.Frame(self._main_pane)
        self._main_pane.add(self._middle_frame, weight=1)
        self._build_control_bar()
        self._build_current_run_panel()

        # Live-Plot
        self._plot_frame = ttk.Frame(self._main_pane)
        self._main_pane.add(self._plot_frame, weight=3)
        self._build_live_plot()

    def _build_upper_zone(self) -> None:
        """Horizontales PanedWindow: Parameter-Panel links, Animation rechts."""
        self._upper_pane = ttk.PanedWindow(self._upper_frame, orient=tk.HORIZONTAL)
        self._upper_pane.pack(fill=tk.BOTH, expand=True)

        # Parameter-Panel (links)
        self._param_outer = ttk.Frame(self._upper_pane)
        self._upper_pane.add(self._param_outer, weight=3)
        self._build_parameter_panel()

        # Animations-Placeholder (rechts)
        self._anim_placeholder = ttk.LabelFrame(self._upper_pane,
                                                 text="Animation", padding=4)
        self._upper_pane.add(self._anim_placeholder, weight=2)
        self._anim_status_label = tk.Label(
            self._anim_placeholder,
            text="Animation in separatem Fenster (Checkbox aktivieren und Training starten)",
            font=GUI_FONT, fg="#888888", bg=GUI_GROUP_BG, justify=tk.CENTER,
        )
        self._anim_status_label.pack(fill=tk.BOTH, expand=True)

    def _build_parameter_panel(self) -> None:
        """Scrollbares Parameter-Panel mit Mausrad-Unterstützung."""
        container = ttk.Frame(self._param_outer)
        container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._param_canvas = tk.Canvas(container, bg=GUI_BG,
                                       yscrollcommand=scrollbar.set,
                                       highlightthickness=0)
        self._param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._param_canvas.yview)

        self._param_inner = ttk.Frame(self._param_canvas)
        self._canvas_window = self._param_canvas.create_window(
            (0, 0), window=self._param_inner, anchor="nw")

        self._param_inner.bind("<Configure>", self._on_param_configure)
        self._param_canvas.bind("<Configure>", self._on_canvas_configure)

        # Mausrad-Binding
        for widget in (self._param_canvas, self._param_inner):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)

        # 2-spaltiges Grid für Gruppen
        self._param_inner.columnconfigure(0, weight=1)
        self._param_inner.columnconfigure(1, weight=1)

        self._build_group_environment()
        self._build_group_training()
        self._build_group_presets()
        self._build_group_algorithms()
        self._build_group_sweep()

    def _on_param_configure(self, event=None) -> None:
        self._param_canvas.configure(
            scrollregion=self._param_canvas.bbox("all"))

    def _on_canvas_configure(self, event=None) -> None:
        self._param_canvas.itemconfig(self._canvas_window,
                                      width=self._param_canvas.winfo_width())

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.num == 4:
            self._param_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._param_canvas.yview_scroll(1, "units")
        else:
            self._param_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _make_group(self, parent, title: str,
                    row: int, col: int,
                    rowspan: int = 1, colspan: int = 1) -> ttk.Frame:
        """Erstellt eine beschriftete Gruppe im Parameter-Panel."""
        lf = ttk.LabelFrame(parent, text=title, padding=6)
        lf.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan,
                sticky="nsew", padx=4, pady=4)
        return lf

    def _lbl_entry(self, parent, label: str, row: int,
                   var: tk.Variable, width: int = 10) -> ttk.Entry:
        ttk.Label(parent, text=label, font=GUI_FONT).grid(
            row=row, column=0, sticky="w", padx=4, pady=2)
        e = ttk.Entry(parent, textvariable=var, width=width, font=GUI_FONT)
        e.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return e

    def _lbl_spinbox(self, parent, label: str, row: int,
                     var: tk.Variable, from_: float, to: float,
                     increment: float = 1.0, width: int = 10) -> ttk.Spinbox:
        ttk.Label(parent, text=label, font=GUI_FONT).grid(
            row=row, column=0, sticky="w", padx=4, pady=2)
        sb = ttk.Spinbox(parent, textvariable=var, from_=from_, to=to,
                         increment=increment, width=width, font=GUI_FONT)
        sb.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return sb

    def _lbl_dropdown(self, parent, label: str, row: int,
                      var: tk.StringVar, options: List[str],
                      width: int = 14) -> ttk.Combobox:
        ttk.Label(parent, text=label, font=GUI_FONT).grid(
            row=row, column=0, sticky="w", padx=4, pady=2)
        cb = ttk.Combobox(parent, textvariable=var, values=options,
                          state="readonly", width=width, font=GUI_FONT)
        cb.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        return cb

    # ------------------------------------------------------------------
    # Gruppe: Environment (row=0, col=0)
    # ------------------------------------------------------------------

    def _build_group_environment(self) -> None:
        g = self._make_group(self._param_inner, "Environment", row=0, col=0)
        g.columnconfigure(1, weight=1)

        self._var_animation = tk.BooleanVar(value=False)
        self._cb_animation = ttk.Checkbutton(
            g, text="Animation aktivieren",
            variable=self._var_animation,
            command=self._on_animation_toggle)
        self._cb_animation.grid(row=0, column=0, columnspan=2,
                                sticky="w", padx=4, pady=2)

        self._var_frame_interval = tk.IntVar(value=10)
        self._sb_frame_interval = self._lbl_spinbox(
            g, "Frame interval (ms)", 1,
            self._var_frame_interval, 1, 500, 1, 8)

        self._var_healthy_reward = tk.DoubleVar(value=10.0)
        self._lbl_spinbox(g, "healthy_reward", 2,
                          self._var_healthy_reward, 0.1, 100.0, 0.5, 8)

        self._var_reset_noise = tk.DoubleVar(value=0.1)
        self._lbl_spinbox(g, "reset_noise_scale", 3,
                          self._var_reset_noise, 0.0, 1.0, 0.01, 8)

    def _on_animation_toggle(self) -> None:
        """Aktualisiert Frame-Interval-Spinbox und informiert aktive Trainer."""
        enabled = self._var_animation.get()
        state = "normal" if enabled else "disabled"
        self._sb_frame_interval.configure(state=state)
        # Mid-Run-Toggle (nur Frame-Emission, kein Rebuild)
        if self._orchestrator.has_active_trainers():
            self._orchestrator.set_animation_enabled_all(enabled)
            if enabled and self._anim_window is None:
                self._open_animation_window()
        self._update_anim_status()

    def _update_anim_status(self) -> None:
        if self._var_animation.get():
            self._anim_status_label.configure(
                text="Animation aktiviert (Fenster öffnet beim Trainingsstart)")
        else:
            self._anim_status_label.configure(
                text="Animation in separatem Fenster (Checkbox aktivieren und Training starten)")

    def _open_animation_window(self) -> None:
        if self._anim_window is not None:
            try:
                self._anim_window.lift()
                return
            except tk.TclError:
                self._anim_window = None
        self._anim_window = AnimationWindow(self, on_close_callback=self._on_anim_window_close)

    def _on_anim_window_close(self) -> None:
        self._anim_window = None

    # ------------------------------------------------------------------
    # Gruppe: Training / General (row=1, col=0)
    # ------------------------------------------------------------------

    def _build_group_training(self) -> None:
        g = self._make_group(self._param_inner, "Training / General", row=1, col=0)
        g.columnconfigure(1, weight=1)

        self._var_total_timesteps = tk.IntVar(value=500_000)
        self._lbl_spinbox(g, "total_timesteps", 0,
                          self._var_total_timesteps, 0, 10_000_000, 10_000, 10)

        self._var_total_episodes = tk.IntVar(value=0)
        self._lbl_spinbox(g, "total_episodes", 1,
                          self._var_total_episodes, 0, 100_000, 10, 10)

        ttk.Label(g, text="Training endet beim ersten erreichten Limit; 0 = ignorieren",
                  font=("Segoe UI", 8), foreground="#666666").grid(
                      row=2, column=0, columnspan=2, sticky="w", padx=4)

        self._var_eval_interval = tk.IntVar(value=10)
        self._lbl_spinbox(g, "eval_interval", 3,
                          self._var_eval_interval, 1, 1000, 1, 8)

        self._var_eval_episodes = tk.IntVar(value=5)
        self._lbl_spinbox(g, "eval_episodes", 4,
                          self._var_eval_episodes, 1, 50, 1, 8)

        self._var_ma_window = tk.IntVar(value=20)
        self._lbl_spinbox(g, "moving_avg_window", 5,
                          self._var_ma_window, 5, 200, 5, 8)

        self._var_seed = tk.IntVar(value=42)
        self._lbl_spinbox(g, "seed", 6,
                          self._var_seed, 0, 2_147_483_647, 1, 10)

        self._var_use_gpu = tk.BooleanVar(value=False)
        self._cb_use_gpu = ttk.Checkbutton(g, text="Use GPU (CUDA/MPS)",
                                           variable=self._var_use_gpu)
        self._cb_use_gpu.grid(row=7, column=0, columnspan=2,
                              sticky="w", padx=4, pady=2)

    # ------------------------------------------------------------------
    # Gruppe: Presets / Common Parameters (row=0, col=1, rowspan=2)
    # ------------------------------------------------------------------

    def _build_group_presets(self) -> None:
        g = self._make_group(self._param_inner, "Presets / Common Parameters",
                             row=0, col=1, rowspan=2)
        g.columnconfigure(1, weight=1)

        self._var_gamma = tk.DoubleVar(value=0.99)
        self._lbl_spinbox(g, "gamma", 0,
                          self._var_gamma, 0.9, 0.9999, 0.001, 8)

        self._var_tau = tk.DoubleVar(value=0.005)
        self._lbl_spinbox(g, "tau", 1,
                          self._var_tau, 0.001, 0.1, 0.001, 8)

        self._var_buffer_size = tk.IntVar(value=1_000_000)
        self._lbl_spinbox(g, "buffer_size", 2,
                          self._var_buffer_size, 10_000, 2_000_000, 10_000, 10)

        self._var_batch_size = tk.IntVar(value=256)
        self._lbl_spinbox(g, "batch_size", 3,
                          self._var_batch_size, 64, 1024, 64, 8)

        self._var_learning_starts = tk.IntVar(value=1000)
        self._lbl_spinbox(g, "learning_starts", 4,
                          self._var_learning_starts, 100, 50_000, 100, 8)

        self._var_net_arch = tk.StringVar(value="[256, 256]")
        self._lbl_dropdown(g, "net_arch", 5, self._var_net_arch,
                           ["[64, 64]", "[128, 128]", "[256, 256]",
                            "[400, 300]", "[512, 512]"])

        self._var_lr_schedule = tk.StringVar(value="constant")
        self._lbl_dropdown(g, "lr_schedule", 6, self._var_lr_schedule,
                           ["constant", "linear", "inverse_time"])

    # ------------------------------------------------------------------
    # Gruppe: Algorithms (row=2, col=0) — ttk.Notebook
    # ------------------------------------------------------------------

    def _build_group_algorithms(self) -> None:
        g = self._make_group(self._param_inner, "Algorithms", row=2, col=0)

        self._algo_notebook = ttk.Notebook(g)
        self._algo_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._build_tab_sac()
        self._build_tab_td3()
        self._build_tab_tqc()

    def _build_tab_sac(self) -> None:
        tab = ttk.Frame(self._algo_notebook, padding=6)
        self._algo_notebook.add(tab, text="SAC")
        tab.columnconfigure(1, weight=1)

        self._var_sac_lr = tk.DoubleVar(value=0.0003)
        self._lbl_spinbox(tab, "learning_rate", 0,
                          self._var_sac_lr, 0.000001, 0.01, 0.00001, 10)

        self._var_sac_ent_coef = tk.StringVar(value="auto")
        self._lbl_dropdown(tab, "ent_coef", 1, self._var_sac_ent_coef,
                           ["auto", "0.0", "0.1", "0.2", "0.5", "1.0"])

    def _build_tab_td3(self) -> None:
        tab = ttk.Frame(self._algo_notebook, padding=6)
        self._algo_notebook.add(tab, text="TD3")
        tab.columnconfigure(1, weight=1)

        self._var_td3_lr = tk.DoubleVar(value=0.0003)
        self._lbl_spinbox(tab, "learning_rate", 0,
                          self._var_td3_lr, 0.000001, 0.01, 0.00001, 10)

        self._var_td3_policy_delay = tk.IntVar(value=2)
        self._lbl_spinbox(tab, "policy_delay", 1,
                          self._var_td3_policy_delay, 1, 10, 1, 8)

        self._var_td3_policy_noise = tk.DoubleVar(value=0.15)
        self._lbl_spinbox(tab, "policy_noise", 2,
                          self._var_td3_policy_noise, 0.0, 0.5, 0.01, 8)

        self._var_td3_noise_clip = tk.DoubleVar(value=0.5)
        self._lbl_spinbox(tab, "noise_clip", 3,
                          self._var_td3_noise_clip, 0.0, 1.0, 0.05, 8)

    def _build_tab_tqc(self) -> None:
        tab = ttk.Frame(self._algo_notebook, padding=6)
        self._algo_notebook.add(tab, text="TQC")
        tab.columnconfigure(1, weight=1)

        self._var_tqc_lr = tk.DoubleVar(value=0.001)
        self._lbl_spinbox(tab, "learning_rate", 0,
                          self._var_tqc_lr, 0.000001, 0.01, 0.00001, 10)

        self._var_tqc_n_quantiles = tk.IntVar(value=25)
        self._lbl_spinbox(tab, "n_quantiles", 1,
                          self._var_tqc_n_quantiles, 5, 100, 5, 8)

        self._var_tqc_n_critics = tk.IntVar(value=2)
        self._lbl_spinbox(tab, "n_critics", 2,
                          self._var_tqc_n_critics, 1, 5, 1, 8)

        self._var_tqc_drop = tk.IntVar(value=2)
        self._lbl_spinbox(tab, "top_q_drop_per_net", 3,
                          self._var_tqc_drop, 0, 5, 1, 8)

        self._var_tqc_ent_coef = tk.StringVar(value="auto")
        self._lbl_dropdown(tab, "ent_coef", 4, self._var_tqc_ent_coef,
                           ["auto", "0.0", "0.1", "0.2", "0.5", "1.0"])

    # ------------------------------------------------------------------
    # Gruppe: Parameter Tuning / Job List (row=2, col=1)
    # ------------------------------------------------------------------

    def _build_group_sweep(self) -> None:
        g = self._make_group(self._param_inner, "Parameter Tuning / Job List",
                             row=2, col=1)
        g.columnconfigure(1, weight=1)

        # Ziel-Algorithmus
        self._var_sweep_algo = tk.StringVar(value="SAC")
        self._lbl_dropdown(g, "Algorithm", 0, self._var_sweep_algo,
                           SUPPORTED_ALGORITHMS)

        # Ziel-Parameter
        self._var_sweep_param = tk.StringVar(value="learning_rate")
        sweep_params = [
            "learning_rate", "gamma", "tau", "batch_size",
            "buffer_size", "learning_starts", "n_quantiles",
            "n_critics", "top_quantiles_to_drop_per_net",
            "policy_noise", "noise_clip", "ent_coef",
        ]
        self._lbl_dropdown(g, "Parameter", 1, self._var_sweep_param,
                           sweep_params, width=22)

        # Ziel-Wert
        self._var_sweep_value = tk.StringVar(value="0.001")
        self._lbl_entry(g, "Value", 2, self._var_sweep_value, width=12)

        # Buttons
        btn_frame = ttk.Frame(g)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Button(btn_frame, text="+ Job hinzufügen",
                   command=self._on_add_job).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✕ Entfernen",
                   command=self._on_remove_job).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Alle leeren",
                   command=self._on_clear_jobs).pack(side=tk.LEFT, padx=2)

        # Job-Liste
        list_frame = ttk.Frame(g)
        list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=4)
        g.rowconfigure(4, weight=1)

        sb_job = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        sb_job.pack(side=tk.RIGHT, fill=tk.Y)
        self._job_listbox = tk.Listbox(list_frame, font=GUI_FONT_MONO,
                                       height=6, selectmode=tk.SINGLE,
                                       yscrollcommand=sb_job.set,
                                       bg="#fafafa", fg="#222222")
        self._job_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_job.config(command=self._job_listbox.yview)

    # ------------------------------------------------------------------
    # 4.3 Control Bar
    # ------------------------------------------------------------------

    def _build_control_bar(self) -> None:
        bar = ttk.Frame(self._middle_frame)
        bar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        # Run-Modus-Selektor
        mode_frame = ttk.LabelFrame(bar, text="Run Mode", padding=2)
        mode_frame.pack(side=tk.LEFT, padx=4)
        for text, value in [("Single", "single"), ("Compare", "compare"), ("Sweep", "sweep")]:
            ttk.Radiobutton(mode_frame, text=text, variable=self._run_mode_var,
                            value=value).pack(side=tk.LEFT, padx=4)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # Haupt-Buttons
        self._btn_start = ttk.Button(bar, text="▶ Start", command=self._on_start)
        self._btn_start.pack(side=tk.LEFT, padx=2)

        self._btn_pause = ttk.Button(bar, text="⏸ Pause", command=self._on_pause,
                                     state=tk.DISABLED)
        self._btn_pause.pack(side=tk.LEFT, padx=2)

        self._btn_resume = ttk.Button(bar, text="▶▶ Resume", command=self._on_resume,
                                      state=tk.DISABLED)
        self._btn_resume.pack(side=tk.LEFT, padx=2)

        self._btn_cancel = ttk.Button(bar, text="⏹ Cancel", command=self._on_cancel,
                                      state=tk.DISABLED)
        self._btn_cancel.pack(side=tk.LEFT, padx=2)

        self._btn_reset = ttk.Button(bar, text="↺ Reset", command=self._on_reset)
        self._btn_reset.pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self._btn_save = ttk.Button(bar, text="💾 Save Config", command=self._on_save_config)
        self._btn_save.pack(side=tk.LEFT, padx=2)

        self._btn_load = ttk.Button(bar, text="📂 Load Config", command=self._on_load_config)
        self._btn_load.pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self._btn_anim_win = ttk.Button(bar, text="🎬 Animation Window",
                                        command=self._open_animation_window,
                                        state=tk.DISABLED)
        self._btn_anim_win.pack(side=tk.LEFT, padx=2)

        self._btn_export = ttk.Button(bar, text="📊 Export Plot",
                                      command=self._on_export_plot,
                                      state=tk.DISABLED)
        self._btn_export.pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # 4.4 Current-Run-Panel
    # ------------------------------------------------------------------

    def _build_current_run_panel(self) -> None:
        panel = ttk.LabelFrame(self._middle_frame, text="Current Run", padding=4)
        panel.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        # 4-spaltiges Status-Grid
        grid = ttk.Frame(panel)
        grid.pack(fill=tk.X, expand=True)
        for c in range(8):
            grid.columnconfigure(c, weight=1)

        def _field(label: str, row: int, col: int) -> tk.StringVar:
            ttk.Label(grid, text=label + ":", font=GUI_FONT_BOLD,
                      anchor="e").grid(row=row, column=col * 2,
                                       sticky="e", padx=(6, 2), pady=1)
            var = tk.StringVar(value="—")
            ttk.Label(grid, textvariable=var, font=GUI_FONT_MONO,
                      anchor="w", foreground="#1a1a2e").grid(
                          row=row, column=col * 2 + 1,
                          sticky="w", padx=(0, 8), pady=1)
            return var

        # Zeile 0
        self._var_status       = _field("Status",      0, 0)
        self._var_episode      = _field("Episode",     0, 1)
        self._var_step_reward  = _field("Step Reward", 0, 2)
        self._var_ep_reward    = _field("Ep. Reward",  0, 3)
        # Zeile 1
        self._var_moving_avg   = _field("Moving Avg",  1, 0)
        self._var_best_reward  = _field("Best Reward", 1, 1)
        self._var_total_steps  = _field("Total Steps", 1, 2)
        self._var_ep_steps     = _field("Ep. Steps",   1, 3)
        # Zeile 2
        self._var_active_algo  = _field("Active Algo", 2, 0)
        self._var_conf_algo    = _field("Config Algo", 2, 1)
        self._var_message      = _field("Message",     2, 2)
        self._var_anim_state   = _field("Animation",   2, 3)

        # Details-Button (öffnet StatusPopup)
        ttk.Button(panel, text="Details…",
                   command=self._show_status_popup).pack(side=tk.RIGHT, padx=4)

        # Progressbar
        self._progressbar = ttk.Progressbar(panel, orient=tk.HORIZONTAL,
                                            mode="indeterminate", length=200)
        self._progressbar.pack(fill=tk.X, padx=4, pady=(4, 0))

    def _show_status_popup(self) -> None:
        if self._status_popup is None:
            self._status_popup = StatusPopup(self)
        self._status_popup.update_data(
            self._last_session_id, self._last_run_id,
            self._last_update, self._last_completion)
        self._status_popup.deiconify()
        self._status_popup.lift()

    # ------------------------------------------------------------------
    # 4.5 Live-Plot
    # ------------------------------------------------------------------

    def _build_live_plot(self) -> None:
        self._fig, self._ax = plt.subplots(figsize=(10, 3))
        self._fig.patch.set_facecolor(THEME["bg"])
        self._init_plot()

        self._canvas_plot = FigureCanvasTkAgg(self._fig, master=self._plot_frame)
        self._canvas_plot.draw()
        self._canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _init_plot(self) -> None:
        ax = self._ax
        ax.set_facecolor(THEME["axes_bg"])
        ax.tick_params(colors=THEME["tick"])
        ax.xaxis.label.set_color(THEME["label"])
        ax.yaxis.label.set_color(THEME["label"])
        ax.spines[:].set_color("#cccccc")
        ax.grid(color=THEME["grid"], linestyle="--", alpha=0.5)
        ax.set_xlabel("Episode", color=THEME["label"])
        ax.set_ylabel("Reward", color=THEME["label"])
        ax.set_title("Live Reward — InvertedDoublePendulum-v5",
                     color=THEME["label"])
        # Reward-Threshold-Linie
        ax.axhline(y=REWARD_THRESHOLD, color=THEME["threshold"],
                   linestyle="--", alpha=0.7, linewidth=1.5,
                   label=f"Solved ({REWARD_THRESHOLD})")
        ax.legend(facecolor=THEME["legend_face"],
                  edgecolor=THEME["legend_edge"],
                  labelcolor=THEME["legend_text"],
                  loc="upper left", fontsize=8)

    def _clear_plot(self) -> None:
        self._ax.cla()
        self._plot_data.clear()
        self._plot_lines.clear()
        self._plot_dirty = False
        self._init_plot()
        self._canvas_plot.draw()

    def _update_plot(self, event: Dict[str, Any]) -> None:
        """Fügt einen Episoden-Datenpunkt zum Plot hinzu (inkrementell)."""
        run_id = event.get("run_id", "unknown")
        algo = event.get("display_label") or event.get("algorithm_name", "?")
        reward = event.get("reward", 0.0)
        ma = event.get("moving_average", 0.0)
        ep = event.get("episode", 1)

        if run_id not in self._plot_data:
            self._plot_data[run_id] = {"episodes": [], "rewards": [], "ma": []}
            # Farbe bestimmen
            idx = len(self._plot_data) - 1
            color = ALGO_COLORS[idx % len(ALGO_COLORS)]
            raw_line, = self._ax.plot(
                [], [], color=color, alpha=0.3, linewidth=1.0,
                label=f"{algo} (raw)")
            ma_line, = self._ax.plot(
                [], [], color=color, alpha=1.0, linewidth=2.5,
                label=f"{algo} (MA)")
            self._plot_lines[run_id] = {"raw": raw_line, "ma": ma_line}
            self._ax.legend(facecolor=THEME["legend_face"],
                            edgecolor=THEME["legend_edge"],
                            labelcolor=THEME["legend_text"],
                            loc="upper left", fontsize=8)

        d = self._plot_data[run_id]
        d["episodes"].append(ep)
        d["rewards"].append(reward)
        d["ma"].append(ma)

        lines = self._plot_lines[run_id]
        lines["raw"].set_data(d["episodes"], d["rewards"])
        lines["ma"].set_data(d["episodes"], d["ma"])

        self._ax.relim()
        self._ax.autoscale_view()
        self._plot_dirty = True
        self._throttled_redraw()

    def _throttled_redraw(self) -> None:
        now = time.monotonic()
        if now - self._last_redraw_time >= PLOT_REDRAW_INTERVAL_MS / 1000.0:
            self._canvas_plot.draw_idle()
            self._last_redraw_time = now
            self._plot_dirty = False

    # ------------------------------------------------------------------
    # 4.6 Event-Pump
    # ------------------------------------------------------------------

    def _pump_events(self) -> None:
        """Verarbeitet max. PUMP_BATCH_SIZE Events pro Takt aus der Queue."""
        processed = 0
        while processed < PUMP_BATCH_SIZE:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break

            # Session-Filterung
            if event.get("session_id") != self._session_id:
                processed += 1
                continue

            etype = event.get("type", "")
            if etype == "episode":
                self._handle_episode(event)
            elif etype == "episode_aux":
                self._handle_episode_aux(event)
            elif etype == "training_done":
                self._handle_training_done(event)
            elif etype == "error":
                self._handle_error(event)

            processed += 1

        # Ausstehender Redraw
        if self._plot_dirty:
            self._throttled_redraw()

        self.after(PUMP_INTERVAL_MS, self._pump_events)

    def _handle_episode(self, e: Dict[str, Any]) -> None:
        algo = e.get("display_label") or e.get("algorithm_name", "?")
        ep = e.get("episode", 0)
        ep_total = e.get("episodes", 0)
        reward = e.get("reward", 0.0)
        ma = e.get("moving_average", 0.0)
        best = e.get("best_reward", 0.0)
        total_steps = e.get("total_steps", 0)
        ep_steps = e.get("steps", 0)
        msg = e.get("message") or ""

        self._last_run_id = e.get("run_id", "")
        self._last_update = datetime.now().strftime("%H:%M:%S")

        self._var_status.set("running")
        self._var_episode.set(f"{ep}" + (f"/{ep_total}" if ep_total > 0 else ""))
        self._var_ep_reward.set(f"{reward:.2f}")
        self._var_moving_avg.set(f"{ma:.2f}")
        self._var_best_reward.set(f"{best:.2f}")
        self._var_total_steps.set(str(total_steps))
        self._var_ep_steps.set(str(ep_steps))
        self._var_active_algo.set(algo)
        self._var_message.set(msg if msg else "—")
        self._var_anim_state.set("on" if self._var_animation.get() else "off")

        # Progressbar
        ts_limit = self._var_total_timesteps.get()
        ep_limit = ep_total
        if ep_limit > 0:
            val = min(100.0, (ep / ep_limit) * 100)
            self._progressbar.configure(mode="determinate", value=val)
        elif ts_limit > 0:
            val = min(100.0, (total_steps / ts_limit) * 100)
            self._progressbar.configure(mode="determinate", value=val)
        else:
            if self._progressbar["mode"] != "indeterminate":
                self._progressbar.configure(mode="indeterminate")
                self._progressbar.start(10)

        # Compare: Maximum aller Worker für Progressbar
        if self._run_mode_var.get() == "compare":
            # Fortschritt = Maximum der bekannten run_id-Fortschritte
            pass  # Inkrementell über episode-Events aus allen Workern

        self._update_plot(e)

    def _handle_episode_aux(self, e: Dict[str, Any]) -> None:
        """Verarbeitet schwere Payloads: Frames und Eval-Punkte."""
        frames = e.get("frames")
        if frames and self._var_animation.get():
            frame = frames[-1]
            if self._anim_window is not None:
                try:
                    self._anim_window.update_frame(frame)
                except tk.TclError:
                    self._anim_window = None

    def _handle_training_done(self, e: Dict[str, Any]) -> None:
        reason = e.get("completion_reason", "finished")
        algo = e.get("display_label") or e.get("algorithm_name", "?")
        best = e.get("best_reward")
        msg = e.get("message", "")

        self._last_completion = reason
        self._last_update = datetime.now().strftime("%H:%M:%S")

        status_map = {
            "finished": "completed",
            "cancel_requested": "cancelled",
            "error": "failed",
            "early_stop": "completed",
        }
        ui_status = status_map.get(reason, "completed")

        self._var_status.set(ui_status)
        self._var_active_algo.set(algo)
        if best is not None:
            self._var_best_reward.set(f"{best:.2f}")
        if msg:
            self._var_message.set(msg)

        # Progressbar einfrieren
        if self._progressbar["mode"] == "indeterminate":
            self._progressbar.stop()
        self._progressbar.configure(mode="determinate",
                                    value=100 if reason == "finished" else
                                    self._progressbar["value"])

        # Kein aktiver Trainer mehr? → Buttons zurücksetzen
        if not self._orchestrator.has_active_trainers():
            self._update_button_states(ui_status)
            self._btn_export.configure(state=tk.NORMAL)

        # Export-Pfade anzeigen
        export_paths = e.get("export_paths", {})
        if export_paths:
            paths_str = "\n".join(f"  {k}: {v}" for k, v in export_paths.items())
            self._var_message.set(f"Gespeichert: {paths_str}")

    def _handle_error(self, e: Dict[str, Any]) -> None:
        stage = e.get("error_stage", "?")
        msg = e.get("error_message", "Unbekannter Fehler")
        details = e.get("traceback", "")

        self._var_status.set("ERROR")
        self._var_message.set(f"[{stage}] {msg}")

        if stage == "env_build":
            self._update_button_states(STATE_IDLE)
            messagebox.showerror(
                "Environment-Fehler",
                f"Umgebung konnte nicht gestartet werden: {msg}\nBitte Konfiguration prüfen und erneut starten.")
        else:
            messagebox.showerror(
                f"Fehler: {stage}",
                f"{msg} {details[:400] if details else ''}")

    # ------------------------------------------------------------------
    # 4.7 Run-Modus Handler
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        if not self._validate_before_start():
            return
        mode = self._run_mode_var.get()
        self._session_id = str(uuid.uuid4())
        self._last_session_id = self._session_id
        self._plot_data.clear()
        self._plot_lines.clear()
        self._clear_plot()
        self._update_button_states(STATE_RUNNING)
        self._progressbar.configure(mode="indeterminate", value=0)
        self._progressbar.start(10)

        if self._var_animation.get():
            self._open_animation_window()

        if mode == "single":
            self._start_single()
        elif mode == "compare":
            self._start_compare()
        elif mode == "sweep":
            self._start_sweep()

    def _start_single(self) -> None:
        tab = self._algo_notebook.index(self._algo_notebook.select())
        algo = SUPPORTED_ALGORITHMS[tab]
        config = self._get_algo_config(algo)
        config["session_id"] = self._session_id
        self._var_conf_algo.set(algo)
        self._orchestrator.run_single(config, self._event_queue, self._session_id)

    def _start_compare(self) -> None:
        configs = []
        for algo in SUPPORTED_ALGORITHMS:
            cfg = self._get_algo_config(algo)
            cfg["session_id"] = self._session_id
            configs.append(cfg)
        self._var_conf_algo.set("SAC | TD3 | TQC")
        self._orchestrator.run_compare(configs, self._event_queue, self._session_id)

    def _start_sweep(self) -> None:
        if not self._job_list:
            messagebox.showwarning("Sweep", "Die Job List ist leer.")
            self._update_button_states(STATE_IDLE)
            return
        base_config = self._get_common_config()
        base_config["session_id"] = self._session_id
        self._var_conf_algo.set("Sweep")
        self._orchestrator.run_sweep(
            self._job_list, base_config,
            self._event_queue, self._session_id)

    def _on_pause(self) -> None:
        self._orchestrator.pause_all()
        self._update_button_states(STATE_PAUSED)
        self._var_status.set("paused")
        if self._progressbar["mode"] == "indeterminate":
            self._progressbar.stop()

    def _on_resume(self) -> None:
        self._orchestrator.resume_all()
        self._update_button_states(STATE_RUNNING)
        self._var_status.set("running")
        if self._progressbar["mode"] == "indeterminate":
            self._progressbar.start(10)

    def _on_cancel(self) -> None:
        self._orchestrator.cancel_all()
        self._update_button_states(STATE_CANCELLED)
        self._var_status.set("cancelled")
        if self._progressbar["mode"] == "indeterminate":
            self._progressbar.stop()

    def _on_reset(self) -> None:
        if self._orchestrator.has_active_trainers():
            if not messagebox.askyesno(
                    "Reset", "Laufendes Training abbrechen und zurücksetzen?"):
                return
            self._orchestrator.cancel_all()

        self._set_initial_state()
        self._clear_plot()
        self._job_list.clear()
        self._job_listbox.delete(0, tk.END)
        self._var_status.set("idle")
        self._var_episode.set("—")
        self._var_ep_reward.set("—")
        self._var_moving_avg.set("—")
        self._var_best_reward.set("—")
        self._var_total_steps.set("—")
        self._var_ep_steps.set("—")
        self._var_active_algo.set("—")
        self._var_message.set("—")
        self._var_step_reward.set("—")
        self._progressbar.stop()
        self._progressbar.configure(mode="determinate", value=0)

    # ------------------------------------------------------------------
    # 4.8 Config Save / Load
    # ------------------------------------------------------------------

    def _collect_config_state(self) -> Dict[str, Any]:
        tab = self._algo_notebook.index(self._algo_notebook.select())
        algo = SUPPORTED_ALGORITHMS[tab]
        state = {
            "algorithm_name": algo,
            "animation_enabled": self._var_animation.get(),
            "frame_interval": self._var_frame_interval.get(),
            "healthy_reward": self._var_healthy_reward.get(),
            "reset_noise_scale": self._var_reset_noise.get(),
            "total_timesteps": self._var_total_timesteps.get(),
            "total_episodes": self._var_total_episodes.get(),
            "eval_interval": self._var_eval_interval.get(),
            "eval_episodes": self._var_eval_episodes.get(),
            "moving_average_window": self._var_ma_window.get(),
            "seed": self._var_seed.get(),
            "use_gpu": self._var_use_gpu.get(),
            "gamma": self._var_gamma.get(),
            "tau": self._var_tau.get(),
            "buffer_size": self._var_buffer_size.get(),
            "batch_size": self._var_batch_size.get(),
            "learning_starts": self._var_learning_starts.get(),
            "net_arch": self._var_net_arch.get(),
            "learning_rate_schedule": self._var_lr_schedule.get(),
            # SAC
            "sac_learning_rate": self._var_sac_lr.get(),
            "sac_ent_coef": self._var_sac_ent_coef.get(),
            # TD3
            "td3_learning_rate": self._var_td3_lr.get(),
            "td3_policy_delay": self._var_td3_policy_delay.get(),
            "td3_policy_noise": self._var_td3_policy_noise.get(),
            "td3_noise_clip": self._var_td3_noise_clip.get(),
            # TQC
            "tqc_learning_rate": self._var_tqc_lr.get(),
            "tqc_n_quantiles": self._var_tqc_n_quantiles.get(),
            "tqc_n_critics": self._var_tqc_n_critics.get(),
            "tqc_top_quantiles_to_drop_per_net": self._var_tqc_drop.get(),
            "tqc_ent_coef": self._var_tqc_ent_coef.get(),
            # Job List
            "job_list": list(self._job_list),
            "run_mode": self._run_mode_var.get(),
        }
        return state

    def _apply_config_state(self, cfg: Dict[str, Any]) -> None:
        def _set(var, key, default=None):
            val = cfg.get(key, default)
            if val is not None:
                try:
                    var.set(val)
                except Exception:
                    pass

        _set(self._var_animation,        "animation_enabled", False)
        _set(self._var_frame_interval,   "frame_interval", 10)
        _set(self._var_healthy_reward,   "healthy_reward", 10.0)
        _set(self._var_reset_noise,      "reset_noise_scale", 0.1)
        _set(self._var_total_timesteps,  "total_timesteps", 500_000)
        _set(self._var_total_episodes,   "total_episodes", 0)
        _set(self._var_eval_interval,    "eval_interval", 10)
        _set(self._var_eval_episodes,    "eval_episodes", 5)
        _set(self._var_ma_window,        "moving_average_window", 20)
        _set(self._var_seed,             "seed", 42)
        _set(self._var_use_gpu,          "use_gpu", False)
        _set(self._var_gamma,            "gamma", 0.99)
        _set(self._var_tau,              "tau", 0.005)
        _set(self._var_buffer_size,      "buffer_size", 1_000_000)
        _set(self._var_batch_size,       "batch_size", 256)
        _set(self._var_learning_starts,  "learning_starts", 1000)
        _set(self._var_net_arch,         "net_arch", "[256, 256]")
        _set(self._var_lr_schedule,      "learning_rate_schedule", "constant")
        _set(self._var_sac_lr,           "sac_learning_rate", 0.0003)
        _set(self._var_sac_ent_coef,     "sac_ent_coef", "auto")
        _set(self._var_td3_lr,           "td3_learning_rate", 0.0003)
        _set(self._var_td3_policy_delay, "td3_policy_delay", 2)
        _set(self._var_td3_policy_noise, "td3_policy_noise", 0.15)
        _set(self._var_td3_noise_clip,   "td3_noise_clip", 0.5)
        _set(self._var_tqc_lr,           "tqc_learning_rate", 0.001)
        _set(self._var_tqc_n_quantiles,  "tqc_n_quantiles", 25)
        _set(self._var_tqc_n_critics,    "tqc_n_critics", 2)
        _set(self._var_tqc_drop,         "tqc_top_quantiles_to_drop_per_net", 2)
        _set(self._var_tqc_ent_coef,     "tqc_ent_coef", "auto")
        _set(self._run_mode_var,         "run_mode", "single")

        # Job List
        jobs = cfg.get("job_list", [])
        self._job_list = list(jobs)
        self._job_listbox.delete(0, tk.END)
        for job in self._job_list:
            self._job_listbox.insert(
                tk.END,
                f"{job.get('algorithm_name','?')} | "
                f"{job.get('parameter','?')} = {job.get('value','?')}")

        # Algo-Tab setzen
        algo = cfg.get("algorithm_name", "SAC")
        if algo in SUPPORTED_ALGORITHMS:
            idx = SUPPORTED_ALGORITHMS.index(algo)
            self._algo_notebook.select(idx)

    def _on_save_config(self) -> None:
        state = self._collect_config_state()
        filename = ConfigState.generate_filename()
        path = filedialog.asksaveasfilename(
            initialdir=ConfigState.CONFIG_DIR,
            initialfile=filename,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Konfiguration speichern")
        if not path:
            return
        try:
            ConfigState.save(os.path.basename(path), state)
            messagebox.showinfo("Gespeichert", f"Konfiguration gespeichert: {path}")
        except Exception as exc:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen: {exc}")

    def _on_load_config(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=ConfigState.CONFIG_DIR,
            filetypes=[("JSON", "*.json")],
            title="Konfiguration laden")
        if not path:
            return
        try:
            cfg = ConfigState.load(path)
            self._apply_config_state(cfg)
            messagebox.showinfo("Geladen", f"Konfiguration geladen: {path}")
        except Exception as exc:
            messagebox.showerror("Fehler", f"Laden fehlgeschlagen: {exc}")

    # ------------------------------------------------------------------
    # 4.9 Sweep / Job List
    # ------------------------------------------------------------------

    def _on_add_job(self) -> None:
        algo = self._var_sweep_algo.get()
        param = self._var_sweep_param.get()
        value = self._var_sweep_value.get().strip()
        if not value:
            messagebox.showwarning("Job", "Bitte einen Wert eingeben.")
            return
        job = {
            "algorithm_name": algo,
            "parameter": param,
            "value": value,
            "display_label": f"{algo} {param}={value}",
        }
        self._job_list.append(job)
        self._job_listbox.insert(
            tk.END, f"{algo} | {param} = {value}")

    def _on_remove_job(self) -> None:
        sel = self._job_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._job_listbox.delete(idx)
        del self._job_list[idx]

    def _on_clear_jobs(self) -> None:
        self._job_list.clear()
        self._job_listbox.delete(0, tk.END)

    # ------------------------------------------------------------------
    # 4.10 Validierung & Hilfsmethoden
    # ------------------------------------------------------------------

    def _validate_before_start(self) -> bool:
        tab = self._algo_notebook.index(self._algo_notebook.select())
        algo = SUPPORTED_ALGORITHMS[tab]
        config = self._get_algo_config(algo)
        messages = validate_config(config)
        errors   = [m for m in messages if m.startswith("ERROR:")]
        warnings = [m for m in messages if m.startswith("WARNING:")]

        if errors:
            messagebox.showerror("Konfigurationsfehler",
                                 "\n".join(e[7:] for e in errors))
            return False
        if warnings:
            warn_text = "\n".join(w[9:] for w in warnings)
            if not messagebox.askyesno(
                    "Warnung", warn_text + "\n\nTrotzdem starten?"):
                return False
        return True

    def _get_common_config(self) -> Dict[str, Any]:
        """Gemeinsame Hyperparameter aus dem GUI-Zustand."""
        return {
            "animation_enabled": self._var_animation.get(),
            "frame_interval": self._var_frame_interval.get(),
            "healthy_reward": self._var_healthy_reward.get(),
            "reset_noise_scale": self._var_reset_noise.get(),
            "total_timesteps": self._var_total_timesteps.get(),
            "total_episodes": self._var_total_episodes.get(),
            "eval_interval": self._var_eval_interval.get(),
            "eval_episodes": self._var_eval_episodes.get(),
            "moving_average_window": self._var_ma_window.get(),
            "seed": self._var_seed.get(),
            "use_gpu": self._var_use_gpu.get(),
            "gamma": self._var_gamma.get(),
            "tau": self._var_tau.get(),
            "buffer_size": self._var_buffer_size.get(),
            "batch_size": self._var_batch_size.get(),
            "learning_starts": self._var_learning_starts.get(),
            "net_arch": self._var_net_arch.get(),
            "learning_rate_schedule": self._var_lr_schedule.get(),
        }

    def _get_algo_config(self, algo: str) -> Dict[str, Any]:
        """Vollständige Config für einen Algorithmus (common + algo-spezifisch)."""
        cfg = self._get_common_config()
        cfg["algorithm_name"] = algo

        if algo == "SAC":
            cfg["learning_rate"] = self._var_sac_lr.get()
            cfg["ent_coef"] = self._var_sac_ent_coef.get()

        elif algo == "TD3":
            cfg["learning_rate"] = self._var_td3_lr.get()
            cfg["policy_delay"] = self._var_td3_policy_delay.get()
            cfg["policy_noise"] = self._var_td3_policy_noise.get()
            cfg["noise_clip"] = self._var_td3_noise_clip.get()

        elif algo == "TQC":
            cfg["learning_rate"] = self._var_tqc_lr.get()
            cfg["n_quantiles"] = self._var_tqc_n_quantiles.get()
            cfg["n_critics"] = self._var_tqc_n_critics.get()
            cfg["top_quantiles_to_drop_per_net"] = self._var_tqc_drop.get()
            cfg["ent_coef"] = self._var_tqc_ent_coef.get()

        return cfg

    def _update_button_states(self, state: str) -> None:
        """Setzt alle Button-Zustände konsistent je nach UI-State."""
        self._ui_state = state
        is_idle      = state in (STATE_IDLE, STATE_COMPLETED, STATE_CANCELLED)
        is_running   = state == STATE_RUNNING
        is_paused    = state == STATE_PAUSED

        self._btn_start.configure( state=tk.NORMAL   if is_idle    else tk.DISABLED)
        self._btn_pause.configure( state=tk.NORMAL   if is_running  else tk.DISABLED)
        self._btn_resume.configure(state=tk.NORMAL   if is_paused   else tk.DISABLED)
        self._btn_cancel.configure(state=tk.NORMAL   if (is_running or is_paused) else tk.DISABLED)
        self._btn_reset.configure( state=tk.NORMAL   if is_idle     else tk.DISABLED)
        self._btn_save.configure(  state=tk.NORMAL   if is_idle     else tk.DISABLED)
        self._btn_load.configure(  state=tk.NORMAL   if is_idle     else tk.DISABLED)

        # Animation und GPU: Startkonfiguration — während Run sperren
        anim_state = tk.DISABLED if (is_running or is_paused) else tk.NORMAL
        self._cb_animation.configure(state=anim_state)
        self._cb_use_gpu.configure(state=anim_state)

        # Animation-Window-Button
        anim_enabled = self._var_animation.get()
        self._btn_anim_win.configure(
            state=tk.NORMAL if anim_enabled else tk.DISABLED)

    def _set_initial_state(self) -> None:
        """Setzt GUI in den Initialzustand zurück."""
        self._update_button_states(STATE_IDLE)
        self._btn_export.configure(state=tk.DISABLED)
        self._var_status.set("idle")
        self._var_anim_state.set("off")
        self._sb_frame_interval.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # 4.11 Teardown & Export
    # ------------------------------------------------------------------

    def _on_closing(self) -> None:
        """Stoppt alle Worker sauber vor dem Beenden."""
        if self._orchestrator.has_active_trainers():
            if not messagebox.askyesno(
                    "Beenden", "Training läuft noch. Wirklich beenden?"):
                return
            self._orchestrator.cancel_all()
            time.sleep(0.3)
        plt.close("all")
        self.destroy()

    def _on_export_plot(self) -> None:
        """Exportiert den Live-Plot als PNG nach plots/."""
        if not self._plot_data:
            messagebox.showinfo("Export", "Keine Plotdaten vorhanden.")
            return
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(ExportHelper.PLOTS_DIR, exist_ok=True)
            filename = f"inverted_double_pendulum_plot_{ts}.png"
            path = os.path.join(ExportHelper.PLOTS_DIR, filename)
            self._fig.savefig(path, dpi=150, facecolor=THEME["bg"],
                              bbox_inches="tight")
            messagebox.showinfo("Export", f"Plot gespeichert: {path}")
        except Exception as exc:
            messagebox.showerror("Export-Fehler", str(exc))


# =============================================================================
# SECTION 5: Einstiegspunkt
# =============================================================================

def main() -> None:
    app = IDPApp()
    app.mainloop()


if __name__ == "__main__":
    main()
