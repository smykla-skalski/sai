"""Behavior tests for ship-it bookkeeping.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
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


def merged_delivery() -> dict[str, object]:
    return {
        "pullRequestUrl": "https://github.com/o/r/pull/1",
        "pullRequestHead": "a" * 40,
        "pullRequestState": "merged",
        "mergeCommit": "b" * 40,
        "mergedAt": "2026-01-02T03:04:05Z",
        "reconciliation": {
            "status": "matched",
            "checkedAt": "2026-01-02T03:05:06Z",
            "error": None,
        },
    }


class BookkeepingTest(unittest.TestCase):
    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_default_policy_enables_local_telemetry_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script("policy", "--repository", directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "claims": False,
                "evidence": False,
                "policySource": "bundled default",
                "telemetry": True,
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

    def test_repository_policy_disables_default_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".sai").mkdir()
            (root / ".sai/ship-it-bookkeeping.json").write_text(
                '{"telemetry":false}', encoding="utf-8"
            )
            result = self.run_script("policy", "--repository", directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "claims": False,
                "evidence": False,
                "policySource": ".sai/ship-it-bookkeeping.json",
                "telemetry": False,
            },
        )

    def test_merged_reconciliation_preserves_separate_audit_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            delivery = document["delivery"]
            if isinstance(workflow, dict):
                workflow.update(
                    {
                        "phase": "wait",
                        "status": "blocked",
                        "blocker": "cleanup audit pending",
                        "nextAction": "finish cleanup audit",
                    },
                )
            if isinstance(delivery, dict):
                delivery.update(
                    {
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "c" * 40,
                    },
                )
            document["gateVerdicts"] = [{"id": "review", "status": "passed"}]
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(json.dumps(document), encoding="utf-8")
            remote = {
                "url": "https://github.com/o/r/pull/1",
                "state": "MERGED",
                "headRefOid": "a" * 40,
                "mergeCommit": {"oid": "b" * 40},
                "mergedAt": "2026-01-02T03:04:05Z",
            }

            result = self.run_script(
                "reconcile-delivery",
                "--checkpoint",
                str(checkpoint),
                "--pull-request-json",
                json.dumps(remote),
            )

            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "merged")
        self.assertEqual(updated["delivery"]["pullRequestState"], "merged")
        self.assertEqual(updated["delivery"]["pullRequestHead"], "a" * 40)
        self.assertEqual(updated["delivery"]["mergeCommit"], "b" * 40)
        self.assertEqual(updated["delivery"]["mergedAt"], "2026-01-02T03:04:05Z")
        self.assertEqual(updated["workflow"]["status"], "blocked")
        self.assertEqual(updated["workflow"]["blocker"], "cleanup audit pending")
        self.assertEqual(
            updated["gateVerdicts"], [{"id": "review", "status": "passed"}]
        )
        self.assertIsNone(updated["outcome"])

    def test_reconciliation_distinguishes_open_and_closed_unmerged(self) -> None:
        for remote_state, expected in (
            ("OPEN", "open"),
            ("CLOSED", "closed-unmerged"),
        ):
            with (
                self.subTest(remote_state=remote_state),
                tempfile.TemporaryDirectory() as directory,
            ):
                document = checkpoint_document()
                checkpoint = checkpoint_path(directory, document)
                checkpoint.write_text(json.dumps(document), encoding="utf-8")
                result = self.run_script(
                    "reconcile-delivery",
                    "--checkpoint",
                    str(checkpoint),
                    "--pull-request-json",
                    json.dumps(
                        {
                            "url": "https://github.com/o/r/pull/1",
                            "state": remote_state,
                            "headRefOid": "a" * 40,
                            "mergeCommit": None,
                            "mergedAt": None,
                        },
                    ),
                )
                updated = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["result"], expected)
            self.assertEqual(updated["delivery"]["pullRequestState"], expected)

    def test_reconciliation_rejects_mismatched_pull_request_without_writing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            delivery = document["delivery"]
            if isinstance(delivery, dict):
                delivery["pullRequestUrl"] = "https://github.com/o/r/pull/1"
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")

            result = self.run_script(
                "reconcile-delivery",
                "--checkpoint",
                str(checkpoint),
                "--pull-request-json",
                json.dumps(
                    {
                        "url": "https://github.com/o/r/pull/2",
                        "state": "OPEN",
                        "headRefOid": "a" * 40,
                        "mergeCommit": None,
                        "mergedAt": None,
                    },
                ),
            )

            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("pull request identity mismatch", result.stderr)
        self.assertEqual(current, original)

    def test_reconciliation_rejects_malformed_remote_merge_facts(self) -> None:
        invalid_fields = {
            "headRefOid": "not-a-sha",
            "mergeCommit": {"oid": "also-not-a-sha"},
            "mergedAt": "yesterday",
        }
        for field, invalid in invalid_fields.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                document = checkpoint_document()
                checkpoint = checkpoint_path(directory, document)
                original = json.dumps(document)
                checkpoint.write_text(original, encoding="utf-8")
                remote = {
                    "url": "https://github.com/o/r/pull/1",
                    "state": "MERGED",
                    "headRefOid": "a" * 40,
                    "mergeCommit": {"oid": "b" * 40},
                    "mergedAt": "2026-01-02T03:04:05Z",
                }
                remote[field] = invalid

                result = self.run_script(
                    "reconcile-delivery",
                    "--checkpoint",
                    str(checkpoint),
                    "--pull-request-json",
                    json.dumps(remote),
                )

                current = checkpoint.read_text(encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertIn(field, result.stderr)
            self.assertEqual(current, original)

    def test_reconciliation_upgrades_completed_legacy_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            delivery = document["delivery"]
            if isinstance(workflow, dict):
                workflow.update(
                    phase="complete",
                    status="completed",
                    revision="a" * 40,
                    nextAction="none",
                )
            if isinstance(delivery, dict):
                delivery.update(
                    pullRequestUrl="https://github.com/o/r/pull/1",
                    pullRequestHead="a" * 40,
                    mergeCommit="b" * 40,
                )
            document["outcome"] = {
                "result": "merged",
                "pullRequestUrl": "https://github.com/o/r/pull/1",
                "pullRequestHead": "a" * 40,
                "mergeCommit": "b" * 40,
                "sourceState": "closed",
                "branchCleanup": "deleted",
                "completedAt": "2026-01-02T03:06:00Z",
            }
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(json.dumps(document), encoding="utf-8")

            result = self.run_script(
                "reconcile-delivery",
                "--checkpoint",
                str(checkpoint),
                "--pull-request-json",
                json.dumps(
                    {
                        "url": "https://github.com/o/r/pull/1",
                        "state": "MERGED",
                        "headRefOid": "a" * 40,
                        "mergeCommit": {"oid": "b" * 40},
                        "mergedAt": "2026-01-02T03:04:05Z",
                    }
                ),
            )

            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated["delivery"]["pullRequestState"], "merged")
        self.assertEqual(updated["delivery"]["mergedAt"], "2026-01-02T03:04:05Z")
        self.assertEqual(updated["delivery"]["reconciliation"]["status"], "matched")
        self.assertEqual(updated["workflow"]["status"], "completed")
        self.assertEqual(updated["outcome"]["result"], "merged")

    def test_unreachable_reconciliation_preserves_confirmed_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            delivery = document["delivery"]
            if isinstance(delivery, dict):
                delivery.update(
                    {
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "a" * 40,
                        "mergeCommit": "b" * 40,
                        "mergedAt": "2026-01-02T03:04:05Z",
                        "pullRequestState": "merged",
                        "reconciliation": None,
                    },
                )
            checkpoint = checkpoint_path(directory, document)
            checkpoint.write_text(json.dumps(document), encoding="utf-8")

            result = self.run_script(
                "reconcile-delivery",
                "--checkpoint",
                str(checkpoint),
                "--failure",
                "GitHub API unavailable",
            )

            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "unreachable")
        self.assertEqual(updated["delivery"]["pullRequestState"], "merged")
        self.assertEqual(updated["delivery"]["mergeCommit"], "b" * 40)
        self.assertEqual(updated["delivery"]["mergedAt"], "2026-01-02T03:04:05Z")
        self.assertEqual(updated["delivery"]["reconciliation"]["status"], "unreachable")

    def test_reconciliation_never_downgrades_confirmed_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            delivery = document["delivery"]
            if isinstance(delivery, dict):
                delivery.update(
                    {
                        "pullRequestUrl": "https://github.com/o/r/pull/1",
                        "pullRequestHead": "a" * 40,
                        "mergeCommit": "b" * 40,
                        "mergedAt": "2026-01-02T03:04:05Z",
                        "pullRequestState": "merged",
                        "reconciliation": None,
                    },
                )
            checkpoint = checkpoint_path(directory, document)
            original = json.dumps(document)
            checkpoint.write_text(original, encoding="utf-8")

            result = self.run_script(
                "reconcile-delivery",
                "--checkpoint",
                str(checkpoint),
                "--pull-request-json",
                json.dumps(
                    {
                        "url": "https://github.com/o/r/pull/1",
                        "state": "CLOSED",
                        "headRefOid": "a" * 40,
                        "mergeCommit": None,
                        "mergedAt": None,
                    },
                ),
            )

            current = checkpoint.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("confirmed merged delivery conflicts", result.stderr)
        self.assertEqual(current, original)

    def test_resumed_transition_preserves_scoped_reply_and_consumed_limits(
        self,
    ) -> None:
        for status in ("active", "ambiguous", "revoked", "exhausted"):
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory() as directory,
            ):
                document = checkpoint_document()
                authorization = {
                    "grants": [
                        {
                            "id": "one-extra-gate",
                            "source": {
                                "kind": "user-reply",
                                "message": "I approve",
                                "request": "Run one additional acceptance gate?",
                                "reference": "original conversation reply 17",
                            },
                            "scope": ["one additional acceptance gate"],
                            "limits": [
                                {"resource": "gate runs", "maximum": 1, "used": 1}
                            ],
                            "status": status,
                            "futureField": "preserve",
                        }
                    ]
                }
                document["authorization"] = authorization
                checkpoint = checkpoint_path(directory, document)
                checkpoint.write_text(json.dumps(document), encoding="utf-8")

                result = self.run_script(
                    "transition",
                    "--checkpoint",
                    str(checkpoint),
                    "--phase",
                    "review",
                    "--status",
                    "active",
                    "--next-action",
                    "reconcile original authorization before dispatch",
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                updated = json.loads(checkpoint.read_text(encoding="utf-8"))
                self.assertEqual(updated["authorization"], authorization)

    def test_legacy_transition_does_not_invent_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
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
                "recover original user request",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(updated["authorization"], {"grants": []})

    def test_invalid_authority_leaves_original_checkpoint_unchanged(self) -> None:
        cases = (
            ("null record", None),
            ("missing grants", {}),
            (
                "summary-only source",
                {
                    "grants": [
                        {
                            "id": "summary",
                            "status": "active",
                            "source": {
                                "kind": "coordinator",
                                "message": "approved",
                                "reference": "summary",
                                "request": None,
                            },
                            "scope": ["ship"],
                            "limits": [],
                        }
                    ]
                },
            ),
            (
                "reply without request",
                {
                    "grants": [
                        {
                            "id": "reply",
                            "status": "active",
                            "source": {
                                "kind": "user-reply",
                                "message": "I approve",
                                "reference": "message 17",
                                "request": None,
                            },
                            "scope": ["ship"],
                            "limits": [],
                        }
                    ]
                },
            ),
            (
                "overspent user limit",
                {
                    "grants": [
                        {
                            "id": "reply",
                            "status": "exhausted",
                            "source": {
                                "kind": "user-request",
                                "message": "one gate",
                                "reference": "message 17",
                                "request": None,
                            },
                            "scope": ["one gate"],
                            "limits": [
                                {"resource": "gate runs", "maximum": 1, "used": 2}
                            ],
                        }
                    ]
                },
            ),
        )
        for name, authorization in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                document = checkpoint_document()
                document["authorization"] = authorization
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
                    "reconcile authority",
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(checkpoint.read_text(encoding="utf-8"), original)

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
                delivery.update(merged_delivery())
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

    def test_complete_transition_rejects_outcome_that_differs_from_delivery(
        self,
    ) -> None:
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
                    delivery.update(merged_delivery())
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

    def test_complete_transition_rejects_head_that_differs_from_workflow_revision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            document = checkpoint_document()
            workflow = document["workflow"]
            delivery = document["delivery"]
            if isinstance(workflow, dict):
                workflow["revision"] = "c" * 40
            if isinstance(delivery, dict):
                delivery.update(merged_delivery())
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

    def test_complete_transition_requires_reconciled_merged_delivery(self) -> None:
        missing_states = {
            "pull request state": {"pullRequestState": None},
            "merge timestamp": {"mergedAt": None},
            "matched reconciliation": {"reconciliation": None},
        }
        for name, replacement in missing_states.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                document = checkpoint_document()
                workflow = document["workflow"]
                delivery = document["delivery"]
                if isinstance(workflow, dict):
                    workflow["revision"] = "a" * 40
                if isinstance(delivery, dict):
                    delivery.update(merged_delivery())
                    delivery.update(replacement)
                checkpoint = checkpoint_path(directory, document)
                original = json.dumps(document)
                checkpoint.write_text(original, encoding="utf-8")
                outcome = {
                    "result": "merged",
                    "pullRequestUrl": "https://github.com/o/r/pull/1",
                    "pullRequestHead": "a" * 40,
                    "mergeCommit": "b" * 40,
                    "sourceState": "closed",
                    "branchCleanup": "preserved",
                    "completedAt": "2026-01-02T03:06:07Z",
                }

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


class UsageDocstringTest(unittest.TestCase):
    def test_docstring_lists_every_command(self) -> None:
        help_text = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        match = re.search(r"\{([a-z-]+(?:,[a-z-]+)+)\}", help_text)
        self.assertIsNotNone(match)
        commands = match.group(1).split(",") if match else []
        docstring = ast.get_docstring(ast.parse(SCRIPT.read_text())) or ""
        for command in commands:
            with self.subTest(command=command):
                self.assertIn(f"  bookkeeping.py {command} ", docstring)


if __name__ == "__main__":
    unittest.main()
