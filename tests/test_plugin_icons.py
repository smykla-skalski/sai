"""Keep every plugin's directory icon present and within the directory's limits.

`claude plugin validate` warns ICON_MISSING without one. The directory takes a
square PNG of 512 to 2048 px under 2 MB. scripts/plugin_icons.py renders them,
so a new plugin also needs a glyph there.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_SIDE, MAX_SIDE = 512, 2048
MAX_BYTES = 2 * 1024 * 1024


def plugin_dirs() -> list[Path]:
    return sorted(
        p.parent.parent
        for p in (REPO_ROOT / "plugins").glob("*/.claude-plugin/plugin.json")
    )


class PluginIconTest(unittest.TestCase):
    def test_every_plugin_has_a_valid_icon(self) -> None:
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                icon = plugin / ".claude-plugin" / "icon.png"
                data = icon.read_bytes()
                self.assertEqual(data[:8], PNG_SIGNATURE)
                width, height = struct.unpack(">II", data[16:24])
                self.assertEqual(width, height)
                self.assertGreaterEqual(width, MIN_SIDE)
                self.assertLessEqual(width, MAX_SIDE)
                self.assertLess(len(data), MAX_BYTES)

    def test_every_plugin_has_a_glyph(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "plugin_icons", REPO_ROOT / "scripts" / "plugin_icons.py"
        )
        if spec is None or spec.loader is None:
            self.fail("cannot load scripts/plugin_icons.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(sorted(module.GLYPHS), [p.name for p in plugin_dirs()])


if __name__ == "__main__":
    unittest.main()
