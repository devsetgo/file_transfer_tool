from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from transfer.manifest import ManifestWriter


class TestManifest(unittest.TestCase):
    def test_manifest_header_includes_timing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.csv"
            with ManifestWriter(path):
                pass

            header = path.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn("Time Taken (Seconds)", header)
            self.assertIn("Transfer Speed (MB/s)", header)


if __name__ == "__main__":
    unittest.main()