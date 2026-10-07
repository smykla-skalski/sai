#!/usr/bin/env python3
"""Behavior tests for the workflow failure replay runner."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("replay_failures.py")
SPEC = importlib.util.spec_from_file_location("replay_failures", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load replay_failures.py")
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


def case() -> dict[str, object]:
    return {
        "id": "stale-validation-after-edit",
        "title": "A source edit invalidates earlier validation",
        "failure_mode": "stale-validation",
        "harnesses": ["claude-code", "codex", "opencode", "copilot-cli", "sail"],
        "workflow": "single-agent",
        "privacy": {
            "classification": "public",
            "provenance": "synthetic-redaction",
            "reviewed": True,
            "contains_source_content": False,
        },
        "task_input": "SENSITIVE_SYNTHETIC_TASK_TEXT",
        "initial_state": ["SENSITIVE_SYNTHETIC_INITIAL_STATE"],
        "expected_behavior": ["Evidence is current."],
        "forbidden_behavior": ["Old evidence is accepted."],
        "grading": {
            "required_observations": [
                "old_evidence_invalidated",
                "current_revision_validated",
                "delivery_waited_for_current_evidence",
            ],
            "failure_observations": ["stale_evidence_accepted", "premature_completion"],
        },
    }


def corpus() -> dict[str, object]:
    return {"schema_version": 1, "cases": [case()]}


class ReplayFailuresTest(unittest.TestCase):
    def run_cli(
        self,
        directory: Path,
        *,
        adapter_body: str | None = None,
        corpus_value: dict[str, object] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        corpus_path = directory / "cases.json"
        corpus_path.write_text(json.dumps(corpus_value or corpus()), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--corpus", str(corpus_path)]
        if adapter_body is not None:
            adapter_path = directory / "adapter.py"
            adapter_path.write_text(adapter_body, encoding="utf-8")
            adapter_path.chmod(0o700)
            command.extend(("--adapter", f"codex={adapter_path}"))
        return subprocess.run(
            command, text=True, capture_output=True, timeout=10, check=False
        )

    def test_unavailable_harnesses_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            completed = self.run_cli(Path(raw_directory))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["summary"], {"failed": 0, "passed": 0, "skipped": 5})
        self.assertEqual(
            {result["reason"] for result in report["results"]},
            {"adapter_unavailable"},
        )

    def test_available_adapter_is_graded_and_cost_is_compared(self) -> None:
        adapter = """#!/usr/bin/env python3
import json, sys
request = json.load(sys.stdin)
observations = request["case"]["grading"]["required_observations"]
trace = {
    "schema_version": 1,
    "case_id": request["case"]["id"],
    "harness": request["harness"],
    "outcome": "accepted",
    "events": [
        {
            "sequence": index,
            "phase": "complete" if index == len(observations) else "test",
            "observation": observation,
        }
        for index, observation in enumerate(observations, start=1)
    ],
    "cost": {
        "turns": 4,
        "tool_calls": 8,
        "permission_decisions": 1,
        "input_tokens": None,
        "output_tokens": None,
        "elapsed_ms": 1200,
        "retries": 0,
    },
}
json.dump(trace, sys.stdout)
"""
        with tempfile.TemporaryDirectory() as raw_directory:
            completed = self.run_cli(Path(raw_directory), adapter_body=adapter)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        codex = next(
            result for result in report["results"] if result["harness"] == "codex"
        )
        self.assertEqual(codex["status"], "passed")
        self.assertEqual(report["accepted_task_cost"]["codex"]["accepted_tasks"], 1)
        self.assertEqual(report["accepted_task_cost"]["codex"]["tool_calls"], 8.0)
        self.assertNotIn("SENSITIVE_SYNTHETIC_TASK_TEXT", completed.stdout)
        self.assertNotIn("SENSITIVE_SYNTHETIC_INITIAL_STATE", completed.stdout)

    def test_missing_observation_blocks_release(self) -> None:
        adapter = """#!/usr/bin/env python3
import json, sys
request = json.load(sys.stdin)
json.dump({
    "schema_version": 1,
    "case_id": request["case"]["id"],
    "harness": request["harness"],
    "outcome": "accepted",
    "events": [{
        "sequence": 1,
        "phase": "complete",
        "observation": "old_evidence_invalidated",
    }],
    "cost": {
        "turns": 1,
        "tool_calls": 1,
        "permission_decisions": 0,
        "input_tokens": None,
        "output_tokens": None,
        "elapsed_ms": 1,
        "retries": 0,
    },
}, sys.stdout)
"""
        with tempfile.TemporaryDirectory() as raw_directory:
            completed = self.run_cli(Path(raw_directory), adapter_body=adapter)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        codex = next(
            result for result in report["results"] if result["harness"] == "codex"
        )
        self.assertEqual(codex["status"], "failed")
        self.assertEqual(
            codex["missing_observations"],
            ["current_revision_validated", "delivery_waited_for_current_evidence"],
        )

    def test_failure_observation_blocks_release(self) -> None:
        value = case()
        observations = value["grading"]["required_observations"]
        trace = {
            "schema_version": 1,
            "case_id": value["id"],
            "harness": "codex",
            "outcome": "accepted",
            "events": [
                {
                    "sequence": index,
                    "phase": "complete" if index == len(observations) + 1 else "test",
                    "observation": observation,
                }
                for index, observation in enumerate(
                    [*observations, "premature_completion"], start=1
                )
            ],
            "cost": dict.fromkeys(REPLAY.COUNTERS),
        }
        result = REPLAY.grade_trace(trace, value)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_observations"], ["premature_completion"])

    def test_wrong_final_outcome_and_phase_block_release(self) -> None:
        value = case()
        value["failure_mode"] = "tool-failure"
        observations = value["grading"]["required_observations"]
        trace = {
            "schema_version": 1,
            "case_id": value["id"],
            "harness": "codex",
            "outcome": "accepted",
            "events": [
                {"sequence": index, "phase": "test", "observation": observation}
                for index, observation in enumerate(observations, start=1)
            ],
            "cost": dict.fromkeys(REPLAY.COUNTERS),
        }
        result = REPLAY.grade_trace(trace, value)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["expected_outcome"], "blocked")
        self.assertEqual(
            result["phase_transition_failures"],
            ["accepted_without_complete_phase"],
        )

    def test_unapproved_or_extended_corpus_is_rejected(self) -> None:
        for mutation in ("privacy", "extra"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as raw_directory,
            ):
                value = corpus()
                if mutation == "privacy":
                    value["cases"][0]["privacy"]["contains_source_content"] = True
                else:
                    value["cases"][0]["prompt"] = "must not be retained"
                completed = self.run_cli(Path(raw_directory), corpus_value=value)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")

    def test_adapter_diagnostic_cannot_leak_into_report(self) -> None:
        adapter = """#!/usr/bin/env python3
import sys
print("PRIVATE_PATH_AND_TOOL_OUTPUT", file=sys.stderr)
raise SystemExit(7)
"""
        with tempfile.TemporaryDirectory() as raw_directory:
            completed = self.run_cli(Path(raw_directory), adapter_body=adapter)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn("PRIVATE_PATH_AND_TOOL_OUTPUT", completed.stdout)
        report = json.loads(completed.stdout)
        codex = next(
            result for result in report["results"] if result["harness"] == "codex"
        )
        self.assertEqual(codex["reason"], "adapter_exit_nonzero")

    def test_unknown_observation_cannot_leak_into_report(self) -> None:
        value = case()
        observations = value["grading"]["required_observations"]
        private_observation = "private_source_content_encoded_as_slug"
        trace = {
            "schema_version": 1,
            "case_id": value["id"],
            "harness": "codex",
            "outcome": "accepted",
            "events": [
                {
                    "sequence": index,
                    "phase": "complete" if index == len(observations) + 1 else "test",
                    "observation": observation,
                }
                for index, observation in enumerate(
                    [*observations, private_observation], start=1
                )
            ],
            "cost": dict.fromkeys(REPLAY.COUNTERS),
        }
        result = REPLAY.grade_trace(trace, value)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["unknown_observation_count"], 1)
        self.assertNotIn(private_observation, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
