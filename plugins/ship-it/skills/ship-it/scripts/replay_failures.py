#!/usr/bin/env python3
# Copyright 2026 Smykla Skalski, MIT License.
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
from typing import Any, Final

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
    },
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
    {"accepted", "rejected", "blocked", "cancelled", "failed", "waiting"},
)
PHASES: Final[frozenset[str]] = frozenset(
    {
        "resolve",
        "orchestrate",
        "explore",
        "branch",
        "implement",
        "publish",
        "review",
        "test",
        "pr",
        "wait",
        "fix",
        "merge",
        "complete",
    },
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
    },
)
TRACE_KEYS: Final[frozenset[str]] = frozenset(
    {"schema_version", "case_id", "harness", "outcome", "events", "cost"},
)
EVENT_KEYS: Final[frozenset[str]] = frozenset({"sequence", "phase", "observation"})
SLUG: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


class UsageError(Exception):
    """Invalid command input or adapter contract."""


class AdapterError(Exception):
    """Privacy-safe adapter failure suitable for a persisted report."""

    def __init__(self, reason: str) -> None:
        """Keep reason, a stable token that is safe to persist in a report."""
        super().__init__(reason)
        self.reason = reason


def require_object(value: object, label: str) -> dict[str, object]:
    """Return value as a JSON object; raise UsageError naming label otherwise."""
    if not isinstance(value, dict):
        msg = f"{label} must be an object"
        raise UsageError(msg)
    return value


def require_string(value: object, label: str, *, slug: bool = False) -> str:
    """Return a non-empty string, a lowercase slug when slug is set."""
    if not isinstance(value, str) or not value:
        msg = f"{label} must be a non-empty string"
        raise UsageError(msg)
    if slug and not SLUG.fullmatch(value):
        msg = f"{label} must be a lowercase slug"
        raise UsageError(msg)
    return value


def require_string_list(value: object, label: str, *, slug: bool = False) -> list[str]:
    """Return a non-empty array of unique strings checked like require_string."""
    if not isinstance(value, list) or not value:
        msg = f"{label} must be a non-empty array"
        raise UsageError(msg)
    result = [require_string(item, f"{label} item", slug=slug) for item in value]
    if len(result) != len(set(result)):
        msg = f"{label} must not contain duplicates"
        raise UsageError(msg)
    return result


def _validate_case_fields(case: dict[str, object], label: str) -> None:
    require_string(case["title"], f"{label}.title")
    if case["failure_mode"] not in FAILURE_MODES:
        msg = f"{label}.failure_mode is unsupported"
        raise UsageError(msg)
    harnesses = require_string_list(case["harnesses"], f"{label}.harnesses", slug=True)
    if any(item not in (*SUPPORTED_HARNESSES, "multi-agent") for item in harnesses):
        msg = f"{label}.harnesses contains an unsupported harness"
        raise UsageError(msg)
    if case["workflow"] not in WORKFLOWS:
        msg = f"{label}.workflow is unsupported"
        raise UsageError(msg)

    privacy = require_object(case["privacy"], f"{label}.privacy")
    expected_privacy = {
        "classification": "public",
        "provenance": "synthetic-redaction",
        "reviewed": True,
        "contains_source_content": False,
    }
    if privacy != expected_privacy:
        msg = f"{label}.privacy is not approved synthetic-redaction"
        raise UsageError(msg)

    require_string(case["task_input"], f"{label}.task_input")
    for field in ("initial_state", "expected_behavior", "forbidden_behavior"):
        require_string_list(case[field], f"{label}.{field}")
    grading = require_object(case["grading"], f"{label}.grading")
    if set(grading) != {"required_observations", "failure_observations"}:
        msg = f"{label}.grading fields do not match schema version 1"
        raise UsageError(msg)
    require_string_list(
        grading["required_observations"],
        f"{label}.grading.required_observations",
        slug=True,
    )
    require_string_list(
        grading["failure_observations"],
        f"{label}.grading.failure_observations",
        slug=True,
    )


def validate_corpus(value: object) -> list[dict[str, object]]:
    """Return the corpus cases; raise UsageError when any case breaks schema 1."""
    corpus = require_object(value, "corpus")
    if set(corpus) != {"schema_version", "cases"} or corpus.get("schema_version") != 1:
        msg = "corpus must match agent-workflows schema version 1"
        raise UsageError(msg)
    raw_cases = corpus.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        msg = "corpus cases must be a non-empty array"
        raise UsageError(msg)

    cases: list[dict[str, object]] = []
    ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        label = f"cases[{index}]"
        case = require_object(raw_case, label)
        if set(case) != CASE_KEYS:
            msg = f"{label} fields do not match schema version 1"
            raise UsageError(msg)
        case_id = require_string(case["id"], f"{label}.id", slug=True)
        if case_id in ids:
            msg = f"duplicate case id {case_id!r}"
            raise UsageError(msg)
        ids.add(case_id)
        _validate_case_fields(case, label)
        cases.append(case)
    return cases


def parse_adapters(values: list[str]) -> dict[str, Path]:
    """Map HARNESS=/absolute/executable arguments to adapter paths."""
    adapters: dict[str, Path] = {}
    for value in values:
        harness, separator, raw_path = value.partition("=")
        if not separator or harness not in SUPPORTED_HARNESSES or not raw_path:
            msg = "adapter must be HARNESS=/absolute/executable"
            raise UsageError(msg)
        if harness in adapters:
            msg = f"duplicate adapter for {harness}"
            raise UsageError(msg)
        path = Path(raw_path)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            msg = f"adapter for {harness} must be an executable absolute path"
            raise UsageError(msg)
        adapters[harness] = path
    return adapters


def _validate_events(raw_events: object) -> list[dict[str, object]]:
    if not isinstance(raw_events, list) or not raw_events:
        msg = "adapter trace events must be a non-empty array"
        raise UsageError(msg)
    events: list[dict[str, object]] = []
    for index, raw_event in enumerate(raw_events, start=1):
        event = require_object(raw_event, f"events[{index - 1}]")
        if set(event) != EVENT_KEYS or event.get("sequence") != index:
            msg = "adapter trace events must have exact fields and contiguous sequence"
            raise UsageError(msg)
        if event.get("phase") not in PHASES:
            msg = "adapter trace event phase is unsupported"
            raise UsageError(msg)
        require_string(event.get("observation"), "adapter trace observation", slug=True)
        events.append(event)
    return events


def _validate_cost(value: object) -> dict[str, object]:
    cost = require_object(value, "adapter trace cost")
    if set(cost) != set(COUNTERS):
        msg = "adapter trace cost fields do not match schema version 1"
        raise UsageError(msg)
    for name in COUNTERS:
        counter = cost[name]
        if counter is not None and (
            isinstance(counter, bool) or not isinstance(counter, int) or counter < 0
        ):
            msg = f"adapter trace cost {name} must be null or a non-negative integer"
            raise UsageError(msg)
    return cost


def validate_trace(value: object, case_id: str, harness: str) -> dict[str, object]:
    """Return the adapter trace when it matches schema 1 and the replay request."""
    trace = require_object(value, "adapter trace")
    if set(trace) != TRACE_KEYS or trace.get("schema_version") != SCHEMA_VERSION:
        msg = "adapter trace fields do not match schema version 1"
        raise UsageError(msg)
    if trace.get("case_id") != case_id or trace.get("harness") != harness:
        msg = "adapter trace identity does not match the replay request"
        raise UsageError(msg)
    if trace.get("outcome") not in OUTCOMES:
        msg = "adapter trace outcome is unsupported"
        raise UsageError(msg)
    events = _validate_events(trace.get("events"))
    cost = _validate_cost(trace.get("cost"))
    trace["events"] = events
    trace["cost"] = cost
    return trace


def run_adapter(
    path: Path,
    harness: str,
    case: dict[str, object],
    timeout: float,
) -> dict[str, object]:
    """Replay one case through an adapter; raise AdapterError with a safe reason."""
    request = {
        "schema_version": SCHEMA_VERSION,
        "harness": harness,
        "case": case,
    }
    try:
        # S603: argv list with no shell; the adapter is the caller's --adapter,
        # checked to be an absolute executable.
        completed = subprocess.run(  # noqa: S603
            [str(path)],
            input=json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n",
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "SAI_REPLAY_HARNESS": harness},
        )
    except subprocess.TimeoutExpired as error:
        msg = "adapter_timeout"
        raise AdapterError(msg) from error
    except OSError as error:
        msg = "adapter_start_failed"
        raise AdapterError(msg) from error
    if completed.returncode != 0:
        msg = "adapter_exit_nonzero"
        raise AdapterError(msg)
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        msg = "adapter_invalid_json"
        raise AdapterError(msg) from error
    try:
        return validate_trace(value, str(case["id"]), harness)
    except UsageError as error:
        msg = "adapter_invalid_trace"
        raise AdapterError(msg) from error


def grade_trace(trace: dict[str, object], case: dict[str, object]) -> dict[str, object]:
    """Grade a validated trace against the observations and phases of its case."""
    grading = require_object(case["grading"], "case grading")
    required = set(
        require_string_list(
            grading["required_observations"],
            "required observations",
            slug=True,
        ),
    )
    failures = set(
        require_string_list(
            grading["failure_observations"],
            "failure observations",
            slug=True,
        ),
    )
    events = trace["events"]
    if not isinstance(events, list):
        msg = "validated trace events changed type"
        raise UsageError(msg)
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
    """Return mean cost counters per harness over passed, accepted results."""
    accepted: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
    cases: list[dict[str, object]],
    adapters: dict[str, Path],
    timeout: float,
) -> dict[str, Any]:
    """Replay every case through the adapter of each harness it names."""
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
                    },
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
                    },
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
    """Return the CLI argument parser."""
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--corpus", type=Path, required=True)
    value.add_argument(
        "--adapter",
        action="append",
        default=[],
        metavar="HARNESS=/ABSOLUTE/PATH",
    )
    value.add_argument("--timeout", type=float, default=300.0)
    value.add_argument("--output", type=Path)
    return value


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return its exit code."""
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
