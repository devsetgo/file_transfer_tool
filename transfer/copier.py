from __future__ import annotations

from dataclasses import dataclass
import logging
import json
from pathlib import Path
from queue import Queue
import threading
import shutil
import subprocess
import time

from transfer.manifest import ManifestWriter
from transfer.progress import NoOpProgressReporter, ProgressReporter
from transfer.utils import now_iso
from transfer.verifier import verify_file_size


@dataclass
class CopySummary:
    files_found: int = 0
    files_copied: int = 0
    duplicates: int = 0
    conflicts_renamed: int = 0
    errors: int = 0
    verified: int = 0
    bytes_copied: int = 0


@dataclass(frozen=True)
class FileOutcome:
    source: Path
    destination: Path
    source_size: int
    elapsed_seconds: float
    transfer_speed_mb_per_second: float
    manifest_status: str
    verification_status: str
    notes: str
    progress_status: str


@dataclass(frozen=True)
class ResumeState:
    source_root: str
    destination_root: str
    completed: set[str]


def _state_path(logs_dir: Path, destination_root: Path) -> Path:
    slug = str(destination_root).replace(":", "").replace("\\", "_").replace("/", "_")
    return logs_dir / f"resume_{slug}.json"


def load_resume_state(logs_dir: Path, destination_root: Path) -> ResumeState:
    path = _state_path(logs_dir, destination_root)
    if not path.exists():
        return ResumeState(source_root="", destination_root=str(destination_root), completed=set())

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return ResumeState(
        source_root=str(data.get("source_root", "")),
        destination_root=str(data.get("destination_root", str(destination_root))),
        completed={str(item) for item in data.get("completed", [])},
    )


def save_resume_state(logs_dir: Path, destination_root: Path, source_root: Path, completed: set[str]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(logs_dir, destination_root)
    payload = {
        "source_root": str(source_root),
        "destination_root": str(destination_root),
        "completed": sorted(completed),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _relative_source_label(source_root: Path, source: Path) -> str:
    return source.relative_to(source_root).as_posix()


def _already_completed_destination(destination_root: Path, source_root: Path, source: Path) -> bool:
    rel_path = source.relative_to(source_root)
    destination = destination_root / rel_path
    try:
        return destination.exists() and destination.stat().st_size == source.stat().st_size
    except OSError:
        return False


def filter_pending_files(
    source_root: Path,
    destination_root: Path,
    files: list[Path],
    resume_state: ResumeState,
) -> tuple[list[Path], set[str]]:
    if not resume_state.completed:
        return files, set()

    pending: list[Path] = []
    completed: set[str] = set()
    for source in files:
        rel_label = _relative_source_label(source_root, source)
        if rel_label in resume_state.completed and _already_completed_destination(destination_root, source_root, source):
            completed.add(rel_label)
            continue
        pending.append(source)
    return pending, completed


def collect_supported_files(source_root: Path, extensions: set[str]) -> list[Path]:
    files: list[Path] = []
    ext_set = {ext.lower() for ext in extensions}
    for path in source_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in ext_set:
            files.append(path)
    return files


def resolve_destination_path(destination_file: Path, source_size: int) -> tuple[Path, str]:
    if not destination_file.exists():
        return destination_file, "COPY"

    if destination_file.stat().st_size == source_size:
        return destination_file, "DUPLICATE"

    stem = destination_file.stem
    suffix = destination_file.suffix
    parent = destination_file.parent

    copy_number = 2
    while True:
        candidate = parent / f"{stem}__copy{copy_number}{suffix}"
        if not candidate.exists():
            return candidate, "CONFLICT_RENAME"
        copy_number += 1


def _copy_with_robocopy(source: Path, destination: Path, robocopy_threads: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "robocopy",
        str(source.parent),
        str(destination.parent),
        source.name,
        f"/MT:{max(1, robocopy_threads)}",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NC",
        "/NS",
        "/NP",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode >= 8:
        raise RuntimeError(f"RoboCopy failed ({result.returncode}): {result.stderr.strip()}")
    if not destination.exists():
        raise RuntimeError("RoboCopy did not produce the expected destination file.")


def copy_file(source: Path, destination: Path, copy_engine: str, robocopy_threads: int) -> None:
    if copy_engine == "robocopy" and source.name == destination.name:
        _copy_with_robocopy(source, destination, robocopy_threads=robocopy_threads)
        return
    shutil.copy2(source, destination)


def _copy_with_retries(
    source: Path,
    destination: Path,
    copy_engine: str,
    robocopy_threads: int,
    copy_retries: int,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, copy_retries + 1):
        try:
            copy_file(source, destination, copy_engine=copy_engine, robocopy_threads=robocopy_threads)
            return
        except Exception as exc:  # pragma: no cover - defensive runtime handling
            last_error = exc
            if attempt < copy_retries:
                time.sleep(0.25)
    if last_error is not None:
        raise last_error


def _process_file(
    source_root: Path,
    destination_root: Path,
    source: Path,
    copy_engine: str,
    robocopy_threads: int,
    copy_retries: int,
    dry_run: bool,
) -> FileOutcome:
    file_start = time.perf_counter()
    rel_path = source.relative_to(source_root)
    desired_destination = destination_root / rel_path
    desired_destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        source_size = source.stat().st_size
        destination, decision = resolve_destination_path(desired_destination, source_size)

        if decision == "DUPLICATE":
            elapsed_seconds = max(0.0, time.perf_counter() - file_start)
            return FileOutcome(
                source=source,
                destination=destination,
                source_size=source_size,
                elapsed_seconds=elapsed_seconds,
                transfer_speed_mb_per_second=0.0,
                manifest_status="SKIP_DUPLICATE",
                verification_status="VERIFIED",
                notes="Existing destination matched source size.",
                progress_status="DUPLICATE",
            )

        if dry_run:
            elapsed_seconds = max(0.0, time.perf_counter() - file_start)
            transfer_speed_mb_per_second = (
                (source_size / (1024 * 1024)) / elapsed_seconds if elapsed_seconds > 0 else 0.0
            )
            return FileOutcome(
                source=source,
                destination=destination,
                source_size=source_size,
                elapsed_seconds=elapsed_seconds,
                transfer_speed_mb_per_second=transfer_speed_mb_per_second,
                manifest_status="DRY_RUN",
                verification_status="SKIPPED",
                notes="No files were copied.",
                progress_status="DRY-RUN",
            )

        _copy_with_retries(
            source,
            destination,
            copy_engine=copy_engine,
            robocopy_threads=robocopy_threads,
            copy_retries=copy_retries,
        )

        manifest_status = "COPIED_RENAMED" if decision == "CONFLICT_RENAME" else "COPIED"
        verification_status = "VERIFIED" if verify_file_size(source, destination) else "FAILED"
        elapsed_seconds = max(0.0, time.perf_counter() - file_start)
        transfer_speed_mb_per_second = (
            (source_size / (1024 * 1024)) / elapsed_seconds if elapsed_seconds > 0 else 0.0
        )
        progress_status = "VERIFIED" if verification_status == "VERIFIED" else "VERIFY_FAIL"
        return FileOutcome(
            source=source,
            destination=destination,
            source_size=source_size,
            elapsed_seconds=elapsed_seconds,
            transfer_speed_mb_per_second=transfer_speed_mb_per_second,
            manifest_status=manifest_status,
            verification_status=verification_status,
            notes="",
            progress_status=progress_status,
        )

    except Exception as exc:  # pragma: no cover - defensive runtime handling
        elapsed_seconds = max(0.0, time.perf_counter() - file_start)
        return FileOutcome(
            source=source,
            destination=desired_destination,
            source_size=0,
            elapsed_seconds=elapsed_seconds,
            transfer_speed_mb_per_second=0.0,
            manifest_status="ERROR",
            verification_status="FAILED",
            notes=str(exc),
            progress_status="ERROR",
        )


def _apply_outcome(summary: CopySummary, outcome: FileOutcome) -> None:
    if outcome.manifest_status == "SKIP_DUPLICATE":
        summary.duplicates += 1
        summary.verified += 1
        return

    if outcome.manifest_status == "DRY_RUN":
        summary.files_copied += 1
        summary.verified += 1
        return

    if outcome.manifest_status == "ERROR":
        summary.errors += 1
        return

    summary.bytes_copied += outcome.source_size

    if outcome.manifest_status == "COPIED_RENAMED":
        summary.conflicts_renamed += 1
    else:
        summary.files_copied += 1

    if outcome.verification_status == "VERIFIED":
        summary.verified += 1
    else:
        summary.errors += 1


def _write_outcome(
    summary: CopySummary,
    manifest: ManifestWriter,
    logger: logging.Logger,
    outcome: FileOutcome,
) -> None:
    _apply_outcome(summary, outcome)
    manifest.add_row(
        now_iso(),
        str(outcome.source),
        str(outcome.destination),
        outcome.source_size,
        outcome.elapsed_seconds,
        outcome.transfer_speed_mb_per_second,
        outcome.manifest_status,
        outcome.verification_status,
        outcome.notes,
    )

    if outcome.manifest_status == "SKIP_DUPLICATE":
        logger.info("Duplicate skipped: %s", outcome.source)
    elif outcome.manifest_status == "DRY_RUN":
        logger.info("Dry-run planned: %s -> %s", outcome.source, outcome.destination)
    elif outcome.manifest_status == "ERROR":
        logger.error("Error copying file: %s (%s)", outcome.source, outcome.notes)
    elif outcome.verification_status == "VERIFIED":
        logger.info("Copied and verified: %s -> %s", outcome.source, outcome.destination)
    else:
        logger.error("Verification failed: %s -> %s", outcome.source, outcome.destination)


def _is_resumeable_success(outcome: FileOutcome) -> bool:
    return outcome.manifest_status == "SKIP_DUPLICATE" or outcome.verification_status == "VERIFIED"


def _copy_and_verify_threaded(
    source_root: Path,
    destination_root: Path,
    files: list[Path],
    logger: logging.Logger,
    manifest: ManifestWriter,
    progress: ProgressReporter,
    worker_threads: int,
    copy_retries: int,
    dry_run: bool,
    logs_dir: Path | None,
    resume_enabled: bool,
) -> CopySummary:
    summary = CopySummary(files_found=len(files))
    reporter = progress or NoOpProgressReporter()
    worker_count = max(1, worker_threads)

    resume_state = load_resume_state(logs_dir, destination_root) if (resume_enabled and logs_dir is not None) else ResumeState(source_root="", destination_root=str(destination_root), completed=set())
    pending_files, precompleted = filter_pending_files(source_root, destination_root, files, resume_state)
    summary.files_found = len(pending_files)

    reporter.start(total=len(pending_files))

    task_queue: Queue[Path | None] = Queue()
    result_queue: Queue[FileOutcome] = Queue()
    completed_labels = set(precompleted)

    for source in pending_files:
        task_queue.put(source)
    for _ in range(worker_count):
        task_queue.put(None)

    def worker(worker_index: int) -> None:
        while True:
            source = task_queue.get()
            if source is None:
                return
            outcome = _process_file(
                source_root=source_root,
                destination_root=destination_root,
                source=source,
                copy_engine="python",
                robocopy_threads=1,
                copy_retries=copy_retries,
                dry_run=dry_run,
            )
            reporter.advance(source=source, status=outcome.progress_status, display_label=source.relative_to(source_root).as_posix())
            result_queue.put(outcome)

    threads = [threading.Thread(target=worker, args=(index,), daemon=True) for index in range(worker_count)]
    for thread in threads:
        thread.start()

    processed = 0
    try:
        while processed < len(pending_files):
            outcome = result_queue.get()
            _write_outcome(summary, manifest, logger, outcome)
            if resume_enabled and logs_dir is not None and _is_resumeable_success(outcome):
                completed_labels.add(_relative_source_label(source_root, outcome.source))
                save_resume_state(logs_dir, destination_root, source_root, completed_labels)
            processed += 1
    finally:
        for thread in threads:
            thread.join()
        reporter.close()

    return summary


def copy_and_verify(
    source_root: Path,
    destination_root: Path,
    files: list[Path],
    logger: logging.Logger,
    manifest: ManifestWriter,
    progress: ProgressReporter | None = None,
    copy_engine: str = "python",
    robocopy_threads: int = 2,
    worker_threads: int = 4,
    copy_retries: int = 2,
    dry_run: bool = False,
    logs_dir: Path | None = None,
    resume_enabled: bool = False,
) -> CopySummary:
    summary = CopySummary(files_found=len(files))
    reporter = progress or NoOpProgressReporter()
    if copy_engine == "threaded":
        return _copy_and_verify_threaded(
            source_root=source_root,
            destination_root=destination_root,
            files=files,
            logger=logger,
            manifest=manifest,
            progress=reporter,
            worker_threads=worker_threads,
            copy_retries=copy_retries,
            dry_run=dry_run,
            logs_dir=logs_dir,
            resume_enabled=resume_enabled,
        )

    resume_state = load_resume_state(logs_dir, destination_root) if (resume_enabled and logs_dir is not None) else ResumeState(source_root="", destination_root=str(destination_root), completed=set())
    pending_files, precompleted = filter_pending_files(source_root, destination_root, files, resume_state)
    summary.files_found = len(pending_files)
    completed_labels = set(precompleted)

    reporter.start(total=len(pending_files))

    try:
        for source in pending_files:
            outcome = _process_file(
                source_root=source_root,
                destination_root=destination_root,
                source=source,
                copy_engine=copy_engine,
                robocopy_threads=robocopy_threads,
                copy_retries=copy_retries,
                dry_run=dry_run,
            )
            _write_outcome(summary, manifest, logger, outcome)
            reporter.advance(source=source, status=outcome.progress_status, display_label=source.relative_to(source_root).as_posix())
            if resume_enabled and logs_dir is not None and _is_resumeable_success(outcome):
                completed_labels.add(_relative_source_label(source_root, outcome.source))
                save_resume_state(logs_dir, destination_root, source_root, completed_labels)
    finally:
        reporter.close()

    return summary
