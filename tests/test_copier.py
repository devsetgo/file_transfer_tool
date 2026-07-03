from __future__ import annotations

import logging
from pathlib import Path
import tempfile
import unittest

from transfer.copier import ResumeState, filter_pending_files, resolve_destination_path


class TestCopier(unittest.TestCase):
    def test_conflict_naming_uses_copy_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "clip.mp4"
            destination.write_bytes(b"123")

            chosen, decision = resolve_destination_path(destination, source_size=4)

            self.assertEqual(decision, "CONFLICT_RENAME")
            self.assertEqual(chosen.name, "clip__copy2.mp4")

    def test_duplicate_detection_by_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "clip.mp4"
            destination.write_bytes(b"1234")

            chosen, decision = resolve_destination_path(destination, source_size=4)

            self.assertEqual(decision, "DUPLICATE")
            self.assertEqual(chosen, destination)

    def test_resume_filter_skips_completed_files_only_when_destination_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source"
            destination_root = root / "dest"
            source_root.mkdir()
            destination_root.mkdir()

            keep = source_root / "keep.mp4"
            skip = source_root / "skip.mp4"
            keep.write_bytes(b"1234")
            skip.write_bytes(b"1234")

            (destination_root / "skip.mp4").write_bytes(b"1234")

            resume_state = ResumeState(
                source_root=str(source_root),
                destination_root=str(destination_root),
                completed={"skip.mp4"},
            )

            pending, completed = filter_pending_files(source_root, destination_root, [keep, skip], resume_state)

            self.assertEqual(pending, [keep])
            self.assertEqual(completed, {"skip.mp4"})


if __name__ == "__main__":
    unittest.main()
