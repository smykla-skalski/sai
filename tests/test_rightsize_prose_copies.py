"""Keep the rightsize prose rules identical to the humanize references.

rightsize write and rewrite apply the humanize rules from bundled copies, so
that they work without the humanize plugin installed.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"
HUMANIZE_REFERENCES = PLUGINS_DIR / "humanize" / "skills" / "humanize" / "references"
RIGHTSIZE_PROSE = (
    PLUGINS_DIR / "rightsize" / "skills" / "rightsize" / "references" / "prose"
)


def names(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.glob("*.md"))


class ProseCopiesTest(unittest.TestCase):
    def test_every_humanize_reference_has_a_copy(self) -> None:
        self.assertEqual(names(RIGHTSIZE_PROSE), names(HUMANIZE_REFERENCES))

    def test_copies_match_humanize_byte_for_byte(self) -> None:
        for name in names(HUMANIZE_REFERENCES):
            with self.subTest(reference=name):
                self.assertEqual(
                    (RIGHTSIZE_PROSE / name).read_bytes(),
                    (HUMANIZE_REFERENCES / name).read_bytes(),
                    f"copy {name} from humanize into rightsize references/prose",
                )


if __name__ == "__main__":
    unittest.main()
