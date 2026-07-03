from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from transfer.config import load_config


class TestConfig(unittest.TestCase):
    def test_copy_engine_defaults_to_robocopy(self) -> None:
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
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(path)
            self.assertEqual(config.copy_engine, "robocopy")
            self.assertEqual(config.robocopy_threads, 2)

    def test_robocopy_threads_minimum_is_one(self) -> None:
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
                        "copy_engine": "robocopy",
                        "robocopy_threads": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(path)
            self.assertEqual(config.robocopy_threads, 1)

    def test_worker_threads_minimum_is_one(self) -> None:
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
                        "copy_engine": "threaded",
                        "worker_threads": 0,
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(path)
            self.assertEqual(config.copy_engine, "threaded")
            self.assertEqual(config.worker_threads, 1)


if __name__ == "__main__":
    unittest.main()