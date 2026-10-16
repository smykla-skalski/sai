"""Exercise the documented per-file helper bundles outside the checkout.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugins/ship-it/skills/ship-it"


class FileDeliveryTest(unittest.TestCase):
    def test_documented_bundles_run_without_checkout_imports(self) -> None:
        reference = (SKILL / "references/helper-loading.md").read_text()
        rows = re.findall(
            r"^\| `scripts/([^`]+)`[^|]* \| ([^|]+) \|$", reference, re.MULTILINE
        )
        self.assertTrue(rows)
        import_template = re.findall(r"`python3 -c '([^']+)'`", reference)
        self.assertEqual(len(import_template), 1)
        self.assertEqual(
            {entry for entry, _ in rows},
            {
                path.name
                for path in (SKILL / "scripts").glob("*.py")
                if not path.name.startswith("test_")
            },
        )
        for entry, dependencies in rows:
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = root / "package"
                files = [
                    f"scripts/{entry}",
                    *re.findall(r"`((?:scripts|references)/[^`]+)`", dependencies),
                ]
                for name in files:
                    destination = bundle / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(SKILL / name, destination)
                if entry in {
                    "checkpoint_state.py",
                    "orchestration_state.py",
                    "convergence.py",
                    "validation_reuse.py",
                    "token_cost.py",
                }:
                    command = [
                        sys.executable,
                        "-E",
                        "-c",
                        import_template[0].replace("MODULE", Path(entry).stem),
                    ]
                else:
                    command = [
                        sys.executable,
                        str(bundle / "scripts" / entry),
                        "--help",
                    ]
                result = subprocess.run(
                    command,
                    cwd=bundle / "scripts",
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                if entry == "bookkeeping.py":
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(bundle / "scripts" / entry),
                            "policy",
                            "--repository",
                            str(root),
                        ],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("telemetry", json.loads(result.stdout))

    def test_entry_only_routes_connected_host_integration(self) -> None:
        entry = (SKILL / "SKILL.md").read_text()
        lines = [line for line in entry.splitlines() if "sail" in line.lower()]
        self.assertEqual(len(lines), 1)
        self.assertIn("If connected tools", lines[0])
        self.assertIn("Otherwise do not load it", lines[0])
        fallbacks = (SKILL / "references/fallbacks.md").read_text()
        self.assertNotIn("Sail worker and gate availability", fallbacks)


if __name__ == "__main__":
    unittest.main()
