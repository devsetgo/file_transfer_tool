from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import transfer_sd


class TestCLIOverrides(unittest.TestCase):
    def test_cli_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "archive_folder_name": "Expedition_Archive",
                        "archive_drive_labels": ["ExpeditionDrive"],
                        "devices": ["DJI"],
                        "supported_extensions": [".mp4"],
                        "verification_mode": "size",
                        "require_external_archive": True,
                        "copy_engine": "python",
                        "robocopy_threads": 2,
                        "worker_threads": 2,
                        "dry_run": False,
                        "copy_retries": 1,
                        "resume_enabled": False,
                    }
                ),
                encoding="utf-8",
            )

            cfg = transfer_sd.get_config_from_args([
                "--config",
                str(path),
                "--dry-run",
                "--resume",
                "--copy-engine",
                "robocopy",
                "--robocopy-threads",
                "8",
                "--worker-threads",
                "6",
                "--copy-retries",
                "4",
            ])

            self.assertTrue(cfg.dry_run)
            self.assertTrue(cfg.resume_enabled)
            self.assertEqual(cfg.copy_engine, "robocopy")
            self.assertEqual(cfg.robocopy_threads, 8)
            self.assertEqual(cfg.worker_threads, 6)
            self.assertEqual(cfg.copy_retries, 4)


if __name__ == "__main__":
    unittest.main()
