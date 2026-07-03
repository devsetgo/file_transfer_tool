# SD Card Transfer Tool (Phase 1)

Safety-first Windows console application to transfer expedition media from SD cards to an archive drive.

## Safety Guarantees

- Never overwrites existing destination files.
- Never deletes or formats source media.
- Detects archive drive by volume label, not by hardcoded letter.
- Verifies each copied file by size.
- Writes both transfer logs and a CSV manifest.

## Requirements

- Windows 11
- Python 3.12+

## Setup

1. Open PowerShell in this project folder.
2. (Optional) Create a venv and activate it.
3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Review and edit `config.json` to match your archive drive volume label(s).

## Run

```powershell
python transfer_sd.py
```

At the confirmation step, enter `YES` or `Y` to proceed, or `NO`/`N` to cancel.

During transfer, a per-file progress bar is shown in the console via `tqdm`.
After transfer, the summary includes elapsed time, files per second, and copied MB/s.

## Config

`config.json` controls:

- `archive_folder_name`
- `archive_drive_labels`
- `devices`
- `supported_extensions`
- `verification_mode`
- `require_external_archive`
- `copy_engine` (`robocopy` or `python`)
- `robocopy_threads` (used when `copy_engine` is `robocopy`)
- `worker_threads` (used when `copy_engine` is `threaded`)
- `dry_run` (plan-only mode, no files are copied)
- `copy_retries` (retry attempts for transient copy errors)
- `resume_enabled` (persist completed files and skip them on later runs when the destination still matches)

Default mode uses RoboCopy on Windows. The console UI uses a single overall progress bar so the transfer stays easy to read at a glance. Conflict-renamed files (for `__copy2`, `__copy3`, etc.) are copied with Python to preserve strict naming behavior.
The progress bar shows the current file name and its status.

Before copying, the tool also shows the available free space on the archive drive and stops if the destination does not have enough room, unless `dry_run` is enabled.

## Output Layout

The tool writes to:

- `<ArchiveDrive>\Expedition_Archive\YYYY-MM-DD\<theme>\<device>\`
- `<ArchiveDrive>\Expedition_Archive\_logs\transfer_YYYY-MM-DD_HHMM.log`
- `<ArchiveDrive>\Expedition_Archive\_logs\manifest_YYYY-MM-DD_HHMM.csv`

The manifest includes per-file timing and transfer speed columns so nightly runs can be compared.

## Running Tests

```powershell
python -m unittest discover -s tests
```

## Progress Architecture

Progress reporting is decoupled from copy logic through a small reporter interface in `transfer/progress.py`.
The current console implementation uses `tqdm`, and a future GUI can plug in a GUI reporter without changing transfer behavior.

## Dry Run

Set `dry_run` to `true` in `config.json` to preview the transfer without copying any files. The manifest and log still record what would have happened.

## Resume Mode

Leave `resume_enabled` set to `true` to keep a small resume state file in the logs folder. If a transfer is interrupted, the next run will skip files that already completed and still match the source size at the destination.

## Packaging

To build a Windows executable with PyInstaller:

```powershell
pip install -r requirements.txt
.\build_exe.ps1
```

The included `build_exe.ps1` script runs PyInstaller and embeds `config.json` next to the executable using `--add-data` so the packaged exe can read configuration at runtime. After building, place any local `config.json` edits beside the exe or edit the embedded copy as needed.
