"""Behavior tests for opt-in ship-it bookkeeping.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/ship-it/skills/ship-it/scripts/bookkeeping.py"


def checkpoint_document() -> dict[str, object]:
    canonical_source = '{"issue":198,"repository":"github.com/smykla-skalski/sai","sourceType":"github"}'
    checkpoint_id = hashlib.sha256(canonical_source.encode()).hexdigest()
    return {
        "schemaVersion": 1,
        "checkpointId": checkpoint_id,
        "task": {
            "sourceType": "github",
            "canonicalSource": canonical_source,
        },
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
        "evidence": {
            "revision": None,
            "recordPath": None,
            "status": "disabled",
            "updatedAt": None,
        },
        "gateVerdicts": [],
        "claim": None,
        "bookkeeping": {
            "claims": False,
            "evidence": False,
            "telemetry": False,
            "policySource": "bundled default",
        },
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


def checkpoint_path(directory: str, document: dict[str, object]) -> Path:
    return Path(directory) / f"{document['checkpointId']}.json"


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
            document = checkpoint_document()
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(
                json.dumps(document),
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
            document = checkpoint_document()
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
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
            document = checkpoint_document()
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
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

    def test_complete_transition_writes_outcome_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            delivery = document["delivery"]
            if isinstance(workflow, dict):
                workflow["revision"] = "a" * 40
            if isinstance(delivery, dict):
                delivery.update(
                    {
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "a" * 40,
                        "mergeCommit": "b" * 40,
                    },
                )
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(json.dumps(document), encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "complete",
                "--status",
                "completed",
                "--next-action",
                "none",
                "--outcome-json",
                json.dumps(
                    {
                        "result": "merged",
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "a" * 40,
                        "mergeCommit": "b" * 40,
                        "sourceState": "closed",
                        "branchCleanup": "deleted",
                        "completedAt": "2026-01-01T00:00:00Z",
                    },
                ),
            )
            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated["outcome"]["result"], "merged")

    def test_complete_transition_rejects_outcome_that_differs_from_delivery(self) -> None:
        fields = {
            "pullRequestUrl": "https://github.com/o/r/pull/2",
            "pullRequestHead": "c" * 40,
            "mergeCommit": "d" * 40,
        }
        for field, mismatched in fields.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                document = checkpoint_document()
                workflow = document["workflow"]
                delivery = document["delivery"]
                if isinstance(workflow, dict):
                    workflow["revision"] = "a" * 40
                if isinstance(delivery, dict):
                    delivery.update(
                        {
                            "pullRequestUrl": "https://github.com/o/r/pull/1",
                            "pullRequestHead": "a" * 40,
                            "mergeCommit": "b" * 40,
                        },
                    )
                outcome = {
                    "result": "merged",
                    "pullRequestUrl": "https://github.com/o/r/pull/1",
                    "pullRequestHead": "a" * 40,
                    "mergeCommit": "b" * 40,
                    "sourceState": "closed",
                    "branchCleanup": "deleted",
                    "completedAt": "2026-01-01T00:00:00Z",
                }
                outcome[field] = mismatched
                checkpoint = checkpoint_path(directory, document)
                original = json.dumps(document)
                checkpoint.write_text(original, encoding="utf-8")
                result = self.run_script(
                    "transition",
                    "--checkpoint",
                    str(checkpoint),
                    "--phase",
                    "complete",
                    "--status",
                    "completed",
                    "--next-action",
                    "none",
                    "--outcome-json",
                    json.dumps(outcome),
                )
                current = checkpoint.read_text(encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertIn(f"must match delivery.{field}", result.stderr)
            self.assertEqual(current, original)

    def test_complete_transition_rejects_head_that_differs_from_workflow_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            delivery = document["delivery"]
            if isinstance(workflow, dict):
                workflow["revision"] = "c" * 40
            if isinstance(delivery, dict):
                delivery.update(
                    {
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "a" * 40,
                        "mergeCommit": "b" * 40,
                    },
                )
            outcome = {
                "result": "merged",
                "pullRequestUrl": "https://github.com/o/r/pull/1",
                "pullRequestHead": "a" * 40,
                "mergeCommit": "b" * 40,
                "sourceState": "closed",
                "branchCleanup": "deleted",
                "completedAt": "2026-01-01T00:00:00Z",
            }
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "complete",
                "--status",
                "completed",
                "--next-action",
                "none",
                "--outcome-json",
                json.dumps(outcome),
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must match workflow.revision", result.stderr)
        self.assertEqual(current, original)

    def test_complete_transition_rejects_incomplete_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "complete",
                "--status",
                "completed",
                "--next-action",
                "none",
                "--outcome-json",
                '{"result":"merged"}',
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("terminal outcome missing required fields", result.stderr)
        self.assertEqual(current, original)

    def test_transition_migrates_known_legacy_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            document.pop("bookkeeping")
            document.pop("hostedReviewDecision")
            evidence = document["evidence"]
            if isinstance(evidence, dict):
                evidence["status"] = "missing"
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(json.dumps(document), encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "explore",
                "--status",
                "active",
                "--next-action",
                "inspect repository",
            )
            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated["bookkeeping"]["policySource"], "legacy compatibility")
        self.assertIsNone(updated["hostedReviewDecision"])

    def test_transition_rejects_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            checkpoint = checkpoint_path(directory, document)
            document["checkpointId"] = "b" * 64
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "explore",
                "--status",
                "active",
                "--next-action",
                "inspect repository",
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("filename must match", result.stderr)
        self.assertEqual(current, original)

    def test_transition_rejects_evidence_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            evidence = document["evidence"]
            if isinstance(evidence, dict):
                evidence["status"] = "complete"
                evidence["revision"] = "a" * 40
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "explore",
                "--status",
                "active",
                "--next-action",
                "inspect repository",
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("disabled evidence", result.stderr)
        self.assertEqual(current, original)

    def test_transition_rejects_wrong_typed_phase_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            if isinstance(workflow, dict):
                workflow["phase"] = []
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")
            result = self.run_script(
                "transition",
                "--checkpoint",
                str(checkpoint),
                "--phase",
                "explore",
                "--status",
                "active",
                "--next-action",
                "inspect repository",
            )
            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid workflow phase", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(current, original)


if __name__ == "__main__":
    unittest.main()
