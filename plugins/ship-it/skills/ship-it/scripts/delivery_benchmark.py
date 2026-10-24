#!/usr/bin/env python3
"""Run and validate the public ship-it delivery performance benchmark.

Usage:
  delivery_benchmark.py run --cases CASES --result-schema SCHEMA
      --baseline-dir DIR --candidate-dir DIR --baseline-revision SHA
      --candidate-revision SHA --model MODEL [--samples N] --output FILE
  delivery_benchmark.py validate --cases CASES --report FILE

The runner persists only normalized decisions, counters, timings, and tool
metadata. It never writes prompts, tool output, paths, source, or credentials.

Exit codes: 0 for a valid comparison, 1 for an acceptance regression, and 2
for invalid input, tool failure, or malformed model output.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeGuard, cast

SCHEMA_VERSION: Final[int] = 1
CASE_IDS: Final[tuple[str, ...]] = (
    "documentation-only-work",
    "ordinary-fix-resume",
    "confirmed-security-defect",
    "moving-default-branch",
    "native-fixture-failure",
)
VARIANTS: Final[tuple[str, ...]] = ("baseline", "candidate")
EXPECTED_PAIRS: Final[frozenset[tuple[str, str]]] = frozenset(
    (variant, case_id) for variant in VARIANTS for case_id in CASE_IDS
)
SHA: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
SHA256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
ENVIRONMENT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "adapter",
        "adapter_version",
        "model",
        "reasoning_effort",
        "sandbox",
        "platform",
        "machine",
        "python",
    },
)
RESULT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "outcome",
        "required_gates",
        "gate_executions",
        "approval_requests",
        "redundant_approval_requests",
        "duplicate_gate_executions",
        "user_interruptions",
        "concurrent_workers_peak",
        "waits",
        "confirmed_defect_detected",
        "required_delivery_blocker_present",
        "untested_criteria",
        "timing",
        "usage",
    },
)
RUN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "variant",
        "case_id",
        "sample",
        "source_revision",
        "contract_digest",
        "result",
    },
)
CANDIDATE_LIMITS: Final[tuple[tuple[str, str], ...]] = (
    ("redundant_approval_requests", "candidate_max_redundant_approval_requests"),
    ("duplicate_gate_executions", "candidate_max_duplicate_gate_executions"),
)
GATE_STATUSES: Final[frozenset[str]] = frozenset(
    {"passed", "failed", "blocked", "pending", "reused"},
)
WAIT_KINDS: Final[frozenset[str]] = frozenset(
    {"approval", "hosted_service", "resource_queue"},
)


class BenchmarkError(ValueError):
    """Invalid benchmark input or execution result."""


@dataclass(frozen=True)
class CodexSettings:
    """Codex invocation settings shared by every benchmark sample."""

    codex: str
    model: str
    reasoning_effort: str
    result_schema: Path
    timeout: float


def load_object(path: Path, label: str) -> dict[str, object]:
    """Return the JSON object stored at path; raise BenchmarkError otherwise."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"cannot read {label}: {error}"
        raise BenchmarkError(msg) from error
    if not isinstance(value, dict):
        msg = f"{label} must be a JSON object"
        raise BenchmarkError(msg)
    return value


def validate_cases(value: dict[str, object]) -> list[dict[str, object]]:
    """Return the five cases in canonical order; raise BenchmarkError on drift."""
    if set(value) != {"schema_version", "cases"} or value["schema_version"] != 1:
        msg = "cases must match schema version 1"
        raise BenchmarkError(msg)
    raw_cases = value["cases"]
    if not isinstance(raw_cases, list) or len(raw_cases) != len(CASE_IDS):
        msg = "cases must contain exactly five entries"
        raise BenchmarkError(msg)
    cases: list[dict[str, object]] = []
    for index, case_id in enumerate(CASE_IDS):
        raw_case = raw_cases[index]
        if not isinstance(raw_case, dict) or raw_case.get("id") != case_id:
            msg = f"case {index} must be {case_id!r}"
            raise BenchmarkError(msg)
        if set(raw_case) != {
            "id",
            "title",
            "acceptance_criteria",
            "scenario",
            "expected",
        }:
            msg = f"case {case_id!r} has unexpected fields"
            raise BenchmarkError(msg)
        for field in ("acceptance_criteria", "scenario"):
            items = raw_case[field]
            if (
                not isinstance(items, list)
                or not items
                or not all(isinstance(item, str) and item for item in items)
            ):
                msg = f"case {case_id!r} {field} must be non-empty strings"
                raise BenchmarkError(msg)
        if not isinstance(raw_case["expected"], dict):
            msg = f"case {case_id!r} expected must be an object"
            raise BenchmarkError(msg)
        cases.append(raw_case)
    return cases


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contract_digest(contract_dir: Path) -> str:
    """Return a digest over the paths and bytes of SKILL.md and references/."""
    digest = hashlib.sha256()
    skill = contract_dir / "SKILL.md"
    references = contract_dir / "references"
    files = [skill]
    if references.is_dir():
        files.extend(sorted(path for path in references.rglob("*") if path.is_file()))
    files = [path for path in files if path.is_file()]
    if not files:
        msg = f"contract directory is empty: {contract_dir}"
        raise BenchmarkError(msg)
    for path in files:
        digest.update(path.relative_to(contract_dir).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_prompt(contract_dir: Path, case: dict[str, object]) -> str:
    """Return the read-only simulation prompt for one case."""
    # validate_cases guarantees both fields are non-empty lists of strings.
    criteria = "\n".join(
        f"- {item}" for item in cast("list[str]", case["acceptance_criteria"])
    )
    scenario = "\n".join(f"- {item}" for item in cast("list[str]", case["scenario"]))
    return (
        f"Read and apply `{contract_dir / 'SKILL.md'}` and only the phase "
        "references it routes for this scenario. This is a public synthetic "
        "benchmark simulation. Do not mutate files, contact services, ask "
        "questions, or perform delivery. Return only JSON matching the supplied "
        "schema.\n"
        "\n"
        f"Case: {case['id']} - {case['title']}\n"
        "\n"
        "Acceptance criteria:\n"
        f"{criteria}\n"
        "\n"
        "Scenario:\n"
        f"{scenario}\n"
        "\n"
        "Count only workflow actions required by the loaded contract. A gate "
        "execution means an actual dispatch or command in this continuation; a "
        "reused result and a pending hosted check each have count zero. Count a "
        "duplicate gate execution only when the same gate runs again with "
        "unchanged relevant inputs. A previously granted approval is neither a "
        "new approval request nor a new approval wait when scope is unchanged; "
        "do not recount its historical request or wait. Preserve every untested "
        "criterion explicitly. A required security defect or unavailable "
        "required native test blocks delivery. Wait duration is null when the "
        "scenario provides no measured duration. Report the scenario's user "
        "interruption count, even when the continuation introduces none.\n"
    )


def parse_codex_usage(stdout: str) -> dict[str, int]:
    """Sum token usage over the turn.completed events of Codex JSONL output."""
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "turn.completed":
            continue
        raw_usage = event.get("usage")
        if not isinstance(raw_usage, dict):
            continue
        for field in usage:
            value = raw_usage.get(field)
            if isinstance(value, int) and not isinstance(value, bool):
                usage[field] += value
    return usage


def run_sample(
    settings: CodexSettings,
    contract_dir: Path,
    case: dict[str, object],
) -> dict[str, object]:
    """Run one read-only Codex sample and attach measured timing and usage."""
    with tempfile.TemporaryDirectory(prefix="ship-it-delivery-benchmark-") as temp:
        output = Path(temp) / "result.json"
        command = [
            settings.codex,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--ignore-rules",
            "--model",
            settings.model,
            "--config",
            f'model_reasoning_effort="{settings.reasoning_effort}"',
            "--output-schema",
            str(settings.result_schema),
            "--output-last-message",
            str(output),
            "--json",
            "-",
        ]
        started = time.perf_counter_ns()
        try:
            # S603: argv list with no shell; the Codex binary is the caller's --codex.
            completed = subprocess.run(  # noqa: S603
                command,
                input=build_prompt(contract_dir, case),
                text=True,
                capture_output=True,
                timeout=settings.timeout,
                check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            msg = f"Codex failed for case {case['id']}: {type(error).__name__}"
            raise BenchmarkError(msg) from error
        elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
        if completed.returncode != 0:
            msg = f"Codex exited nonzero for case {case['id']}"
            raise BenchmarkError(msg)
        result = load_object(output, f"Codex result for {case['id']}")
        result["timing"] = {
            "elapsed_ms": elapsed_ms,
            "active_ms": elapsed_ms,
            "wait_ms": {
                "approval": None,
                "hosted_service": None,
                "resource_queue": None,
            },
        }
        result["usage"] = parse_codex_usage(completed.stdout)
        return result


def normalized_environment(settings: CodexSettings) -> dict[str, object]:
    """Return the adapter, model, and host fields recorded in a report."""
    # S603: argv list with no shell; the Codex binary is the caller's --codex.
    version = subprocess.run(  # noqa: S603
        [settings.codex, "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    if version.returncode != 0:
        msg = "cannot read Codex version"
        raise BenchmarkError(msg)
    return {
        "adapter": "codex-exec-read-only",
        "adapter_version": version.stdout.strip(),
        "model": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "sandbox": "read-only",
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
        "python": platform.python_version(),
    }


def _is_count(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_non_negative_count(value: object) -> bool:
    return _is_count(value) and value >= 0


def _is_positive_count(value: object) -> bool:
    return _is_count(value) and value >= 1


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _exceeds_limit(value: object, maximum: object) -> bool:
    """Return whether value is malformed or above an integer maximum."""
    return not _is_count(value) or not isinstance(maximum, int) or value > maximum


def _untested_criteria_missing(
    expected: dict[str, object],
    result: dict[str, object],
) -> bool:
    required_untested = expected.get("required_untested_criteria", [])
    actual_untested = result.get("untested_criteria", [])
    if not isinstance(required_untested, list) or not isinstance(
        actual_untested,
        list,
    ):
        return True
    required_phrases = [str(item).casefold() for item in required_untested]
    actual_phrases = [str(item).casefold() for item in actual_untested]
    return any(
        not any(required in actual for actual in actual_phrases)
        for required in required_phrases
    )


def _derived_duplicates(gate_executions: object) -> int | None:
    """Return repeats summed per gate, or None when any execution is malformed."""
    if not isinstance(gate_executions, list):
        return None
    totals: dict[str, int] = {}
    for execution in gate_executions:
        if not isinstance(execution, dict):
            return None
        gate = execution.get("gate")
        count = execution.get("count")
        if not isinstance(gate, str) or not gate or not _is_count(count) or count < 0:
            return None
        totals[gate] = totals.get(gate, 0) + count
    return sum(max(total - 1, 0) for total in totals.values())


def _approval_waits(waits: object) -> int | None:
    if not isinstance(waits, list):
        return None
    return sum(
        wait.get("count", 0)
        for wait in waits
        if isinstance(wait, dict)
        and wait.get("kind") == "approval"
        and _is_count(wait.get("count"))
    )


def _candidate_failures(
    expected: dict[str, object],
    result: dict[str, object],
) -> list[str]:
    failures = [
        f"{field}: expected at most {expected.get(limit)}, got {result.get(field)!r}"
        for field, limit in CANDIDATE_LIMITS
        if _exceeds_limit(result.get(field), expected.get(limit))
    ]
    duplicates = _derived_duplicates(result.get("gate_executions"))
    maximum_duplicates = expected.get("candidate_max_duplicate_gate_executions")
    if (
        isinstance(maximum_duplicates, int)
        and duplicates is not None
        and duplicates > maximum_duplicates
    ):
        failures.append(
            "derived duplicate gate executions: expected at most "
            f"{maximum_duplicates}, got {duplicates}",
        )
    approval_requests = result.get("approval_requests")
    maximum_requests = expected.get("candidate_max_approval_requests")
    if maximum_requests is not None and _exceeds_limit(
        approval_requests,
        maximum_requests,
    ):
        failures.append(
            "approval_requests: expected at most "
            f"{maximum_requests}, got {approval_requests!r}",
        )
    approval_waits = _approval_waits(result.get("waits"))
    maximum_waits = expected.get("candidate_max_approval_waits")
    if maximum_waits is not None and _exceeds_limit(approval_waits, maximum_waits):
        failures.append(
            f"approval waits: expected at most {maximum_waits}, got {approval_waits!r}",
        )
    return failures


def validate_result(
    case: dict[str, object],
    result: dict[str, object],
    variant: str,
) -> list[str]:
    """Return acceptance failures of one result; candidates also face limits."""
    expected = case["expected"]
    if not isinstance(expected, dict):
        return ["invalid expected result"]
    failures = [
        f"{field}: expected {expected.get(field)!r}, got {result.get(field)!r}"
        for field in (
            "outcome",
            "confirmed_defect_detected",
            "required_delivery_blocker_present",
        )
        if result.get(field) != expected.get(field)
    ]
    if _untested_criteria_missing(expected, result):
        failures.append("required untested criteria are missing")
    if variant == "candidate":
        failures.extend(_candidate_failures(expected, result))
    return failures


def _is_gate_execution(gate: object) -> bool:
    return (
        isinstance(gate, dict)
        and set(gate) == {"gate", "count", "status"}
        and isinstance(gate["gate"], str)
        and _is_non_negative_count(gate["count"])
        and gate["status"] in GATE_STATUSES
    )


def _is_wait(wait: object) -> bool:
    return (
        isinstance(wait, dict)
        and set(wait) == {"kind", "count", "duration_ms"}
        and isinstance(wait["kind"], str)
        and wait["kind"] in WAIT_KINDS
        and _is_non_negative_count(wait["count"])
        and (wait["duration_ms"] is None or _is_non_negative_count(wait["duration_ms"]))
    )


def _wait_ms_failures(wait_ms: object) -> list[str]:
    if not isinstance(wait_ms, dict) or set(wait_ms) != WAIT_KINDS:
        return ["timing.wait_ms fields do not match the benchmark schema"]
    if any(
        value is not None and not _is_non_negative_count(value)
        for value in wait_ms.values()
    ):
        return ["timing.wait_ms values must be null or non-negative integers"]
    return []


def _timing_failures(timing: object) -> list[str]:
    if not isinstance(timing, dict) or set(timing) != {
        "elapsed_ms",
        "active_ms",
        "wait_ms",
    }:
        return ["timing fields do not match the benchmark schema"]
    failures = [
        f"timing.{field} must be a non-negative integer"
        for field in ("elapsed_ms", "active_ms")
        if not _is_non_negative_count(timing[field])
    ]
    if (
        isinstance(timing["elapsed_ms"], int)
        and isinstance(timing["active_ms"], int)
        and timing["active_ms"] > timing["elapsed_ms"]
    ):
        failures.append("timing.active_ms must not exceed elapsed_ms")
    failures.extend(_wait_ms_failures(timing["wait_ms"]))
    return failures


def _usage_failures(usage: object) -> list[str]:
    if not isinstance(usage, dict) or set(usage) != {
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
    }:
        return ["usage fields do not match the benchmark schema"]
    if any(not _is_non_negative_count(value) for value in usage.values()):
        return ["usage values must be non-negative integers"]
    return []


def validate_result_shape(result: dict[str, object]) -> list[str]:
    """Return schema failures of one normalized result."""
    if set(result) != RESULT_FIELDS:
        return ["result fields do not match the benchmark schema"]
    failures: list[str] = []
    if result["outcome"] not in {"accepted", "blocked", "waiting"}:
        failures.append("outcome is invalid")
    failures.extend(
        f"{field} must be a non-negative integer"
        for field in (
            "approval_requests",
            "redundant_approval_requests",
            "duplicate_gate_executions",
            "user_interruptions",
            "concurrent_workers_peak",
        )
        if not _is_non_negative_count(result[field])
    )
    failures.extend(
        f"{field} must be a boolean"
        for field in (
            "confirmed_defect_detected",
            "required_delivery_blocker_present",
        )
        if not isinstance(result[field], bool)
    )
    failures.extend(
        f"{field} must be an array"
        for field in ("required_gates", "gate_executions", "waits", "untested_criteria")
        if not isinstance(result[field], list)
    )
    failures.extend(
        f"{field} must contain strings"
        for field in ("required_gates", "untested_criteria")
        if isinstance(values := result[field], list)
        and not all(isinstance(value, str) for value in values)
    )
    gate_executions = result["gate_executions"]
    if isinstance(gate_executions, list) and not all(
        _is_gate_execution(gate) for gate in gate_executions
    ):
        failures.append("gate executions must contain normalized counters")
    waits = result["waits"]
    if isinstance(waits, list) and not all(_is_wait(wait) for wait in waits):
        failures.append("waits must contain normalized counters and durations")
    failures.extend(_timing_failures(result["timing"]))
    failures.extend(_usage_failures(result["usage"]))
    return failures


def metric_total(result: object, field: str) -> int:
    """Return an integer metric of a result, or 0 when absent or malformed."""
    if not isinstance(result, dict):
        return 0
    value = result.get(field)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def nested_metric_total(result: object, parent: str, field: str) -> int:
    """Return an integer metric nested under parent, or 0 when absent."""
    if not isinstance(result, dict):
        return 0
    value = result.get(parent)
    return metric_total(value, field)


def wait_total(result: object) -> int:
    """Return the summed count of every wait a result reports."""
    if not isinstance(result, dict) or not isinstance(result.get("waits"), list):
        return 0
    return sum(metric_total(wait, "count") for wait in result["waits"])


def compare_runs(runs: list[dict[str, object]]) -> dict[str, object]:
    """Classify per-case metric totals as improvements, regressions, or unchanged."""
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for run in runs:
        key = (str(run["variant"]), str(run["case_id"]))
        grouped.setdefault(key, []).append(run)
    improvements: list[dict[str, object]] = []
    regressions: list[dict[str, object]] = []
    unchanged: list[dict[str, object]] = []
    for case_id in CASE_IDS:
        baseline = grouped[("baseline", case_id)]
        candidate = grouped[("candidate", case_id)]
        for field in (
            "redundant_approval_requests",
            "duplicate_gate_executions",
            "user_interruptions",
        ):
            before = sum(metric_total(item.get("result"), field) for item in baseline)
            after = sum(metric_total(item.get("result"), field) for item in candidate)
            record: dict[str, object] = {
                "case_id": case_id,
                "metric": field,
                "baseline": before,
                "candidate": after,
            }
            if after < before:
                improvements.append(record)
            elif after > before:
                regressions.append(record)
            else:
                unchanged.append(record)
        baseline_elapsed = sum(
            nested_metric_total(item.get("result"), "timing", "elapsed_ms")
            for item in baseline
        ) // len(baseline)
        candidate_elapsed = sum(
            nested_metric_total(item.get("result"), "timing", "elapsed_ms")
            for item in candidate
        ) // len(candidate)
        elapsed_record = {
            "case_id": case_id,
            "metric": "mean_elapsed_ms",
            "baseline": baseline_elapsed,
            "candidate": candidate_elapsed,
        }
        if candidate_elapsed < baseline_elapsed:
            improvements.append(elapsed_record)
        elif candidate_elapsed > baseline_elapsed:
            regressions.append(elapsed_record)
        else:
            unchanged.append(elapsed_record)
        baseline_waits = sum(wait_total(item.get("result")) for item in baseline)
        candidate_waits = sum(wait_total(item.get("result")) for item in candidate)
        wait_record = {
            "case_id": case_id,
            "metric": "reported_wait_count",
            "baseline": baseline_waits,
            "candidate": candidate_waits,
        }
        if candidate_waits < baseline_waits:
            improvements.append(wait_record)
        elif candidate_waits > baseline_waits:
            regressions.append(wait_record)
        else:
            unchanged.append(wait_record)
    return {
        "improvements": improvements,
        "regressions": regressions,
        "unchanged": unchanged,
        "speedup_claimed": False,
        "speedup_reason": (
            "No speedup claim: one sample per case and variant is insufficient "
            "for timing inference, and aggregate candidate elapsed time increased."
        ),
    }


def _provenance_failures(provenance: object) -> list[str]:
    if not isinstance(provenance, dict) or set(provenance) != {
        "baseline_artifact_sha256",
        "baseline_harness_revision",
        "candidate_harness_revision",
    }:
        return [
            "report provenance must identify the artifact and harness revisions",
        ]
    if (
        not SHA256.fullmatch(str(provenance["baseline_artifact_sha256"]))
        or not SHA.fullmatch(str(provenance["baseline_harness_revision"]))
        or not SHA.fullmatch(str(provenance["candidate_harness_revision"]))
    ):
        return ["report provenance contains an invalid digest or revision"]
    return []


def _metadata_failures(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if report.get("benchmark") != "ship-it-delivery-performance":
        failures.append("report benchmark identifier is invalid")
    environment = report.get("environment")
    if (
        not isinstance(environment, dict)
        or set(environment) != ENVIRONMENT_FIELDS
        or not all(isinstance(value, str) and value for value in environment.values())
    ):
        failures.append("report environment is incomplete")
    failures.extend(
        f"report {field} is invalid"
        for field in ("cases_digest", "result_schema_digest")
        if not SHA256.fullmatch(str(report.get(field)))
    )
    failures.extend(_provenance_failures(report.get("provenance")))
    return failures


def _run_failures(
    run: object,
    case_map: dict[str, dict[str, object]],
) -> list[str]:
    if not isinstance(run, dict):
        return ["run must be an object"]
    if set(run) != RUN_FIELDS:
        return ["run fields do not match the benchmark schema"]
    failures: list[str] = []
    if not _is_positive_count(run["sample"]):
        failures.append("run sample must be a positive integer")
    if not _matches(SHA, run["source_revision"]):
        failures.append("run source revision is invalid")
    if not _matches(SHA256, run["contract_digest"]):
        failures.append("run contract digest is invalid")
    case = case_map.get(str(run.get("case_id")))
    result = run.get("result")
    if case is None or not isinstance(result, dict):
        return [*failures, "run case or result is invalid"]
    prefix = f"{run.get('variant')}/{run.get('case_id')}"
    failures.extend(f"{prefix}: {failure}" for failure in validate_result_shape(result))
    failures.extend(
        f"{prefix}: {failure}"
        for failure in validate_result(case, result, str(run.get("variant")))
    )
    return failures


def _run_identity_failures(runs: list[object], sample_count: object) -> list[str]:
    """Check sample coverage per pair and revision and digest stability."""
    samples_by_pair: dict[tuple[object, object], set[int]] = {}
    revisions_by_variant: dict[object, set[str]] = {}
    digests_by_variant: dict[object, set[str]] = {}
    for run in runs:
        if not isinstance(run, dict) or set(run) != RUN_FIELDS:
            continue
        variant = run["variant"]
        if _is_positive_count(run["sample"]):
            pair = (variant, run["case_id"])
            samples_by_pair.setdefault(pair, set()).add(run["sample"])
        if _matches(SHA, run["source_revision"]):
            revisions_by_variant.setdefault(variant, set()).add(run["source_revision"])
        if _matches(SHA256, run["contract_digest"]):
            digests_by_variant.setdefault(variant, set()).add(run["contract_digest"])
    failures: list[str] = []
    if _is_count(sample_count):
        expected_samples = set(range(1, sample_count + 1))
        if any(
            samples_by_pair.get(pair) != expected_samples for pair in EXPECTED_PAIRS
        ):
            failures.append(
                "run samples must cover the declared sequence for every pair",
            )
    if any(len(values) != 1 for values in revisions_by_variant.values()):
        failures.append("source revision must be stable within each variant")
    if any(len(values) != 1 for values in digests_by_variant.values()):
        failures.append("contract digest must be stable within each variant")
    return failures


def validate_report(
    cases: list[dict[str, object]],
    report: dict[str, object],
) -> list[str]:
    """Return every schema, provenance, and acceptance failure of a report."""
    failures: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        failures.append("report schema version is unsupported")
    sample_count = report.get("sample_count_per_case_and_variant")
    if not _is_positive_count(sample_count):
        failures.append("sample count must be a positive integer")
    runs = report.get("runs")
    if not isinstance(runs, list):
        return [*failures, "report runs must be an array"]
    actual_pairs = {
        (run.get("variant"), run.get("case_id"))
        for run in runs
        if isinstance(run, dict)
    }
    if actual_pairs != EXPECTED_PAIRS:
        failures.append("report must cover both variants for exactly five cases")
    if (
        isinstance(sample_count, int)
        and len(runs) != len(EXPECTED_PAIRS) * sample_count
    ):
        failures.append("report run count does not match the declared sample count")
    failures.extend(_metadata_failures(report))
    case_map = {str(case["id"]): case for case in cases}
    for run in runs:
        failures.extend(_run_failures(run, case_map))
    failures.extend(_run_identity_failures(runs, sample_count))
    comparison = report.get("comparison")
    if (
        not isinstance(comparison, dict)
        or comparison.get("speedup_claimed") is not False
    ):
        failures.append("single-sample report must not claim a speedup")
    elif (
        actual_pairs == EXPECTED_PAIRS
        and isinstance(sample_count, int)
        and comparison != compare_runs(runs)
    ):
        failures.append("report comparison does not match its normalized runs")
    return failures


def run_command(args: argparse.Namespace) -> int:
    """Run every case and variant, write the report, and return the exit code."""
    cases = validate_cases(load_object(args.cases, "cases"))
    for revision in (args.baseline_revision, args.candidate_revision):
        if not SHA.fullmatch(revision):
            msg = "revisions must be full lowercase commit SHAs"
            raise BenchmarkError(msg)
    for revision in (
        args.baseline_harness_revision,
        args.candidate_harness_revision,
    ):
        if not SHA.fullmatch(revision):
            msg = "harness revisions must be full lowercase commit SHAs"
            raise BenchmarkError(msg)
    if not SHA256.fullmatch(args.baseline_artifact_sha256):
        msg = "baseline artifact SHA-256 must be lowercase hexadecimal"
        raise BenchmarkError(msg)
    settings = CodexSettings(
        codex=args.codex,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        result_schema=args.result_schema,
        timeout=args.timeout,
    )
    environment = normalized_environment(settings)
    variants = (
        ("baseline", args.baseline_dir, args.baseline_revision),
        ("candidate", args.candidate_dir, args.candidate_revision),
    )
    runs: list[dict[str, object]] = []
    for variant, contract_dir, revision in variants:
        digest = contract_digest(contract_dir)
        for case in cases:
            for sample in range(1, args.samples + 1):
                result = run_sample(settings, contract_dir, case)
                runs.append(
                    {
                        "variant": variant,
                        "case_id": case["id"],
                        "sample": sample,
                        "source_revision": revision,
                        "contract_digest": digest,
                        "result": result,
                    },
                )
    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "ship-it-delivery-performance",
        "sample_count_per_case_and_variant": args.samples,
        "environment": environment,
        "provenance": {
            "baseline_artifact_sha256": args.baseline_artifact_sha256,
            "baseline_harness_revision": args.baseline_harness_revision,
            "candidate_harness_revision": args.candidate_harness_revision,
        },
        "cases_digest": sha256_file(args.cases),
        "result_schema_digest": sha256_file(args.result_schema),
        "runs": runs,
        "comparison": compare_runs(runs),
    }
    failures = validate_report(cases, report)
    report["acceptance"] = {
        "status": "passed" if not failures else "failed",
        "failures": failures,
    }
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if not failures else 1


def validate_command(args: argparse.Namespace) -> int:
    """Print the validation status of a saved report and return the exit code."""
    cases = validate_cases(load_object(args.cases, "cases"))
    report = load_object(args.report, "report")
    failures = validate_report(cases, report)
    print(
        json.dumps(
            {"status": "passed" if not failures else "failed", "failures": failures},
            sort_keys=True,
        ),
    )
    return 0 if not failures else 1


def argument_parser() -> argparse.ArgumentParser:
    """Return the CLI parser with the run and validate subcommands."""
    parser = argparse.ArgumentParser(
        description="Run the ship-it delivery performance benchmark",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--cases", type=Path, required=True)
    run.add_argument("--result-schema", type=Path, required=True)
    run.add_argument("--baseline-dir", type=Path, required=True)
    run.add_argument("--candidate-dir", type=Path, required=True)
    run.add_argument("--baseline-revision", required=True)
    run.add_argument("--candidate-revision", required=True)
    run.add_argument("--baseline-artifact-sha256", required=True)
    run.add_argument("--baseline-harness-revision", required=True)
    run.add_argument("--candidate-harness-revision", required=True)
    run.add_argument("--codex", default="codex")
    run.add_argument("--model", required=True)
    run.add_argument("--reasoning-effort", default="high")
    run.add_argument("--samples", type=int, default=1)
    run.add_argument("--timeout", type=float, default=300.0)
    run.add_argument("--output", type=Path, required=True)
    run.set_defaults(handler=run_command)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--cases", type=Path, required=True)
    validate.add_argument("--report", type=Path, required=True)
    validate.set_defaults(handler=validate_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return its exit code."""
    args = argument_parser().parse_args(argv)
    if getattr(args, "samples", 1) < 1:
        print("samples must be positive", file=sys.stderr)
        return 2
    try:
        return args.handler(args)
    except BenchmarkError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
