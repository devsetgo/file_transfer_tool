from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ProgressReporter(Protocol):
    def start(self, total: int) -> None:
        ...

    def advance(self, source: Path, status: str, display_label: str | None = None) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass
class NoOpProgressReporter:
    def start(self, total: int) -> None:
        return None

    def advance(self, source: Path, status: str, display_label: str | None = None) -> None:
        return None

    def close(self) -> None:
        return None


class TqdmProgressReporter:
    def __init__(self) -> None:
        self._bar = None

    def start(self, total: int) -> None:
        try:
            from tqdm import tqdm
        except Exception:
            self._bar = None
            return

        self._bar = tqdm(
            total=total,
            desc="Transfer",
            unit="file",
            dynamic_ncols=True,
        )

    def advance(self, source: Path, status: str, display_label: str | None = None) -> None:
        if self._bar is None:
            return
        label = display_label or source.name
        self._bar.set_postfix_str(f"{label} | {status}")
        self._bar.update(1)

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()
            self._bar = None


def build_console_progress() -> ProgressReporter:
    return TqdmProgressReporter()
