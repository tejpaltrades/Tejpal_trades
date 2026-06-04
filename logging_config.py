"""File + console logging for local and cloud (VPS) runs."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import PROJECT_DIR


def setup_logging(log_dir: Path | None = None) -> Path:
    log_dir = log_dir or (PROJECT_DIR / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "bot.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("brahmos_bot").info("Logging to %s", log_file)
    return log_dir
