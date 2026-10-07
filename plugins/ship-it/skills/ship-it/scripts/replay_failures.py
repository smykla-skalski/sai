#!/usr/bin/env python3
"""Replay the public agent-workflow failure corpus through harness adapters.

Adapters receive one synthetic corpus case as JSON on stdin and return a
privacy-safe normalized trace as JSON on stdout. The report contains only
stable identifiers, observation tokens, phase names, statuses, and counters.

Exit codes: 0 when every available adapter passes, 1 on a regression, and 2
for invalid input or usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final[int] = 1
SUPPORTED_HARNESSES: Final[tuple[str, ...]] = (
    "claude-code",
    "codex",
    "opencode",
    "copilot-cli",
    "sail",
)
FAILURE_MODES: Final[frozenset[str]] = frozenset(
    {
        "duplicate-work",
        "permission-loop",
        "stale-validation",
        "compaction-loss",
        "tool-failure",
        "incomplete-delivery",
    }
)
WORKFLOWS: Final[frozenset[str]] = frozenset({"single-agent", "multi-agent"})
EXPECTED_OUTCOMES: Final[dict[str, str]] = {
    "duplicate-work": "blocked",
    "permission-loop": "accepted",
    "stale-validation": "accepted",
    "compaction-loss": "accepted",
    "tool-failure": "blocked",
    "incomplete-delivery": "waiting",
}
OUTCOMES: Final[frozenset[str]] = frozenset(
    {"accepted", "rejected", "blocked", "cancelled", "failed", "waiting"}
)
PHASES: Final[frozenset[str]] = frozenset(
    {
        "resolve",
        "orchestrate",
        "explore",
        "branch",
        "implement",
        "review",
        "test",
        "pr",
        "wait",
        "fix",
        "merge",
        "complete",
    }
)
COUNTERS: Final[tuple[str, ...]] = (
    "turns",
    "tool_calls",
    "permission_decisions",
    "input_tokens",
    "output_tokens",
    "elapsed_ms",
    "retries",
)
CASE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "title",
        "failure_mode",
        "harnesses",
        "workflow",
        "privacy",
        "task_input",
        "initial_state",
        "expected_behavior",
        "forbidden_behavior",
        "grading",
    }
)
TRACE_KEYS: Final[frozenset[str]] = frozenset(
    {"schema_version", "case_id", "harness", "outcome", "events", "cost"}
)
EVENT_KEYS: Final[frozenset[str]] = frozenset({"sequence", "phase", "observation"})
SLUG: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


class UsageError(Exception):
    """Invalid command input or adapter contract."""


class AdapterError(Exception):
    """Privacy-safe adapter failure suitable for a persisted report."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise UsageError(f"{label} must be an object")
    return value


def require_string(value: object, label: str, *, slug: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise UsageError(f"{label} must be a non-empty string")
    if slug and not SLUG.fullmatch(value):
        raise UsageError(f"{label} must be a lowercase slug")
    return value


def require_string_list(value: object, label: str, *, slug: bool = False) -> list[str]:
    if not isinstance(value, list) or not value:
        raise UsageError(f"{label} must be a non-empty array")
    result = [require_string(item, f"{label} item", slug=slug) for item in value]
    if len(result) != len(set(result)):
        raise UsageError(f"{label} must not contain duplicates")
    return result


def validate_corpus(value: object) -> list[dict[str, object]]:
    corpus = require_object(value, "corpus")
    if set(corpus) != {"schema_version", "cases"} or corpus.get("schema_version") != 1:
        raise UsageError("corpus must match agent-workflows schema version 1")
    raw_cases = corpus.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise UsageError("corpus cases must be a non-empty array")

    cases: list[dict[str, object]] = []
    ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        case = require_object(raw_case, f"cases[{index}]")
        if set(case) != CASE_KEYS:
            raise UsageError(f"cases[{index}] fields do not match schema version 1")
        case_id = require_string(case["id"], f"cases[{index}].id", slug=True)
        if case_id in ids:
            raise UsageError(f"duplicate case id {case_id!r}")
        ids.add(case_id)
        require_string(case["title"], f"cases[{index}].title")
        if case["failure_mode"] not in FAILURE_MODES:
            raise UsageError(f"cases[{index}].failure_mode is unsupported")
        harnesses = require_string_list(
            case["harnesses"], f"cases[{index}].harnesses", slug=True
        )
        if any(item not in (*SUPPORTED_HARNESSES, "multi-agent") for item in harnesses):
            raise UsageError(
                f"cases[{index}].harnesses contains an unsupported harness"
            )
        if case["workflow"] not in WORKFLOWS:
            raise UsageError(f"cases[{index}].workflow is unsupported")

        privacy = require_object(case["privacy"], f"cases[{index}].privacy")
        expected_privacy = {
            "classification": "public",
            "provenance": "synthetic-redaction",
            "reviewed": True,
            "contains_source_content": False,
        }
        if privacy != expected_privacy:
            raise UsageError(
                f"cases[{index}].privacy is not approved synthetic-redaction"
            )

        require_string(case["task_input"], f"cases[{index}].task_input")
        for field in ("initial_state", "expected_behavior", "forbidden_behavior"):
            require_string_list(case[field], f"cases[{index}].{field}")
        grading = require_object(case["grading"], f"cases[{index}].grading")
        if set(grading) != {"required_observations", "failure_observations"}:
            raise UsageError(
                f"cases[{index}].grading fields do not match schema version 1"
            )
        require_string_list(
            grading["required_observations"],
            f"cases[{index}].grading.required_observations",
            slug=True,
        )
        require_string_list(
            grading["failure_observations"],
            f"cases[{index}].grading.failure_observations",
            slug=True,
        )
        cases.append(case)
    return cases


def parse_adapters(values: list[str]) -> dict[str, Path]:
    adapters: dict[str, Path] = {}
    for value in values:
        harness, separator, raw_path = value.partition("=")
        if not separator or harness not in SUPPORTED_HARNESSES or not raw_path:
            raise UsageError("adapter must be HARNESS=/absolute/executable")
        if harness in adapters:
            raise UsageError(f"duplicate adapter for {harness}")
        path = Path(raw_path)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise UsageError(
                f"adapter for {harness} must be an executable absolute path"
            )
        adapters[harness] = path
    return adapters


def validate_trace(value: object, case_id: str, harness: str) -> dict[str, object]:
    trace = require_object(value, "adapter trace")
    if set(trace) != TRACE_KEYS or trace.get("schema_version") != SCHEMA_VERSION:
        raise UsageError("adapter trace fields do not match schema version 1")
    if trace.get("case_id") != case_id or trace.get("harness") != harness:
        raise UsageError("adapter trace identity does not match the replay request")
    if trace.get("outcome") not in OUTCOMES:
        raise UsageError("adapter trace outcome is unsupported")

    raw_events = trace.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise UsageError("adapter trace events must be a non-empty array")
    events: list[dict[str, object]] = []
    for index, raw_event in enumerate(raw_events, start=1):
        event = require_object(raw_event, f"events[{index - 1}]")
        if set(event) != EVENT_KEYS or event.get("sequence") != index:
            raise UsageError(
                "adapter trace events must have exact fields and contiguous sequence"
            )
        if event.get("phase") not in PHASES:
            raise UsageError("adapter trace event phase is unsupported")
        require_string(event.get("observation"), "adapter trace observation", slug=True)
        events.append(event)

    cost = require_object(trace.get("cost"), "adapter trace cost")
    if set(cost) != set(COUNTERS):
        raise UsageError("adapter trace cost fields do not match schema version 1")
    for name in COUNTERS:
        counter = cost[name]
        if counter is not None and (
            isinstance(counter, bool) or not isinstance(counter, int) or counter < 0
        ):
            raise UsageError(
                f"adapter trace cost {name} must be null or a non-negative integer"
            )
    trace["events"] = events
    trace["cost"] = cost
    return trace


def run_adapter(
    path: Path, harness: str, case: dict[str, object], timeout: float
) -> dict[str, object]:
    request = {
        "schema_version": SCHEMA_VERSION,
        "harness": harness,
        "case": case,
    }
    try:
        completed = subprocess.run(
            [str(path)],
            input=json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n",
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "SAI_REPLAY_HARNESS": harness},
        )
    except subprocess.TimeoutExpired as error:
        raise AdapterError("adapter_timeout") from error
    except OSError as error:
        raise AdapterError("adapter_start_failed") from error
    if completed.returncode != 0:
        raise AdapterError("adapter_exit_nonzero")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdapterError("adapter_invalid_json") from error
    try:
        return validate_trace(value, str(case["id"]), harness)
    except UsageError as error:
        raise AdapterError("adapter_invalid_trace") from error


def grade_trace(trace: dict[str, object], case: dict[str, object]) -> dict[str, object]:
    grading = require_object(case["grading"], "case grading")
    required = set(
        require_string_list(
            grading["required_observations"], "required observations", slug=True
        )
    )
    failures = set(
        require_string_list(
            grading["failure_observations"], "failure observations", slug=True
        )
    )
    events = trace["events"]
    if not isinstance(events, list):
        raise UsageError("validated trace events changed type")
    observed = {
        str(event["observation"]) for event in events if isinstance(event, dict)
    }
    phases = [str(event["phase"]) for event in events if isinstance(event, dict)]
    missing = sorted(required - observed)
    forbidden = sorted(failures & observed)
    known_observations = required | failures
    unknown_observation_count = len(observed - known_observations)
    expected_outcome = EXPECTED_OUTCOMES[str(case["failure_mode"])]
    outcome_matches = trace["outcome"] == expected_outcome
    phase_failures: list[str] = []
    if "complete" in phases[:-1]:
        phase_failures.append("activity_after_complete")
    if trace["outcome"] == "accepted" and phases[-1] != "complete":
        phase_failures.append("accepted_without_complete_phase")
    if trace["outcome"] == "waiting" and phases[-1] != "wait":
        phase_failures.append("waiting_without_wait_phase")
    return {
        "case_id": case["id"],
        "harness": trace["harness"],
        "status": (
            "passed"
            if not missing
            and not forbidden
            and not unknown_observation_count
            and outcome_matches
            and not phase_failures
            else "failed"
        ),
        "outcome": trace["outcome"],
        "expected_outcome": expected_outcome,
        "phases": phases,
        "observations": sorted(observed & known_observations),
        "unknown_observation_count": unknown_observation_count,
        "missing_observations": missing,
        "failure_observations": forbidden,
        "phase_transition_failures": phase_failures,
        "cost": trace["cost"],
    }


def accepted_cost(results: list[dict[str, object]]) -> dict[str, object]:
    accepted: dict[str, list[dict[str, object]]] = defaultdict(list)
    for result in results:
        if result.get("status") == "passed" and result.get("outcome") == "accepted":
            cost = result.get("cost")
            if isinstance(cost, dict):
                accepted[str(result["harness"])].append(cost)

    comparison: dict[str, object] = {}
    for harness in SUPPORTED_HARNESSES:
        samples = accepted.get(harness, [])
        if not samples:
            comparison[harness] = {"accepted_tasks": 0, **dict.fromkeys(COUNTERS)}
            continue
        summary: dict[str, object] = {"accepted_tasks": len(samples)}
        for counter in COUNTERS:
            values = [
                sample[counter] for sample in samples if sample[counter] is not None
            ]
            summary[counter] = sum(values) / len(values) if values else None
        comparison[harness] = summary
    return comparison


def replay(
    cases: list[dict[str, object]], adapters: dict[str, Path], timeout: float
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for harness in SUPPORTED_HARNESSES:
        adapter = adapters.get(harness)
        for case in cases:
            harnesses = case["harnesses"]
            if not isinstance(harnesses, list) or harness not in harnesses:
                continue
            if adapter is None:
                results.append(
                    {
                        "case_id": case["id"],
                        "harness": harness,
                        "status": "skipped",
                        "reason": "adapter_unavailable",
                    }
                )
                continue
            try:
                trace = run_adapter(adapter, harness, case, timeout)
                results.append(grade_trace(trace, case))
            except AdapterError as error:
                results.append(
                    {
                        "case_id": case["id"],
                        "harness": harness,
                        "status": "failed",
                        "reason": error.reason,
                    }
                )
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus_schema_version": 1,
        "results": results,
        "accepted_task_cost": accepted_cost(results),
        "summary": {
            status: sum(result["status"] == status for result in results)
            for status in ("passed", "failed", "skipped")
        },
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--corpus", type=Path, required=True)
    value.add_argument(
        "--adapter", action="append", default=[], metavar="HARNESS=/ABSOLUTE/PATH"
    )
    value.add_argument("--timeout", type=float, default=300.0)
    value.add_argument("--output", type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout <= 0:
        print("error: timeout must be positive", file=sys.stderr)
        return 2
    try:
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        cases = validate_corpus(corpus)
        adapters = parse_adapters(args.adapter)
        report = replay(cases, adapters, args.timeout)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, UsageError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        try:
            args.output.write_text(encoded, encoding="utf-8")
        except OSError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(encoded)
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
