from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import time
import shutil
import argparse

from dataclasses import replace
from transfer.config import load_config
from transfer.copier import collect_supported_files, copy_and_verify
from transfer.drive_detection import (
    find_archive_candidates,
    is_system_drive,
    list_drives,
    list_removable_drives,
)
from transfer.logger import build_logger
from transfer.manifest import ManifestWriter
from transfer.progress import build_console_progress
from transfer.utils import ask_with_default, choose_menu_index, format_bytes, now_stamp, slugify_theme


def _fail(message: str) -> int:
    print(f"\nERROR: {message}")
    return 1


def _confirm_proceed() -> bool:
    while True:
        proceed = input("Proceed? Type YES/Y to continue, NO/N to cancel: ").strip().lower()
        if proceed in {"yes", "y"}:
            return True
        if proceed in {"no", "n", ""}:
            return False
        print("Please enter YES, Y, NO, or N.")


def _rate(value: float) -> str:
    return f"{value:.2f}"


def _available_destination_bytes(archive_drive_root: Path) -> int:
    usage = shutil.disk_usage(archive_drive_root)
    return usage.free


def get_config_from_args(argv: list[str] | None = None):
    project_root = Path(__file__).resolve().parent
    default_config_path = project_root / "config.json"

    parser = argparse.ArgumentParser(description="Safe SD card transfer tool")
    parser.add_argument("--config", "-c", default=str(default_config_path), help="Path to config.json")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Enable dry run (override config)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Disable dry run (override config)")
    parser.add_argument("--resume", dest="resume", action="store_true", help="Enable resume mode (override config)")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Disable resume mode (override config)")
    parser.add_argument("--copy-engine", choices=["python", "robocopy", "threaded"], help="Copy engine to use (override config)")
    parser.add_argument("--robocopy-threads", type=int, help="Number of threads for robocopy (override config)")
    parser.add_argument("--worker-threads", type=int, help="Number of worker threads for threaded mode (override config)")
    parser.add_argument("--copy-retries", type=int, help="Number of copy retries on failure (override config)")

    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    config = load_config(config_path)

    # Apply CLI overrides where provided (use dataclasses.replace since AppConfig is frozen)
    if args.dry_run is not None:
        config = replace(config, dry_run=bool(args.dry_run))
    if args.resume is not None:
        config = replace(config, resume_enabled=bool(args.resume))
    if args.copy_engine:
        config = replace(config, copy_engine=str(args.copy_engine))
    if args.robocopy_threads is not None:
        config = replace(config, robocopy_threads=max(1, int(args.robocopy_threads)))
    if args.worker_threads is not None:
        config = replace(config, worker_threads=max(1, int(args.worker_threads)))
    if args.copy_retries is not None:
        config = replace(config, copy_retries=max(0, int(args.copy_retries)))

    return config


def main(argv: list[str] | None = None) -> int:
    # Parse args and load configuration
    config = get_config_from_args(argv)
    if config.copy_engine not in {"python", "robocopy", "threaded"}:
        return _fail("Invalid copy_engine in config. Use 'python', 'robocopy', or 'threaded'.")

    all_drives = list_drives()
    archive_candidates = find_archive_candidates(all_drives, config.archive_drive_labels)
    if not archive_candidates:
        return _fail("No archive drive found using configured volume labels.")

    archive_options = [f"{d.root}  {d.label or '(No Label)'}" for d in archive_candidates]
    archive_index = 0
    if len(archive_options) > 1:
        archive_index = choose_menu_index("Detected Archive Drives", archive_options)

    archive_drive = archive_candidates[archive_index]
    if config.require_external_archive and is_system_drive(archive_drive.root):
        return _fail("Refusing to use system drive as archive destination.")

    removable = list_removable_drives()
    if not removable:
        return _fail("No removable drives (SD cards) were detected.")

    sd_options = [f"{d.root}  {d.label or '(No Label)'}" for d in removable]
    source_index = choose_menu_index("Detected Removable Drives", sd_options)
    source_drive = removable[source_index]

    if source_drive.root.upper() == archive_drive.root.upper():
        return _fail("Source drive and archive drive cannot be the same drive.")

    default_date = date.today().isoformat()
    day_value = ask_with_default("\nEnter date (press Enter for today): ", default_date)

    theme_raw = input("Enter today's theme: ").strip()
    if not theme_raw:
        return _fail("Theme is required.")
    theme_slug = slugify_theme(theme_raw)

    device_index = choose_menu_index("Device", config.devices)
    device_name = config.devices[device_index]

    archive_root = Path(archive_drive.root) / config.archive_folder_name
    destination = archive_root / day_value / theme_slug / device_name
    logs_dir = archive_root / "_logs"

    files = collect_supported_files(Path(source_drive.root), config.supported_extensions)
    if not files:
        return _fail("No supported media files found on selected SD card.")

    total_size = sum(path.stat().st_size for path in files)
    available_bytes = _available_destination_bytes(Path(archive_drive.root))

    print("\nTransfer Confirmation\n")
    print(f"Archive Drive\n{archive_drive.root} {archive_drive.label}\n")
    print(f"Source\n{source_drive.root} {source_drive.label}\n")
    print(f"Destination\n{destination}\n")
    print(f"Files Found\n{len(files)}\n")
    print(f"Total Size\n{format_bytes(total_size)}\n")
    print(f"Available Destination Space\n{format_bytes(available_bytes)}\n")

    if not config.dry_run and available_bytes < total_size:
        return _fail("Destination drive does not have enough free space for this transfer.")

    if config.dry_run:
        print("DRY RUN MODE ENABLED\nNo files will be copied.\n")

    if config.resume_enabled:
        print("Resume mode enabled\nCompleted files from prior runs will be skipped when possible.\n")

    if not _confirm_proceed():
        print("Transfer canceled.")
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    stamp = now_stamp()
    log_path = logs_dir / f"transfer_{stamp}.log"
    manifest_path = logs_dir / f"manifest_{stamp}.csv"

    logger = build_logger(log_path)
    logger.info("Transfer started.")
    logger.info("Source: %s", source_drive.root)
    logger.info("Destination: %s", destination)

    transfer_start = time.perf_counter()
    with ManifestWriter(manifest_path) as manifest:
        summary = copy_and_verify(
            source_root=Path(source_drive.root),
            destination_root=destination,
            files=files,
            logger=logger,
            manifest=manifest,
            progress=build_console_progress(),
            copy_engine=config.copy_engine,
            robocopy_threads=config.robocopy_threads,
            worker_threads=config.worker_threads,
            copy_retries=config.copy_retries,
            dry_run=config.dry_run,
            logs_dir=logs_dir,
            resume_enabled=config.resume_enabled,
        )
    elapsed_seconds = max(0.001, time.perf_counter() - transfer_start)
    files_per_second = summary.files_found / elapsed_seconds
    copied_mb_per_second = (summary.bytes_copied / (1024 * 1024)) / elapsed_seconds

    success = summary.errors == 0 and summary.verified == summary.files_found

    print("")
    if success:
        print("COPY COMPLETE\n")
    else:
        print("COPY COMPLETED WITH ERRORS\n")

    print(f"Files Copied\n{summary.files_copied}\n")
    print(f"Duplicates\n{summary.duplicates}\n")
    print(f"Conflicts Renamed\n{summary.conflicts_renamed}\n")
    print(f"Errors\n{summary.errors}\n")
    print(f"Verified\n{summary.verified} / {summary.files_found}\n")
    print(f"Elapsed\n{elapsed_seconds:.1f} s\n")
    print(f"Files/s\n{_rate(files_per_second)}\n")
    print(f"Copied Throughput\n{_rate(copied_mb_per_second)} MB/s\n")
    print(f"Data Copied\n{format_bytes(summary.bytes_copied)}\n")
    if config.dry_run:
        print("DRY RUN COMPLETE\n")

    if success:
        print("SAFE TO FORMAT SD CARD")
    else:
        print("DO NOT FORMAT SD CARD")
        print("Review the transfer log.")

    print(f"\nLog File: {log_path}")
    print(f"Manifest: {manifest_path}")

    logger.info("Transfer elapsed seconds: %.3f", elapsed_seconds)
    logger.info("Transfer files per second: %.3f", files_per_second)
    logger.info("Transfer copied MB/s: %.3f", copied_mb_per_second)
    logger.info("Transfer copied bytes: %d", summary.bytes_copied)
    logger.info("Transfer dry run: %s", config.dry_run)
    logger.info("Destination available bytes: %d", available_bytes)
    logger.info("Transfer resume enabled: %s", config.resume_enabled)

    return 0


if __name__ == "__main__":
    sys.exit(main())
