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
from datetime import UTC, datetime

from test_ship_it_bookkeeping import SCRIPT, checkpoint_document, checkpoint_path


class ReservationFixture(unittest.TestCase):
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
        outcome = self.cli(
            "finish",
            "--checkpoint",
            str(self.path),
            "--id",
            identity,
            "--result-json",
            json.dumps(result),
        )
        state = self.read()
        receipt = next(
            item
            for item in state["convergence"]["reservations"]
            if item["id"] == identity
        )
        if (
            outcome.returncode == 0
            and receipt["kind"] in {"review", "test"}
            and not any(
                item["target"].get("reservationId") == identity
                for item in state.get("workerRecovery", [])
            )
        ):
            self.settle_command_only_fixture(identity)
        return outcome

    def settle_command_only_fixture(self, identity: str) -> None:
        at = datetime.now(UTC).isoformat()
        for kind, data in (
            (
                "adopt",
                {
                    "target": {"reservationId": identity},
                    "owner": None,
                    "deadlineAt": None,
                },
            ),
            (
                "release-owner",
                {
                    "hostStatus": "not-created",
                    "observation": "CLI unit fixture launches no native worker",
                },
            ),
        ):
            self.assert_ok(
                self.cli(
                    "record-worker-event",
                    "--checkpoint",
                    str(self.path),
                    "--event-json",
                    json.dumps(
                        {"dispatchId": identity, "kind": kind, "at": at, "data": data}
                    ),
                )
            )

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_denied(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class ReservationTest(ReservationFixture):
    def test_concurrent_duplicate_reserves_have_one_dispatch_receipt(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.reserve("one"), range(8)))
        receipts = [self.assert_ok(result) for result in results]
        self.assertEqual(sum(receipt["dispatch"] for receipt in receipts), 1)
        self.assertEqual(self.read()["convergence"]["reviewCycles"], 1)
        self.assertEqual(len(self.read()["convergence"]["reservations"]), 1)

    def test_finished_gate_cannot_redispatch_while_worker_owner_is_unknown(
        self,
    ) -> None:
        self.assert_ok(self.reserve("review-one"))
        event = {
            "dispatchId": "gate-worker-one",
            "kind": "register",
            "at": "2026-10-15T21:00:00Z",
            "data": {
                "target": {"reservationId": "review-one"},
                "owner": "native-reviewer-one",
                "deadlineAt": "2026-10-15T22:00:00Z",
            },
        }
        self.assert_ok(
            self.cli(
                "record-worker-event",
                "--checkpoint",
                str(self.path),
                "--event-json",
                json.dumps(event),
            )
        )
        self.assert_ok(self.finish("review-one", {"verdict": "passed", "findings": []}))
        self.assert_denied(
            self.reserve(
                "review-two",
                "review",
                "changed-inputs",
                "--reason",
                "changed acceptance inputs",
            )
        )
        self.assertFalse(self.assert_ok(self.reserve("review-one"))["dispatch"])

    def test_legacy_gate_needs_native_owner_reconciliation_before_another_attempt(
        self,
    ) -> None:
        self.assert_ok(self.reserve("legacy-review"))
        self.assert_ok(
            self.cli(
                "finish",
                "--checkpoint",
                str(self.path),
                "--id",
                "legacy-review",
                "--result-json",
                '{"verdict":"passed","findings":[]}',
            )
        )
        retry = (
            "next-review",
            "review",
            "changed",
            "--reason",
            "Changed inputs",
            "--trigger",
            "security",
        )
        before = self.read()
        self.assert_denied(self.reserve(*retry))
        self.assertEqual(before, self.read())
        self.settle_command_only_fixture("legacy-review")
        reconciled = self.read()
        for field in ("authorization", "gateVerdicts", "convergence"):
            self.assertEqual(before[field], reconciled[field])
        self.assertTrue(self.assert_ok(self.reserve(*retry))["dispatch"])

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

    def test_completed_receipt_requires_result_before_finish_or_resume(self) -> None:
        self.assert_ok(self.reserve("quality", "quality"))
        self.assert_ok(self.finish("quality", {"verdict": "passed"}))
        original = self.read()
        for invalid in ("missing", None, {}, {"verdict": "unknown"}, "passed"):
            with self.subTest(invalid=invalid):
                doc = json.loads(json.dumps(original))
                receipt = doc["convergence"]["reservations"][0]
                if invalid == "missing":
                    receipt.pop("result")
                else:
                    receipt["result"] = invalid
                self.write(doc)
                before = self.path.read_bytes()
                self.assert_denied(self.finish("quality", {"verdict": "passed"}))
                self.assert_denied(
                    self.cli(
                        "transition",
                        "--checkpoint",
                        str(self.path),
                        "--phase",
                        "test",
                        "--status",
                        "active",
                        "--next-action",
                        "resume",
                    )
                )
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.read()["convergence"]["fullQualityGateRuns"], 1)

    def test_reserved_receipt_cannot_claim_completed_result(self) -> None:
        self.assert_ok(self.reserve("quality", "quality"))
        doc = self.read()
        doc["convergence"]["reservations"][0]["result"] = {"verdict": "passed"}
        self.write(doc)
        self.assert_denied(self.finish("quality", {"verdict": "passed"}))

    def test_scoped_user_limits_bind_ordinary_reservations(self) -> None:
        for maximum in (0, 1):
            with self.subTest(maximum=maximum):
                self.document["authorization"]["grants"][0].update(
                    scope=["reviewCycles"],
                    limits=[
                        {"resource": "reviewCycles", "maximum": maximum, "used": 0}
                    ],
                )
                self.write(self.document)
                if maximum:
                    self.assert_ok(self.reserve("first"))
                    self.assertEqual(
                        self.read()["authorization"]["grants"][0]["limits"][0]["used"],
                        1,
                    )
                    self.assert_ok(
                        self.finish("first", {"verdict": "passed", "findings": []})
                    )
                self.assert_denied(
                    self.reserve(
                        "second",
                        "review",
                        "changed",
                        "--trigger",
                        "security",
                        "--reason",
                        "security correction",
                    )
                )
                self.assertEqual(
                    self.read()["authorization"]["grants"][0]["limits"][0]["used"],
                    maximum,
                )

    def test_legacy_null_review_evidence_without_receipt_blocks_transition(
        self,
    ) -> None:
        doc = self.read()
        doc["convergence"] = {
            "reviewCycles": 1,
            "startedAt": "2026-01-01T00:00:00Z",
            "reviewedRevision": None,
            "findings": [],
            "reservations": [],
        }
        self.write(doc)
        before = self.path.read_bytes()
        result = self.cli(
            "transition",
            "--checkpoint",
            str(self.path),
            "--phase",
            "test",
            "--status",
            "active",
            "--next-action",
            "resume testing",
        )
        self.assert_denied(result)
        self.assertIn("recover revision-bound", result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

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

    def append_test_grant(self, identity: str, maximum: int = 1) -> None:
        doc = self.read()
        doc["authorization"]["grants"].append(
            {
                "id": identity,
                "source": {
                    "kind": "user-reply",
                    "message": "yes",
                    "request": "One more adversarial test",
                    "reference": f"user:{identity}",
                },
                "scope": ["broadTestRuns"],
                "limits": [
                    {"resource": "broadTestRuns", "maximum": maximum, "used": 0}
                ],
                "status": "active",
            }
        )
        self.write(doc)

    def spend_routine_and_first_extra_test(self) -> None:
        doc = self.read()
        doc["gateVerdicts"] = [
            {"gate": "adversarial-review", "revision": "a" * 40, "status": "passed"}
        ]
        self.write(doc)
        self.assert_ok(self.reserve("test-1", "test"))
        self.assert_ok(self.finish("test-1", {"verdict": "failed"}))
        self.append_test_grant("G3")
        self.assert_ok(self.reserve("test-2", "test", "same", "--grant", "G3"))
        self.assert_ok(self.finish("test-2", {"verdict": "failed"}))

    def grant_limits(self) -> dict[str, list[dict]]:
        return {
            grant["id"]: grant["limits"]
            for grant in self.read()["authorization"]["grants"]
        }

    def test_later_named_grant_supersedes_spent_earlier_limit(self) -> None:
        self.spend_routine_and_first_extra_test()
        self.append_test_grant("G4")
        receipt = self.assert_ok(
            self.reserve("test-3", "test", "same", "--grant", "G4")
        )
        self.assertTrue(receipt["dispatch"])
        state = self.read()
        g3 = state["authorization"]["grants"][1]
        self.assertEqual(g3["id"], "G3")
        self.assertEqual(g3["status"], "active")
        self.assertEqual(
            g3["limits"], [{"resource": "broadTestRuns", "maximum": 1, "used": 1}]
        )
        self.assertEqual(self.grant_limits()["G4"][0]["used"], 1)
        self.assertEqual(state["convergence"]["broadTestRuns"], 3)
        self.assertEqual(state["convergence"]["authorizedBy"], "G4")

    def test_spent_later_grant_and_unnamed_reservation_stay_refused(self) -> None:
        self.spend_routine_and_first_extra_test()
        self.append_test_grant("G4")
        self.assert_ok(self.reserve("test-3", "test", "same", "--grant", "G4"))
        self.assert_ok(self.finish("test-3", {"verdict": "failed"}))
        before = self.path.read_bytes()
        for extra in (
            ("--grant", "G4"),
            ("--grant", "G3"),
            ("--reason", "routine fix"),
        ):
            with self.subTest(extra=extra):
                self.assert_denied(self.reserve("test-4", "test", "changed", *extra))
                self.assertEqual(self.path.read_bytes(), before)

    def test_unnamed_reservation_stays_bound_by_spent_grant_limit(self) -> None:
        doc = self.read()
        doc["authorization"]["grants"].append(
            {
                "id": "G3",
                "source": {
                    "kind": "user-reply",
                    "message": "yes",
                    "request": "One more quality run",
                    "reference": "user:G3",
                },
                "scope": ["fullQualityGateRuns"],
                "limits": [
                    {"resource": "fullQualityGateRuns", "maximum": 1, "used": 1}
                ],
                "status": "active",
            }
        )
        self.write(doc)
        before = self.path.read_bytes()
        result = self.reserve("quality", "quality")
        self.assert_denied(result)
        self.assertIn("explicit user fullQualityGateRuns limit", result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_earlier_zero_cap_still_binds_a_later_named_grant(self) -> None:
        self.spend_routine_and_first_extra_test()
        self.append_test_grant("G4", maximum=0)
        self.append_test_grant("G5")
        before = self.path.read_bytes()
        self.assert_denied(self.reserve("test-3", "test", "same", "--grant", "G5"))
        self.assertEqual(self.path.read_bytes(), before)

    def test_named_grant_still_charges_earlier_limit_with_room(self) -> None:
        self.spend_routine_and_first_extra_test()
        self.append_test_grant("G4", maximum=2)
        self.append_test_grant("G5")
        self.assert_ok(self.reserve("test-3", "test", "same", "--grant", "G5"))
        limits = self.grant_limits()
        self.assertEqual(
            [limits[name][0]["used"] for name in ("G3", "G4", "G5")], [1, 1, 1]
        )

    def test_reserved_state_is_owner_only_and_original_backup_retained(self) -> None:
        original = self.path.read_bytes()
        self.assert_ok(self.reserve("one"))
        self.assertEqual(self.path.with_suffix(".json.bak").read_bytes(), original)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            self.path.with_suffix(".json.lock").stat().st_mode & 0o777, 0o600
        )


SEVERE_FINDING = {
    "id": "F1",
    "label": "blocking",
    "location": "script.py:4",
    "summary": "Confirmed destructive race",
    "category": "destructive-concurrency",
    "disposition": "open",
}
FOLLOW_UP = "https://github.com/owner/repo/issues/9"


class ReassessmentResolutionTest(ReservationFixture):
    def setUp(self) -> None:
        super().setUp()
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
        self.assert_ok(
            self.finish("two", {"verdict": "failed", "findings": [SEVERE_FINDING]})
        )
        self.add_grant("decision", ["reassessment"])

    def add_grant(
        self, identity: str, scope: list[str], status: str = "active"
    ) -> None:
        grant = {
            "id": identity,
            "source": {
                "kind": "user-reply",
                "message": "Ship it with a follow-up issue",
                "reference": f"user:{identity}",
                "request": "Reassess the severe findings",
            },
            "scope": scope,
            "limits": [],
            "status": status,
        }
        self.assert_ok(
            self.cli(
                "add-grant",
                "--checkpoint",
                str(self.path),
                "--grant-json",
                json.dumps(grant),
            )
        )

    def resolve(self, resolution: dict) -> subprocess.CompletedProcess[str]:
        return self.cli(
            "resolve-reassessment",
            "--checkpoint",
            str(self.path),
            "--resolution-json",
            json.dumps(resolution),
        )

    def resolution(self, **changes: object) -> dict:
        return {
            "grantId": "decision",
            "decision": "Ship with a follow-up issue",
            "revision": "a" * 40,
            "findings": [
                {"id": "F1", "disposition": "follow-up", "followUpIssue": FOLLOW_UP}
            ],
            **changes,
        }

    def test_owner_decision_unblocks_without_new_budget(self) -> None:
        before = self.read()
        result = self.assert_ok(self.resolve(self.resolution()))
        self.assertTrue(result["applied"])
        after = self.read()
        self.assertIsNone(after["convergence"]["reassessment"])
        self.assertEqual(after["workflow"]["status"], "active")
        self.assertIsNone(after["workflow"]["blocker"])
        (entry,) = after["convergence"]["reassessmentResolutions"]
        self.assertEqual(entry["reassessment"], before["convergence"]["reassessment"])
        self.assertEqual(entry["grantId"], "decision")
        self.assertEqual(
            after["convergence"]["findings"][0]["disposition"], "follow-up"
        )
        self.assertEqual(after["convergence"]["followUpIssues"], [FOLLOW_UP])
        for field in (
            "reviewCycles",
            "fixPasses",
            "fullQualityGateRuns",
            "broadTestRuns",
            "reservations",
        ):
            self.assertEqual(after["convergence"][field], before["convergence"][field])
        self.assertEqual(after["authorization"], before["authorization"])
        self.assert_denied(
            self.reserve("three", "review", "changed-again", "--trigger", "security")
        )
        self.assertTrue(self.assert_ok(self.reserve("quality", "quality"))["dispatch"])

    def test_retry_is_idempotent_and_history_is_kept(self) -> None:
        self.assert_ok(self.resolve(self.resolution()))
        first = self.read()
        retry = self.assert_ok(self.resolve(self.resolution()))
        self.assertFalse(retry["applied"])
        second = self.read()
        first.pop("updatedAt")
        second.pop("updatedAt")
        self.assertEqual(first, second)
        self.assert_denied(self.resolve(self.resolution(decision="Something else")))

    def test_fixed_disposition_needs_a_new_revision(self) -> None:
        fixed = {"findings": [{"id": "F1", "disposition": "fixed"}]}
        self.assert_denied(self.resolve(self.resolution(**fixed)))
        doc = self.read()
        doc["workflow"]["revision"] = "b" * 40
        self.write(doc)
        self.assert_denied(self.resolve(self.resolution(**fixed)))
        self.assert_ok(self.resolve(self.resolution(revision="b" * 40, **fixed)))
        after = self.read()
        self.assertEqual(after["convergence"]["findings"][0]["disposition"], "fixed")
        self.assertEqual(after["convergence"]["followUpIssues"], [])

    def test_refuses_without_scoped_authority_or_complete_dispositions(self) -> None:
        self.add_grant("revoked", ["reassessment"], status="revoked")
        before = self.path.read_bytes()
        for resolution in (
            self.resolution(grantId="ship"),
            self.resolution(grantId="revoked"),
            self.resolution(grantId="missing"),
            self.resolution(revision="b" * 40),
            self.resolution(decision=" "),
            self.resolution(findings=[]),
            self.resolution(findings=[{"id": "F1", "disposition": "open"}]),
            self.resolution(findings=[{"id": "F1", "disposition": "follow-up"}]),
            self.resolution(
                findings=[
                    {"id": "F1", "disposition": "follow-up", "followUpIssue": "x"}
                ]
            ),
            self.resolution(
                findings=[
                    {
                        "id": "F1",
                        "disposition": "follow-up",
                        "followUpIssue": FOLLOW_UP,
                    },
                    {
                        "id": "F2",
                        "disposition": "follow-up",
                        "followUpIssue": FOLLOW_UP,
                    },
                ]
            ),
            self.resolution(findings=[{"id": 1, "disposition": "fixed"}]),
            self.resolution(extra=True),
            {"grantId": "decision"},
        ):
            with self.subTest(resolution=resolution):
                self.assert_denied(self.resolve(resolution))
                self.assertEqual(self.path.read_bytes(), before)

    def test_refuses_when_no_reassessment_is_pending(self) -> None:
        doc = self.read()
        doc["convergence"]["reassessment"] = None
        self.write(doc)
        self.assert_denied(self.resolve(self.resolution()))


class ClosedGateOwnerTest(ReservationFixture):
    def event(self, dispatch: str, kind: str, at: str, data: dict) -> dict:
        return self.assert_ok(self.send(dispatch, kind, at, data))

    def send(
        self, dispatch: str, kind: str, at: str, data: dict
    ) -> subprocess.CompletedProcess[str]:
        return self.cli(
            "record-worker-event",
            "--checkpoint",
            str(self.path),
            "--event-json",
            json.dumps({"dispatchId": dispatch, "kind": kind, "at": at, "data": data}),
        )

    def setUp(self) -> None:
        super().setUp()
        self.assert_ok(self.reserve("review-one"))
        self.event(
            "gate-one",
            "register",
            "2026-10-15T21:00:00Z",
            {
                "target": {"reservationId": "review-one"},
                "owner": None,
                "deadlineAt": "2026-10-15T22:00:00Z",
            },
        )
        self.release = {
            "owner": "native-reviewer-one",
            "hostStatus": "exited",
            "observation": "host task list: native-reviewer-one exited 0",
        }
        self.next_review = (
            "review-two",
            "review",
            "changed",
            "--reason",
            "changed inputs",
            "--trigger",
            "security",
        )

    def test_finished_unbound_gate_records_owner_and_release(self) -> None:
        self.assert_denied(
            self.send(
                "gate-one",
                "release-closed-gate",
                "2026-10-15T21:20:00Z",
                self.release,
            )
        )
        self.assert_ok(
            self.cli(
                "finish",
                "--checkpoint",
                str(self.path),
                "--id",
                "review-one",
                "--result-json",
                '{"verdict":"passed","findings":[]}',
            )
        )
        self.assert_denied(
            self.send(
                "gate-one",
                "bind-owner",
                "2026-10-15T21:20:00Z",
                {"owner": "native-reviewer-one"},
            )
        )
        self.assert_denied(self.reserve(*self.next_review))
        before = self.read()
        applied = self.event(
            "gate-one", "release-closed-gate", "2026-10-15T21:20:00Z", self.release
        )
        self.assertTrue(applied["applied"])
        after = self.read()
        (record,) = after["workerRecovery"]
        self.assertEqual(record["owner"], "native-reviewer-one")
        self.assertEqual(record["ownerReleasedAt"], "2026-10-15T21:20:00Z")
        self.assertEqual(record["ownerObservation"], self.release["observation"])
        self.assertIsNone(record["result"])
        self.assertIsNone(record["startedAt"])
        for field in ("convergence", "gateVerdicts", "authorization", "workflow"):
            self.assertEqual(after[field], before[field])
        retry = self.event(
            "gate-one", "release-closed-gate", "2026-10-15T21:20:00Z", self.release
        )
        self.assertFalse(retry["applied"])
        self.assertTrue(self.assert_ok(self.reserve(*self.next_review))["dispatch"])

    def test_refuses_fabricated_or_conflicting_release(self) -> None:
        self.assert_ok(
            self.cli(
                "finish",
                "--checkpoint",
                str(self.path),
                "--id",
                "review-one",
                "--result-json",
                '{"verdict":"passed","findings":[]}',
            )
        )
        before = self.path.read_bytes()
        for data in (
            {**self.release, "hostStatus": "not-created"},
            {**self.release, "hostStatus": "timeout"},
            {**self.release, "observation": " "},
            {**self.release, "owner": None},
            {"owner": "native-reviewer-one", "hostStatus": "exited"},
            {**self.release, "result": "passed"},
        ):
            with self.subTest(data=data):
                self.assert_denied(
                    self.send(
                        "gate-one", "release-closed-gate", "2026-10-15T21:20:00Z", data
                    )
                )
                self.assert_denied(
                    self.send(
                        "gate-one",
                        "release-closed-gate",
                        "2026-10-15T20:00:00Z",
                        self.release,
                    )
                )
                self.assertEqual(self.path.read_bytes(), before)
        self.event(
            "gate-one", "release-closed-gate", "2026-10-15T21:20:00Z", self.release
        )
        self.assert_denied(
            self.send(
                "gate-one",
                "release-closed-gate",
                "2026-10-15T21:30:00Z",
                {**self.release, "owner": "someone-else"},
            )
        )


if __name__ == "__main__":
    unittest.main()
