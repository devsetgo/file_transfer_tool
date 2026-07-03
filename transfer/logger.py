from __future__ import annotations

import logging
from pathlib import Path


def build_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger(f"transfer_{log_file.stem}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(handler)
    return logger
