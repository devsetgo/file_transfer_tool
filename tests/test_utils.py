from __future__ import annotations

import unittest

from transfer.utils import slugify_theme


class TestUtils(unittest.TestCase):
    def test_slugify_theme(self) -> None:
        self.assertEqual(slugify_theme("Taiga Out"), "taiga-out")
        self.assertEqual(slugify_theme("  Northern Lights!!  "), "northern-lights")
        self.assertEqual(slugify_theme("***"), "untitled")


if __name__ == "__main__":
    unittest.main()
