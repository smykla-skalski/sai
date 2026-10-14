"""Exercise convergence reservations through the actual cross-harness CLI.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from test_ship_it_bookkeeping import SCRIPT, checkpoint_document, checkpoint_path


class ReservationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.document = checkpoint_document()
        self.document["workflow"]["revision"] = "a" * 40
        self.document["authorization"] = {
            "grants": [
                {
                    "id": "ship",
                    "source": {
                        "kind": "user-request",
                        "message": "ship this",
                        "reference": "user:1",
                        "request": None,
                    },
                    "scope": ["Ship acceptance criteria"],
                    "limits": [],
                    "status": "active",
                }
            ]
        }
        self.path = checkpoint_path(self.directory.name, self.document)
        self.write(self.document)

    def write(self, document: dict) -> None:
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def reserve(
        self,
        identity: str,
        kind: str = "review",
        inputs: str = "affected-files:initial",
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return self.cli(
            "reserve",
            "--checkpoint",
            str(self.path),
            "--id",
            identity,
            "--kind",
            kind,
            "--revision",
            "a" * 40,
            "--inputs",
            inputs,
            *extra,
        )

    def finish(self, identity: str, result: dict) -> subprocess.CompletedProcess[str]:
        return self.cli(
            "finish",
            "--checkpoint",
            str(self.path),
            "--id",
            identity,
            "--result-json",
            json.dumps(result),
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_denied(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_concurrent_duplicate_reserves_have_one_dispatch_receipt(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.reserve("one"), range(8)))
        receipts = [self.assert_ok(result) for result in results]
        self.assertEqual(sum(receipt["dispatch"] for receipt in receipts), 1)
        self.assertEqual(self.read()["convergence"]["reviewCycles"], 1)
        self.assertEqual(len(self.read()["convergence"]["reservations"]), 1)

    def test_concurrent_distinct_fix_batches_cannot_spend_twice(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(lambda number: self.reserve(f"fix-{number}", "fix"), range(8))
            )
        self.assertEqual(sum(result.returncode == 0 for result in results), 1)
        self.assertEqual(self.read()["convergence"]["fixPasses"], 1)
        for result in results:
            if result.returncode:
                self.assert_denied(result)

    def test_crash_before_finish_and_cross_harness_resume_preserve_consumption(
        self,
    ) -> None:
        self.assert_ok(self.reserve("one", "quality"))
        original = self.read()["convergence"]
        self.assert_ok(
            self.cli(
                "transition",
                "--checkpoint",
                str(self.path),
                "--phase",
                "review",
                "--status",
                "active",
                "--next-action",
                "resume in another harness",
            )
        )
        self.assertEqual(self.read()["convergence"], original)
        self.assertFalse(self.assert_ok(self.reserve("one", "quality"))["dispatch"])
        self.assert_denied(
            self.reserve(
                "another", "quality", "changed", "--reason", "new affected files"
            )
        )

    def test_retry_with_changed_request_is_rejected_without_state_change(self) -> None:
        self.assert_ok(self.reserve("one"))
        before = self.path.read_bytes()
        self.assert_denied(self.reserve("one", inputs="different"))
        self.assertEqual(self.path.read_bytes(), before)

    def test_completion_is_idempotent_and_consumes_no_extra_allowance(self) -> None:
        self.assert_ok(self.reserve("one"))
        result = {"verdict": "passed", "findings": []}
        self.assert_ok(self.finish("one", result))
        self.assertEqual(
            self.assert_ok(self.finish("one", result))["completion"], "already-recorded"
        )
        self.assertEqual(self.read()["convergence"]["reviewCycles"], 1)
        self.assert_denied(self.finish("one", {"verdict": "failed", "findings": []}))

    def test_second_review_needs_changed_relevant_inputs_and_severity_trigger(
        self,
    ) -> None:
        self.assert_ok(self.reserve("one"))
        self.assert_ok(self.finish("one", {"verdict": "passed", "findings": []}))
        self.assert_denied(
            self.reserve(
                "two", "review", "changed", "--reason", "fixed acceptance defect"
            )
        )
        self.assert_denied(
            self.reserve(
                "two",
                "review",
                "affected-files:initial",
                "--trigger",
                "security",
                "--reason",
                "security correction",
            )
        )
        self.assert_ok(
            self.reserve(
                "two",
                "review",
                "changed",
                "--trigger",
                "security",
                "--reason",
                "security correction",
            )
        )
        self.assert_denied(
            self.reserve(
                "three",
                "review",
                "third",
                "--trigger",
                "security",
                "--reason",
                "another correction",
            )
        )

    def test_elapsed_limit_rejects_broad_review_but_allows_remaining_quality_gate(
        self,
    ) -> None:
        self.assert_ok(self.reserve("one"))
        doc = self.read()
        doc["convergence"]["startedAt"] = "2020-01-01T00:00:00Z"
        self.write(doc)
        self.assert_denied(
            self.reserve(
                "two",
                "review",
                "changed",
                "--trigger",
                "security",
                "--reason",
                "security correction",
            )
        )
        self.assert_ok(self.reserve("quality", "quality"))

    def test_explicit_limit_consumes_before_dispatch_and_survives_resume(self) -> None:
        doc = self.read()
        doc["authorization"]["grants"][0]["limits"] = [
            {"resource": "fixPasses", "maximum": 1, "used": 0}
        ]
        self.write(doc)
        self.assert_ok(self.reserve("fix", "fix"))
        self.assertEqual(
            self.read()["authorization"]["grants"][0]["limits"][0]["used"], 1
        )
        self.assertFalse(self.assert_ok(self.reserve("fix", "fix"))["dispatch"])
        self.assert_denied(self.reserve("fix-again", "fix"))

    def test_one_scoped_extra_gate_spends_once_and_never_authorizes_a_loop(
        self,
    ) -> None:
        self.assert_ok(self.reserve("one"))
        self.assert_ok(self.finish("one", {"verdict": "passed", "findings": []}))
        doc = self.read()
        doc["authorization"]["grants"].append(
            {
                "id": "extra",
                "source": {
                    "kind": "user-reply",
                    "message": "yes",
                    "request": "One additional review",
                    "reference": "user:2",
                },
                "scope": ["reviewCycles"],
                "limits": [{"resource": "reviewCycles", "maximum": 1, "used": 0}],
                "status": "active",
            }
        )
        self.write(doc)
        self.assert_ok(self.reserve("two", "review", "unchanged", "--grant", "extra"))
        self.assertFalse(
            self.assert_ok(
                self.reserve("two", "review", "unchanged", "--grant", "extra")
            )["dispatch"]
        )
        self.assert_denied(
            self.reserve("three", "review", "unchanged", "--grant", "extra")
        )
        self.assertEqual(
            self.read()["authorization"]["grants"][1]["limits"][0]["used"], 1
        )

    def test_empty_limits_and_coordinator_sources_cannot_extend_optional_budget(
        self,
    ) -> None:
        self.assert_ok(self.reserve("one", "fix"))
        self.assert_denied(self.reserve("two", "fix", "changed", "--grant", "ship"))
        doc = self.read()
        doc["authorization"]["grants"][0]["source"]["kind"] = "coordinator"
        self.write(doc)
        self.assert_denied(self.reserve("two", "fix", "changed", "--grant", "ship"))

    def test_revoked_ambiguous_and_exhausted_grants_do_not_authorize_dispatch(
        self,
    ) -> None:
        for status in ("revoked", "ambiguous", "exhausted"):
            with self.subTest(status=status):
                doc = self.read()
                doc["authorization"]["grants"][0]["status"] = status
                self.write(doc)
                self.assert_denied(self.reserve("one"))

    def test_second_severe_review_blocks_with_named_reassessment(self) -> None:
        self.assert_ok(self.reserve("one"))
        self.assert_ok(self.finish("one", {"verdict": "passed", "findings": []}))
        self.assert_ok(
            self.reserve(
                "two",
                "review",
                "changed",
                "--trigger",
                "security",
                "--reason",
                "security correction",
            )
        )
        finding = {
            "id": "F1",
            "label": "blocking",
            "location": "script.py:4",
            "summary": "Confirmed destructive race",
            "category": "destructive-concurrency",
            "disposition": "open",
        }
        self.assert_ok(self.finish("two", {"verdict": "failed", "findings": [finding]}))
        doc = self.read()
        self.assertEqual(doc["workflow"]["status"], "blocked")
        self.assertIn("Reassess scope or design", doc["workflow"]["nextAction"])
        self.assertEqual(doc["convergence"]["reassessment"]["findings"], ["F1"])
        self.assert_denied(self.reserve("another", "quality"))

    def test_full_quality_crash_is_spent_before_it_starts(self) -> None:
        self.assert_ok(self.reserve("quality", "quality"))
        self.assertEqual(self.read()["convergence"]["fullQualityGateRuns"], 1)
        self.assert_ok(self.finish("quality", {"verdict": "failed"}))
        self.assert_denied(
            self.reserve("again", "quality", "changed", "--reason", "routine fix")
        )

    def test_broad_test_requires_clean_review_for_current_revision(self) -> None:
        self.assert_denied(self.reserve("test", "test"))
        doc = self.read()
        doc["gateVerdicts"] = [
            {"gate": "adversarial-review", "revision": "a" * 40, "status": "passed"}
        ]
        self.write(doc)
        self.assert_ok(self.reserve("test", "test"))
        self.assert_denied(
            self.reserve("test-again", "test", "changed", "--reason", "routine fix")
        )

    def test_malformed_counters_fail_cleanly_without_rewriting_state(self) -> None:
        for value in (True, -1, "1", None):
            with self.subTest(value=value):
                doc = self.document.copy()
                doc["convergence"] = {"reviewCycles": value}
                self.write(doc)
                before = self.path.read_bytes()
                self.assert_denied(self.reserve("one"))
                self.assertEqual(self.path.read_bytes(), before)

    def test_old_spent_review_without_revision_evidence_requires_recovery(self) -> None:
        doc = self.read()
        doc["convergence"] = {"reviewCycles": 1}
        self.write(doc)
        result = self.reserve("two")
        self.assert_denied(result)
        self.assertIn("recover revision-bound", result.stderr)

    def test_unrecorded_overspent_bounded_counter_is_rejected(self) -> None:
        doc = self.read()
        doc["convergence"] = {"fixPasses": 99}
        self.write(doc)
        self.assert_denied(self.reserve("one", "fix"))

    def test_enabled_evidence_cannot_bypass_review_clean_prerequisite(self) -> None:
        doc = self.read()
        doc["bookkeeping"]["evidence"] = True
        doc["evidence"]["status"] = "missing"
        self.write(doc)
        self.assert_denied(self.reserve("test", "test"))

    def test_extension_cannot_override_original_explicit_user_limit(self) -> None:
        doc = self.read()
        doc["authorization"]["grants"][0]["limits"] = [
            {"resource": "reviewCycles", "maximum": 0, "used": 0}
        ]
        doc["authorization"]["grants"].append(
            {
                "id": "extra",
                "source": {
                    "kind": "user-reply",
                    "message": "yes",
                    "request": "One more review",
                    "reference": "user:2",
                },
                "scope": ["reviewCycles"],
                "limits": [{"resource": "reviewCycles", "maximum": 1, "used": 0}],
                "status": "active",
            }
        )
        self.write(doc)
        before = self.path.read_bytes()
        self.assert_denied(self.reserve("one", "review", "same", "--grant", "extra"))
        self.assertEqual(self.path.read_bytes(), before)

    def test_reserved_state_is_owner_only_and_original_backup_retained(self) -> None:
        original = self.path.read_bytes()
        self.assert_ok(self.reserve("one"))
        self.assertEqual(self.path.with_suffix(".json.bak").read_bytes(), original)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            self.path.with_suffix(".json.lock").stat().st_mode & 0o777, 0o600
        )


if __name__ == "__main__":
    unittest.main()
