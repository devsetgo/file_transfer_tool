from __future__ import annotations

from pathlib import Path


def verify_file_size(source: Path, destination: Path) -> bool:
    try:
        return source.stat().st_size == destination.stat().st_size
    except OSError:
        return False
