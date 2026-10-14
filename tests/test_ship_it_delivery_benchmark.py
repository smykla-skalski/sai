from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "ship-it"
    / "skills"
    / "ship-it"
    / "scripts"
    / "delivery_benchmark.py"
)
CASES = (
    ROOT
    / "plugins"
    / "ship-it"
    / "benchmarks"
    / "delivery-performance"
    / "cases.json"
)
SPEC = importlib.util.spec_from_file_location("delivery_benchmark", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
delivery_benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery_benchmark)


def sample_result(
    *,
    outcome: str = "waiting",
    detected: bool = False,
    blocking: bool = False,
    untested: list[str] | None = None,
    approvals: int = 0,
    approval_requests: int = 0,
    approval_waits: int = 0,
    duplicates: int = 0,
) -> dict[str, object]:
    return {
        "outcome": outcome,
        "required_gates": ["ci"],
        "gate_executions": [{"gate": "ci", "count": 0, "status": "pending"}],
        "approval_requests": approval_requests,
        "redundant_approval_requests": approvals,
        "duplicate_gate_executions": duplicates,
        "user_interruptions": 0,
        "concurrent_workers_peak": 0,
        "waits": [
            {"kind": "approval", "count": approval_waits, "duration_ms": None},
            {"kind": "hosted_service", "count": 1, "duration_ms": None},
        ],
        "confirmed_defect_detected": detected,
        "required_delivery_blocker_present": blocking,
        "untested_criteria": [] if untested is None else untested,
        "timing": {
            "elapsed_ms": 10,
            "active_ms": 10,
            "wait_ms": {
                "approval": None,
                "hosted_service": None,
                "resource_queue": None,
            },
        },
        "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 5},
    }


class DeliveryBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        value = json.loads(CASES.read_text(encoding="utf-8"))
        self.cases = delivery_benchmark.validate_cases(value)

    def test_public_corpus_contains_exact_required_scenarios(self) -> None:
        self.assertEqual(
            [case["id"] for case in self.cases],
            [
                "documentation-only-work",
                "ordinary-fix-resume",
                "confirmed-security-defect",
                "moving-default-branch",
                "native-fixture-failure",
            ],
        )

    def test_candidate_rejects_replayed_approval_and_duplicate_gate(self) -> None:
        case = self.cases[1]
        result = sample_result(approvals=1, duplicates=1)

        failures = delivery_benchmark.validate_result(case, result, "candidate")

        self.assertEqual(
            failures,
            [
                "redundant_approval_requests: expected at most 0, got 1",
                "duplicate_gate_executions: expected at most 0, got 1",
            ],
        )

    def test_security_defect_requires_detection_and_blocking(self) -> None:
        case = self.cases[2]
        result = sample_result(
            outcome="blocked",
            detected=True,
            blocking=False,
            untested=["The security regression criterion has not passed."],
        )

        failures = delivery_benchmark.validate_result(case, result, "baseline")

        self.assertEqual(
            failures,
            ["required_delivery_blocker_present: expected True, got False"],
        )

    def test_candidate_rejects_new_approval_action_after_recorded_approval(self) -> None:
        case = self.cases[1]
        result = sample_result(approval_requests=1, approval_waits=1)

        failures = delivery_benchmark.validate_result(case, result, "candidate")

        self.assertEqual(
            failures,
            [
                "approval_requests: expected at most 0, got 1",
                "approval waits: expected at most 0, got 1",
            ],
        )

    def test_candidate_derives_duplicate_gate_executions(self) -> None:
        case = self.cases[1]
        cases = (
            [{"gate": "review", "count": 2, "status": "passed"}],
            [
                {"gate": "review", "count": 1, "status": "passed"},
                {"gate": "review", "count": 1, "status": "passed"},
            ],
        )

        for gate_executions in cases:
            with self.subTest(gate_executions=gate_executions):
                result = sample_result()
                result["gate_executions"] = gate_executions

                failures = delivery_benchmark.validate_result(
                    case, result, "candidate"
                )

                self.assertEqual(
                    failures,
                    [
                        "derived duplicate gate executions: expected at most 0, got 1"
                    ],
                )

    def test_native_failure_requires_explicit_untested_criterion(self) -> None:
        case = self.cases[4]
        result = sample_result(outcome="blocked", blocking=True)

        failures = delivery_benchmark.validate_result(case, result, "candidate")

        self.assertEqual(failures, ["required untested criteria are missing"])

    def test_report_requires_elapsed_and_active_time(self) -> None:
        result = sample_result()
        del result["timing"]["active_ms"]

        failures = delivery_benchmark.validate_result_shape(result)

        self.assertEqual(
            failures,
            ["timing fields do not match the benchmark schema"],
        )

    def test_comparison_reports_improvements_and_regressions_separately(self) -> None:
        runs: list[dict[str, object]] = []
        for case_id in delivery_benchmark.CASE_IDS:
            runs.extend(
                [
                    {
                        "variant": "baseline",
                        "case_id": case_id,
                        "result": sample_result(approvals=1, duplicates=0),
                    },
                    {
                        "variant": "candidate",
                        "case_id": case_id,
                        "result": sample_result(approvals=0, duplicates=1),
                    },
                ]
            )

        comparison = delivery_benchmark.compare_runs(runs)

        self.assertEqual(len(comparison["improvements"]), 5)
        self.assertEqual(len(comparison["regressions"]), 5)
        self.assertEqual(len(comparison["unchanged"]), 15)
        self.assertFalse(comparison["speedup_claimed"])

    def test_report_rejects_missing_reproducibility_provenance(self) -> None:
        report = json.loads(
            (
                ROOT
                / "plugins"
                / "ship-it"
                / "benchmarks"
                / "delivery-performance"
                / "report.json"
            ).read_text(encoding="utf-8")
        )
        report["runs"][0]["source_revision"] = "not-a-revision"

        failures = delivery_benchmark.validate_report(self.cases, report)

        self.assertIn("run source revision is invalid", failures)


if __name__ == "__main__":
    unittest.main()
