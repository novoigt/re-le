"""
inverted_double_pendulum_app.py
Einstiegspunkt für das Projekt "Inverted Double Pendulum"
Workbench v2.0 — Bootstrap, Logging, Verzeichnisse, CLI
"""

# =============================================================================
# SECTION 1: Imports
# =============================================================================

from __future__ import annotations

import argparse
import logging
import os
import queue
import sys
import time
import uuid
from pathlib import Path

# =============================================================================
# SECTION 2: Projektkonstanten
# =============================================================================

PROJECT_NAME    = "inverted_double_pendulum"
PROJECT_VERSION = "1.0.0"

PROJECT_DIRS = [
    "plots",
    "configs",
    "models",
    "results_csv",
    "logs",
    "tests",
]

LOG_FILE = os.path.join("logs", f"{PROJECT_NAME}.log")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# =============================================================================
# SECTION 3: Logging-Setup
# =============================================================================

def setup_logging(level_name: str = "INFO") -> None:
    """
    Konfiguriert Dual-Logging:
    - FileHandler  → logs/inverted_double_pendulum.log
    - StreamHandler → stderr
    Level ist per CLI konfigurierbar.
    """
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # StreamHandler (stderr)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # FileHandler (logs/)
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as exc:
        # Logdatei nicht erreichbar → nur stderr, kein Abbruch
        logging.warning("Log-Datei konnte nicht geöffnet werden: %s", exc)

    logging.info(
        "%s v%s — Logging initialisiert (Level: %s)",
        PROJECT_NAME, PROJECT_VERSION, level_name.upper()
    )


# =============================================================================
# SECTION 4: Verzeichnis-Bootstrap
# =============================================================================

def ensure_project_dirs() -> None:
    """
    Legt alle Pflichtverzeichnisse an, sofern nicht vorhanden.
    Bricht mit sauberer Fehlermeldung ab, wenn ein Verzeichnis
    nicht erstellt werden kann.
    """
    for dir_name in PROJECT_DIRS:
        try:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(
                f"[FEHLER] Verzeichnis '{dir_name}' konnte nicht erstellt werden: {exc} " "Bitte Schreibrechte prüfen.",
                file=sys.stderr,
            )
            sys.exit(1)


# =============================================================================
# SECTION 5: CLI-Argument-Parser
# =============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    """Erstellt den CLI-Argument-Parser für inverted_double_pendulum_app.py."""
    parser = argparse.ArgumentParser(
        prog=f"{PROJECT_NAME}_app",
        description=(
            f"{PROJECT_NAME} v{PROJECT_VERSION} -"
            "RL-Workbench für InvertedDoublePendulum-v5 (SAC, TD3, TQC)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PROJECT_VERSION}",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Headless-Modus starten (kein GUI; für Tests / CI-Umgebungen).",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log-Level (default: INFO).",
    )
    parser.add_argument(
        "--config",
        dest="config",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Pfad zu einer gespeicherten Konfigurationsdatei (JSON). "
            "Wird beim GUI-Start automatisch geladen."
        ),
    )
    return parser


# =============================================================================
# SECTION 6: Headless-Stub
# =============================================================================

def run_headless(args: argparse.Namespace) -> int:
    """
    Führt einen minimalen Smoke-Run headless durch (kein GUI).
    Geeignet für CI-Umgebungen und automatisierte Tests.
    Gibt Exit-Code 0 bei Erfolg, 1 bei Fehler zurück.
    """
    logger = logging.getLogger(f"{PROJECT_NAME}.headless")
    logger.info("Headless-Modus gestartet.")

    try:
        from inverted_double_pendulum_logic import (
            IDPTrainer,
            ConfigState,
            validate_config,
        )
    except ImportError as exc:
        logger.error("Import von inverted_double_pendulum_logic fehlgeschlagen: %s", exc)
        return 1

    # Basis-Konfiguration für Smoke-Run
    base_config: dict = {
        "algorithm_name": "SAC",
        "animation_enabled": False,
        "total_timesteps": 1000,
        "total_episodes": 2,
        "eval_interval": 1,
        "eval_episodes": 1,
        "moving_average_window": 2,
        "seed": 42,
        "use_gpu": False,
        "gamma": 0.99,
        "tau": 0.005,
        "buffer_size": 10_000,
        "batch_size": 64,
        "learning_starts": 100,
        "net_arch": "[64, 64]",
        "learning_rate_schedule": "constant",
        "learning_rate": 0.0003,
        "ent_coef": "auto",
        "healthy_reward": 10.0,
        "reset_noise_scale": 0.1,
        "display_label": "SAC (headless smoke)",
    }

    # Optionale Config aus Datei laden
    if args.config:
        try:
            loaded = ConfigState.load(args.config)
            base_config.update(loaded)
            logger.info("Konfiguration geladen aus: %s", args.config)
        except Exception as exc:
            logger.warning("Konfiguration konnte nicht geladen werden: %s", exc)

    # Validierung
    messages = validate_config(base_config)
    for msg in messages:
        if msg.startswith("ERROR:"):
            logger.error("Konfigurationsfehler: %s", msg)
            return 1
        else:
            logger.warning("Konfigurationswarnung: %s", msg)

    # Lokale Queue für Events
    event_queue: queue.Queue = queue.Queue()
    session_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    trainer = IDPTrainer(
        config=base_config,
        event_queue=event_queue,
        run_id=run_id,
        session_id=session_id,
        run_mode="single_run",
    )

    # Training in aktuellem Thread (headless = kein GUI-Thread nötig)
    import threading
    done_event = threading.Event()
    exit_code_holder = [0]

    def _train():
        try:
            trainer.train()
        except Exception as exc:
            logger.error("Training fehlgeschlagen: %s", exc)
            exit_code_holder[0] = 1
        finally:
            done_event.set()

    t = threading.Thread(target=_train, daemon=False)
    t.start()

    # Events konsumieren bis training_done
    timeout = 120.0
    start = time.monotonic()
    training_done_received = False

    while not training_done_received:
        if time.monotonic() - start > timeout:
            logger.error("Headless-Timeout nach %.0f Sekunden.", timeout)
            trainer.cancel()
            exit_code_holder[0] = 1
            break
        try:
            event = event_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        etype = event.get("type", "")
        if etype == "episode":
            ep = event.get("episode", "?")
            reward = event.get("reward", 0.0)
            logger.info(
                "Episode %s | Reward: %.4f | MA: %.4f",
                ep, reward, event.get("moving_average", 0.0)
            )
        elif etype == "training_done":
            reason = event.get("completion_reason", "?")
            best = event.get("best_reward", "?")
            logger.info(
                "training_done | reason=%s | best_reward=%s", reason, best
            )
            if reason == "error":
                exit_code_holder[0] = 1
            training_done_received = True
        elif etype == "error":
            logger.error(
                "[%s] %s",
                event.get("error_stage", "?"),
                event.get("error_message", "?"),
            )
            exit_code_holder[0] = 1

    done_event.wait(timeout=10.0)
    t.join(timeout=10.0)

    if exit_code_holder[0] == 0:
        logger.info("Headless Smoke-Run erfolgreich abgeschlossen.")
    else:
        logger.error("Headless Smoke-Run mit Fehler beendet.")

    return exit_code_holder[0]


# =============================================================================
# SECTION 7: Einstiegspunkt
# =============================================================================

def main() -> None:
    """
    Haupt-Einstiegspunkt für inverted_double_pendulum_app.py.

    Reihenfolge:
    1. CLI-Argumente parsen
    2. Pflichtverzeichnisse anlegen
    3. Logging initialisieren
    4. Headless-Modus → run_headless(); sys.exit()
    5. GUI-Modus → inverted_double_pendulum_ui.main()
    """
    parser = build_arg_parser()
    args = parser.parse_args()

    # Verzeichnisse zuerst (Logging braucht logs/)
    ensure_project_dirs()

    # Logging
    setup_logging(args.log_level)
    logger = logging.getLogger(PROJECT_NAME)

    # Optionale Config-Datei per Env-Variable an UI weitergeben
    if args.config:
        if not os.path.isfile(args.config):
            logger.error("Konfigurationsdatei nicht gefunden: %s", args.config)
            sys.exit(1)
        os.environ["IDP_LOAD_CONFIG"] = os.path.abspath(args.config)
        logger.info("Konfigurationsdatei vorgemerkt: %s", args.config)

    # Headless-Modus
    if args.headless:
        logger.info("Starte im Headless-Modus.")
        exit_code = run_headless(args)
        sys.exit(exit_code)

    # GUI-Modus
    logger.info("Starte GUI.")
    try:
        from inverted_double_pendulum_ui import main as ui_main
        ui_main()
    except ImportError as exc:
        logger.critical(
            "inverted_double_pendulum_ui konnte nicht importiert werden: %s", exc
        )
        print(
            f"[FEHLER] GUI-Modul nicht gefunden:\n  {exc}\n"
            "Bitte sicherstellen, dass inverted_double_pendulum_ui.py "
            "im selben Verzeichnis liegt.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        logger.critical("GUI-Start fehlgeschlagen: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
