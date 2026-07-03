from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    archive_folder_name: str
    archive_drive_labels: list[str]
    devices: list[str]
    supported_extensions: set[str]
    verification_mode: str
    require_external_archive: bool
    copy_engine: str
    robocopy_threads: int
    worker_threads: int
    dry_run: bool
    copy_retries: int
    resume_enabled: bool


def _normalize_extensions(items: list[str]) -> set[str]:
    normalized: set[str] = set()
    for item in items:
        ext = item.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized.add(ext)
    return normalized


def load_config(config_path: Path) -> AppConfig:
    with config_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return AppConfig(
        archive_folder_name=data.get("archive_folder_name", "Expedition_Archive"),
        archive_drive_labels=[str(x) for x in data.get("archive_drive_labels", [])],
        devices=[str(x) for x in data.get("devices", ["DJI", "GoPro", "Dashcam", "Phone", "Other"])],
        supported_extensions=_normalize_extensions(data.get("supported_extensions", [])),
        verification_mode=str(data.get("verification_mode", "size")).lower(),
        require_external_archive=bool(data.get("require_external_archive", True)),
        copy_engine=str(data.get("copy_engine", "robocopy")).lower(),
        robocopy_threads=max(1, int(data.get("robocopy_threads", 2))),
        worker_threads=max(1, int(data.get("worker_threads", 4))),
        dry_run=bool(data.get("dry_run", False)),
        copy_retries=max(1, int(data.get("copy_retries", 2))),
        resume_enabled=bool(data.get("resume_enabled", True)),
    )
