"""Exercise gate reuse and invalidation through the real bookkeeping CLI.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import test_ship_it_reservations as reservations


class ValidationReuseTest(unittest.TestCase):
    write = reservations.ReservationTest.write
    read = reservations.ReservationTest.read
    cli = reservations.ReservationTest.cli
    finish = reservations.ReservationTest.finish
    assert_ok = reservations.ReservationTest.assert_ok
    assert_denied = reservations.ReservationTest.assert_denied

    def setUp(self) -> None:
        reservations.ReservationTest.setUp(self)
        self.repository = Path(self.directory.name) / "repository"
        self.repository.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.test")
        for name, text in (
            ("src/behavior", "source"),
            ("dependency", "lock"),
            ("policy", "required"),
            ("unrelated", "documentation"),
        ):
            path = self.repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.commit()
        self.spec = {
            "repository": str(self.repository),
            "source": ["src"],
            "dependencies": ["dependency"],
            "policy": ["policy"],
            "command": ["python", "check.py"],
            "environment": {
                "variables": ["SAI_REUSE_TEST_ENV"],
                "facts": {"python": sys.version},
            },
            "policyFacts": {"requiredChecks": ["CI"]},
        }
        self.manifest = Path(self.directory.name) / "inputs.json"
        self.output = Path(self.directory.name) / "output.txt"
        self.output.write_text("Review Verdict: CLEAN\n")
        self.save_manifest()

    def git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()

    def commit(self) -> None:
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
        self.revision = self.git("rev-parse", "HEAD")
        document = self.read()
        document["workflow"]["revision"] = self.revision
        self.write(document)

    def save_manifest(self) -> None:
        self.manifest.write_text(json.dumps(self.spec))

    def structured(
        self, identity: str = "initial", kind: str = "review", *extra: str
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
            self.revision,
            "--inputs-json",
            str(self.manifest),
            *extra,
        )

    def assess(self, kind: str = "review") -> dict:
        return self.assert_ok(
            self.cli(
                "assess",
                "--checkpoint",
                str(self.path),
                "--kind",
                kind,
                "--revision",
                self.revision,
                "--inputs-json",
                str(self.manifest),
            )
        )

    def complete(self, verdict: str = "passed", kind: str = "review") -> None:
        self.assertTrue(self.assert_ok(self.structured(kind=kind))["dispatch"])
        result = {"verdict": verdict, "output": str(self.output)}
        if kind == "review":
            result["findings"] = []
        self.assert_ok(self.finish("initial", result))

    def test_unchanged_inputs_new_identity_reuses_without_consuming(self) -> None:
        self.complete()
        before = self.read()["convergence"]["reviewCycles"]
        receipt = self.assert_ok(self.structured("repeat"))
        self.assertFalse(receipt["dispatch"])
        self.assertEqual(receipt["reservation"]["result"]["verdict"], "passed")
        self.assertEqual(receipt["validity"]["status"], "reusable")
        self.assertEqual(self.read()["convergence"]["reviewCycles"], before)

    def test_unrelated_integration_carries_review_provenance_to_current_head(
        self,
    ) -> None:
        self.complete()
        original = self.revision
        (self.repository / "unrelated").write_text("updated docs")
        self.commit()
        self.assertFalse(self.assert_ok(self.structured("integrated"))["dispatch"])
        verdict = self.read()["gateVerdicts"][-1]
        self.assertEqual(verdict["revision"], self.revision)
        self.assertEqual(verdict["provenance"]["originalRevision"], original)
        self.assertTrue(self.assert_ok(self.structured("test", "test"))["dispatch"])

    def test_every_relevant_dimension_records_precise_invalidation(self) -> None:
        self.complete()
        for name in ("source", "dependencies", "policy"):
            path = {
                "source": "src/behavior",
                "dependencies": "dependency",
                "policy": "policy",
            }[name]
            (self.repository / path).write_text(name + " changed")
        self.spec["command"].append("--strict")
        self.spec["environment"]["facts"]["python"] = "different runtime"
        self.spec["policyFacts"]["requiredChecks"].append("security")
        self.save_manifest()
        self.commit()
        decision = self.assess()
        self.assertEqual(decision["status"], "invalid")
        self.assertEqual(
            set(decision["reasons"]),
            {
                "source",
                "dependencies",
                "policy",
                "command",
                "environment",
                "policyFacts",
            },
        )
        self.assertEqual(self.read()["gateVerdicts"][0]["status"], "stale")
        self.assert_denied(self.structured("test", "test"))

    def test_source_directory_detects_new_file_and_changed_criteria(self) -> None:
        self.complete()
        (self.repository / "src/new").write_text("new behavior")
        self.commit()
        document = self.read()
        document["task"]["acceptanceCriteria"] = ["new criterion"]
        self.write(document)
        self.assertEqual(
            set(self.assess()["reasons"]), {"source", "acceptanceCriteria"}
        )

    def test_failed_and_blocked_results_remain_unsatisfied_when_reused(self) -> None:
        self.complete("failed")
        result = self.assert_ok(self.structured("repeat"))
        self.assertFalse(result["dispatch"])
        self.assertEqual(result["reservation"]["result"]["verdict"], "failed")
        self.assertEqual(self.read()["gateVerdicts"], [])
        self.assert_denied(self.structured("test", "test"))

    def test_pending_result_cannot_redispatch_or_attest_clean(self) -> None:
        self.assert_ok(self.structured())
        self.assertFalse(self.assert_ok(self.structured())["dispatch"])
        self.assert_denied(self.structured("new-id"))
        self.assertIn("incomplete-result", self.assess()["reasons"])
        self.assertEqual(self.read()["gateVerdicts"], [])

    def test_modified_output_invalidates_result_even_with_unchanged_inputs(
        self,
    ) -> None:
        self.complete()
        self.output.write_text("different evidence")
        self.assertEqual(self.assess()["reasons"], ["unverifiable-output"])
        self.assert_denied(self.structured("repeat"))

    def test_missing_output_cannot_complete_a_gate(self) -> None:
        self.assert_ok(self.structured())
        result = self.finish(
            "initial",
            {
                "verdict": "passed",
                "findings": [],
                "output": str(self.output.with_name("missing")),
            },
        )
        self.assert_denied(result)
        self.assertEqual(
            self.read()["convergence"]["reservations"][0]["status"], "reserved"
        )

    def test_environment_variable_is_captured_without_manual_fingerprint(self) -> None:
        self.complete()
        original = os.environ.get("SAI_REUSE_TEST_ENV")
        try:
            os.environ["SAI_REUSE_TEST_ENV"] = "changed"
            self.assertEqual(self.assess()["reasons"], ["environment"])
        finally:
            if original is None:
                os.environ.pop("SAI_REUSE_TEST_ENV", None)
            else:
                os.environ["SAI_REUSE_TEST_ENV"] = original

    def test_dirty_worktree_and_mismatched_head_fail_closed(self) -> None:
        (self.repository / "src/behavior").write_text("uncommitted")
        self.assert_denied(self.structured())
        self.assertEqual(self.read()["convergence"].get("reviewCycles", 0), 0)

    def test_quality_reuses_completed_result_after_its_allowance_is_spent(self) -> None:
        self.complete(kind="quality")
        result = self.assert_ok(self.structured("repeat", "quality"))
        self.assertFalse(result["dispatch"])
        self.assertEqual(self.read()["convergence"]["fullQualityGateRuns"], 1)
        self.assertEqual(self.read()["gateVerdicts"][-1]["gate"], "local-checks")

    def test_current_inputs_must_still_match_at_completion(self) -> None:
        self.assert_ok(self.structured())
        original = self.path.read_bytes()
        (self.repository / "src/behavior").write_text("changed while executing")
        result = self.finish(
            "initial", {"verdict": "passed", "findings": [], "output": str(self.output)}
        )
        self.assert_denied(result)
        self.assertEqual(self.path.read_bytes(), original)

    def test_same_identity_cannot_change_request_on_cache_hit(self) -> None:
        self.complete()
        self.assert_denied(
            self.structured("initial", "review", "--reason", "changed request")
        )

    def test_same_identity_cannot_return_passing_unverifiable_evidence(self) -> None:
        self.complete()
        self.output.write_text("modified output")
        self.assert_denied(self.structured())
        document = self.read()
        self.assertEqual(document["gateVerdicts"][0]["status"], "stale")
        self.assertEqual(
            document["convergence"]["validityDecisions"][-1]["reasons"],
            ["unverifiable-output"],
        )
        self.assertEqual(document["convergence"]["reviewCycles"], 1)
        self.assert_denied(self.structured("test-after-invalid-retry", "test"))

    def test_corrupted_review_output_cannot_authorize_test_without_assessment(
        self,
    ) -> None:
        self.complete()
        self.output.write_text("corrupted after completion")

        self.assert_denied(self.structured("manual-test", "test"))

        document = self.read()
        self.assertEqual(document["convergence"]["broadTestRuns"], 0)
        self.assertEqual(document["gateVerdicts"][0]["status"], "stale")
        self.assertEqual(
            document["convergence"]["validityDecisions"][-1]["reasons"],
            ["unverifiable-output"],
        )

    def test_changed_runtime_invalidates_review_before_test_dispatch(self) -> None:
        self.complete()
        original = os.environ.get("SAI_REUSE_TEST_ENV")
        try:
            os.environ["SAI_REUSE_TEST_ENV"] = "different runtime"
            self.assert_denied(self.structured("manual-test", "test"))
            self.assertEqual(
                self.read()["convergence"]["validityDecisions"][-1]["reasons"],
                ["environment"],
            )
        finally:
            if original is None:
                os.environ.pop("SAI_REUSE_TEST_ENV", None)
            else:
                os.environ["SAI_REUSE_TEST_ENV"] = original

    def test_symlink_scope_and_unknown_manifest_field_fail_closed(self) -> None:
        (self.repository / "src/link").symlink_to(self.output)
        self.commit()
        self.assert_denied(self.structured())

    def test_failed_test_has_no_passing_attestation_when_reused(self) -> None:
        self.complete()
        self.assert_ok(self.structured("manual-test", "test"))
        self.assert_ok(
            self.finish(
                "manual-test", {"verdict": "failed", "output": str(self.output)}
            )
        )
        result = self.assert_ok(self.structured("repeat", "test"))
        self.assertFalse(result["dispatch"])
        self.assertEqual(result["reservation"]["result"]["verdict"], "failed")
        self.assertEqual(
            [verdict["gate"] for verdict in self.read()["gateVerdicts"]],
            ["adversarial-review"],
        )

    def test_missing_declared_inputs_cannot_start_passing_coverage(self) -> None:
        for dimension in ("source", "dependencies", "policy"):
            with self.subTest(dimension=dimension):
                original = self.spec[dimension]
                self.spec[dimension] = ["absent-declared-path"]
                self.save_manifest()

                self.assert_denied(self.structured())

                document = self.read()
                self.assertEqual(document["convergence"]["reviewCycles"], 0)
                self.assertEqual(document["gateVerdicts"], [])
                self.assertEqual(
                    document["convergence"]["validityDecisions"][-1]["reasons"],
                    [dimension, "unverifiable-inputs"],
                )
                self.spec[dimension] = original

    def test_missing_new_declaration_persists_invalidation_and_blocks_reuse(
        self,
    ) -> None:
        self.complete()
        self.spec["dependencies"] = ["absent-declared-path"]
        self.save_manifest()

        self.assert_denied(self.structured("new-head"))

        document = self.read()
        self.assertEqual(document["convergence"]["reviewCycles"], 1)
        self.assertEqual(document["gateVerdicts"][0]["status"], "stale")
        self.assertEqual(
            document["convergence"]["validityDecisions"][-1]["reasons"],
            ["dependencies", "unverifiable-inputs"],
        )

    def test_empty_dependency_declaration_remains_valid(self) -> None:
        self.spec["dependencies"] = []
        self.save_manifest()

        self.complete()

        self.assertFalse(self.assert_ok(self.structured("repeat"))["dispatch"])
