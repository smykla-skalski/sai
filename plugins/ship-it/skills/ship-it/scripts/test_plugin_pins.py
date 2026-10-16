"""Disposable cache lifetime regressions for complete plugin snapshots.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from plugin_pins import Pins, inventory, remove_snapshot


class PluginPinsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(lambda: remove_snapshot(Path(self.temporary.name)))
        self.root = Path(self.temporary.name)
        self.source = self.root / "provider/ship-it"
        self.source.mkdir(parents=True)
        self.skill = self.source / "skills/ship-it"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("complete skill")
        (self.skill / "references").mkdir()
        (self.skill / "references/example.md").write_text("version one reference")
        (self.skill / "scripts").mkdir()
        (self.skill / "scripts/helper.py").write_text("print('version one')")
        self.write_version("1.0.0")
        self.pins = Pins(self.root / "owned")

    def write_version(self, version: str) -> None:
        (self.source / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "ship-it",
                    "version": version,
                }
            )
        )

    def acquire(self) -> dict:
        return self.pins.acquire(self.source, os.getpid())

    def test_update_during_use_and_cleanup_after_last_consumer(self) -> None:
        first = self.acquire()
        worker = self.pins.acquire(Path(first["bundle"]), os.getpid())
        self.write_version("1.0.1")
        (self.skill / "scripts/helper.py").write_text("print('version two')")
        second = self.acquire()
        shutil.rmtree(self.source)
        self.assertNotEqual(first["bundle"], second["bundle"])
        self.assertEqual(first["bundle"], worker["bundle"])
        self.assertEqual(
            (Path(first["skillRoot"]) / "scripts/helper.py").read_text(),
            "print('version one')",
        )
        self.assertEqual(
            (Path(first["skillRoot"]) / "references/example.md").read_text(),
            "version one reference",
        )
        output = subprocess.check_output(
            [
                sys.executable,
                str(Path(first["skillRoot"]) / "scripts/helper.py"),
            ],
            text=True,
        )
        self.assertEqual(output.strip(), "version one")
        self.pins.release(first["lease"])
        self.assertEqual(self.pins.collect(3)["removed"], [])
        self.pins.release(worker["lease"])
        self.assertEqual(self.pins.collect(3)["removed"], [first["digest"]])
        self.assertTrue(Path(second["bundle"]).is_dir())

    def test_failed_copy_preserves_previous_bundle(self) -> None:
        first = self.acquire()
        self.write_version("1.0.1")
        with (
            patch("plugin_pins.shutil.copytree", side_effect=OSError("interrupted")),
            self.assertRaisesRegex(OSError, "interrupted"),
        ):
            self.acquire()
        self.assertTrue((Path(first["skillRoot"]) / "SKILL.md").is_file())
        self.assertEqual(list(self.pins.root.glob(".staging-*")), [])
        self.assertEqual(len(list((self.pins.root / "bundles").iterdir())), 1)

    def test_mutating_source_is_not_published(self) -> None:
        def changing_inventory(root: Path) -> dict:
            result = inventory(root)
            if root != self.source:
                self.write_version("1.0.1")
            return result

        with (
            patch("plugin_pins.inventory", side_effect=changing_inventory),
            self.assertRaisesRegex(ValueError, "changed during snapshot"),
        ):
            self.acquire()
        self.assertEqual(list((self.pins.root / "bundles").iterdir()), [])

    def test_cleanup_limit_and_abandoned_owner(self) -> None:
        leases = []
        for version in ("1.0.0", "1.0.1", "1.0.2"):
            self.write_version(version)
            leases.append(self.acquire())
        with patch("plugin_pins.process_identity", side_effect=ValueError("dead")):
            self.assertEqual(len(self.pins.collect(1)["removed"]), 1)
        self.assertEqual(len(list((self.pins.root / "bundles").iterdir())), 2)
        self.assertEqual(list((self.pins.root / "leases").iterdir()), [])

    def test_reject_symlink_and_tampered_snapshot(self) -> None:
        first = self.acquire()
        (Path(first["skillRoot"]) / "SKILL.md").chmod(0o600)
        (Path(first["skillRoot"]) / "SKILL.md").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.acquire()
        (self.skill / "external").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.acquire()

    def test_concurrent_acquire_and_collection_protect_live_leases(self) -> None:
        def consumer(_: int) -> dict:
            lease = self.acquire()
            self.pins.collect(1)
            return lease

        with ThreadPoolExecutor(max_workers=4) as executor:
            leases = list(executor.map(consumer, range(12)))
        self.assertEqual(len({item["lease"] for item in leases}), 12)
        self.assertEqual(len({item["bundle"] for item in leases}), 1)
        self.assertTrue(Path(leases[0]["bundle"]).is_dir())

    def test_probe_failure_never_reclaims_active_bundle(self) -> None:
        first = self.acquire()
        with (
            patch("plugin_pins.process_identity", side_effect=OSError("probe denied")),
            self.assertRaisesRegex(OSError, "probe denied"),
        ):
            self.pins.collect(3)
        self.assertTrue(Path(first["bundle"]).is_dir())
        self.assertTrue(
            (self.pins.root / "leases" / f"{first['lease']}.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
