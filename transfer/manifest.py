from __future__ import annotations

import csv
from pathlib import Path


class ManifestWriter:
    def __init__(self, manifest_path: Path) -> None:
        self._handle = manifest_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._handle)
        self._writer.writerow(
            [
                "Timestamp",
                "Source Path",
                "Destination Path",
                "File Size",
                "Time Taken (Seconds)",
                "Transfer Speed (MB/s)",
                "Status",
                "Verification Status",
                "Notes",
            ]
        )

    def add_row(
        self,
        timestamp: str,
        source_path: str,
        destination_path: str,
        file_size: int,
        time_taken_seconds: float,
        transfer_speed_mb_per_second: float,
        status: str,
        verification_status: str,
        notes: str,
    ) -> None:
        self._writer.writerow(
            [
                timestamp,
                source_path,
                destination_path,
                file_size,
                f"{time_taken_seconds:.3f}",
                f"{transfer_speed_mb_per_second:.3f}",
                status,
                verification_status,
                notes,
            ]
        )

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "ManifestWriter":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
