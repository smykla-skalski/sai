"""Behavior tests for opt-in ship-it bookkeeping.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/ship-it/skills/ship-it/scripts/bookkeeping.py"


def checkpoint_document() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "checkpointId": "a" * 64,
        "task": {},
        "repository": {},
        "workflow": {
            "phase": "resolve",
            "status": "active",
            "revision": None,
            "blocker": None,
            "unresolvedQuestions": [],
            "nextAction": "explore",
        },
        "delivery": {},
        "evidence": {},
        "claim": None,
        "bookkeeping": {},
        "risk": {},
        "releasePolicy": None,
        "hostedReviewDecision": None,
        "convergence": {},
        "ciTriage": {},
        "orchestration": None,
        "outcome": None,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


class BookkeepingTest(unittest.TestCase):
    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_policy_disables_optional_bookkeeping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script("policy", "--repository", directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "claims": False,
                "evidence": False,
                "policySource": "bundled default",
                "telemetry": False,
            },
        )

    def test_repository_and_user_policy_enable_features(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".sai").mkdir()
            (root / ".sai/ship-it-bookkeeping.json").write_text(
                '{"claims":true}', encoding="utf-8"
            )
            result = self.run_script(
                "policy", "--repository", directory, "--enable", "telemetry"
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        policy = json.loads(result.stdout)
        self.assertTrue(policy["claims"])
        self.assertFalse(policy["evidence"])
        self.assertTrue(policy["telemetry"])
        self.assertEqual(policy["policySource"], "explicit user request")

    def test_transition_updates_checkpoint_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            checkpoint.write_text(
                json.dumps(checkpoint_document()),
                encoding="utf-8",
            )
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "publish",
                "--status",
                "active",
                "--next-action",
                "open draft PR",
                "--revision",
                "a" * 40,
            )
            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated["workflow"]["phase"], "publish")
        self.assertEqual(updated["workflow"]["nextAction"], "open draft PR")
        self.assertEqual(updated["workflow"]["revision"], "a" * 40)

    def test_transition_rejects_invalid_phase_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            original = json.dumps(checkpoint_document())
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "nonsense",
                "--status",
                "active",
                "--next-action",
                "continue",
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid workflow phase", result.stderr)
        self.assertEqual(current, original)

    def test_blocked_transition_requires_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            original = json.dumps(checkpoint_document())
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "wait",
                "--status",
                "blocked",
                "--next-action",
                "supply credentials",
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--blocker is required", result.stderr)
        self.assertEqual(current, original)


if __name__ == "__main__":
    unittest.main()
