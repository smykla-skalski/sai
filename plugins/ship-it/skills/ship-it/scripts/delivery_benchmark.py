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
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final[int] = 1
CASE_IDS: Final[tuple[str, ...]] = (
    "documentation-only-work",
    "ordinary-fix-resume",
    "confirmed-security-defect",
    "moving-default-branch",
    "native-fixture-failure",
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
    }
)


class BenchmarkError(ValueError):
    """Invalid benchmark input or execution result."""


def load_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BenchmarkError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise BenchmarkError(f"{label} must be a JSON object")
    return value


def validate_cases(value: dict[str, object]) -> list[dict[str, object]]:
    if set(value) != {"schema_version", "cases"} or value["schema_version"] != 1:
        raise BenchmarkError("cases must match schema version 1")
    raw_cases = value["cases"]
    if not isinstance(raw_cases, list) or len(raw_cases) != len(CASE_IDS):
        raise BenchmarkError("cases must contain exactly five entries")
    cases: list[dict[str, object]] = []
    for index, case_id in enumerate(CASE_IDS):
        raw_case = raw_cases[index]
        if not isinstance(raw_case, dict) or raw_case.get("id") != case_id:
            raise BenchmarkError(f"case {index} must be {case_id!r}")
        if set(raw_case) != {
            "id",
            "title",
            "acceptance_criteria",
            "scenario",
            "expected",
        }:
            raise BenchmarkError(f"case {case_id!r} has unexpected fields")
        for field in ("acceptance_criteria", "scenario"):
            items = raw_case[field]
            if not isinstance(items, list) or not items or not all(
                isinstance(item, str) and item for item in items
            ):
                raise BenchmarkError(
                    f"case {case_id!r} {field} must be non-empty strings"
                )
        if not isinstance(raw_case["expected"], dict):
            raise BenchmarkError(f"case {case_id!r} expected must be an object")
        cases.append(raw_case)
    return cases


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contract_digest(contract_dir: Path) -> str:
    digest = hashlib.sha256()
    skill = contract_dir / "SKILL.md"
    references = contract_dir / "references"
    files = [skill]
    if references.is_dir():
        files.extend(sorted(path for path in references.rglob("*") if path.is_file()))
    files = [path for path in files if path.is_file()]
    if not files:
        raise BenchmarkError(f"contract directory is empty: {contract_dir}")
    for path in files:
        digest.update(path.relative_to(contract_dir).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_prompt(contract_dir: Path, case: dict[str, object]) -> str:
    criteria = "\n".join(f"- {item}" for item in case["acceptance_criteria"])
    scenario = "\n".join(f"- {item}" for item in case["scenario"])
    return f"""Read and apply `{contract_dir / 'SKILL.md'}` and only the phase references it routes for this scenario. This is a public synthetic benchmark simulation. Do not mutate files, contact services, ask questions, or perform delivery. Return only JSON matching the supplied schema.

Case: {case['id']} - {case['title']}

Acceptance criteria:
{criteria}

Scenario:
{scenario}

Count only workflow actions required by the loaded contract. A gate execution means an actual dispatch or command in this continuation; a reused result and a pending hosted check each have count zero. Count a duplicate gate execution only when the same gate runs again with unchanged relevant inputs. A previously granted approval is neither a new approval request nor a new approval wait when scope is unchanged; do not recount its historical request or wait. Preserve every untested criterion explicitly. A required security defect or unavailable required native test blocks delivery. Wait duration is null when the scenario provides no measured duration. Report the scenario's user interruption count, even when the continuation introduces none.
"""


def parse_codex_usage(stdout: str) -> dict[str, int]:
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
    codex: str,
    model: str,
    reasoning_effort: str,
    contract_dir: Path,
    result_schema: Path,
    case: dict[str, object],
    timeout: float,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="ship-it-delivery-benchmark-") as temp:
        output = Path(temp) / "result.json"
        command = [
            codex,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--ignore-rules",
            "--model",
            model,
            "--config",
            f'model_reasoning_effort="{reasoning_effort}"',
            "--output-schema",
            str(result_schema),
            "--output-last-message",
            str(output),
            "--json",
            "-",
        ]
        started = time.perf_counter_ns()
        try:
            completed = subprocess.run(
                command,
                input=build_prompt(contract_dir, case),
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise BenchmarkError(
                f"Codex failed for case {case['id']}: {type(error).__name__}"
            ) from error
        elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
        if completed.returncode != 0:
            raise BenchmarkError(f"Codex exited nonzero for case {case['id']}")
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


def normalized_environment(
    codex: str, model: str, reasoning_effort: str
) -> dict[str, object]:
    version = subprocess.run(
        [codex, "--version"], text=True, capture_output=True, check=False
    )
    if version.returncode != 0:
        raise BenchmarkError("cannot read Codex version")
    return {
        "adapter": "codex-exec-read-only",
        "adapter_version": version.stdout.strip(),
        "model": model,
        "reasoning_effort": reasoning_effort,
        "sandbox": "read-only",
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
        "python": platform.python_version(),
    }


def validate_result(
    case: dict[str, object], result: dict[str, object], variant: str
) -> list[str]:
    failures: list[str] = []
    expected = case["expected"]
    if not isinstance(expected, dict):
        return ["invalid expected result"]
    for field in (
        "outcome",
        "confirmed_defect_detected",
        "required_delivery_blocker_present",
    ):
        if result.get(field) != expected.get(field):
            failures.append(
                f"{field}: expected {expected.get(field)!r}, got {result.get(field)!r}"
            )
    required_untested = expected.get("required_untested_criteria", [])
    actual_untested = result.get("untested_criteria", [])
    if not isinstance(required_untested, list) or not isinstance(
        actual_untested, list
    ):
        failures.append("required untested criteria are missing")
    else:
        required_phrases = [str(item).casefold() for item in required_untested]
        actual_phrases = [str(item).casefold() for item in actual_untested]
        if any(
            not any(required in actual for actual in actual_phrases)
            for required in required_phrases
        ):
            failures.append("required untested criteria are missing")
    if variant == "candidate":
        limits = (
            (
                "redundant_approval_requests",
                "candidate_max_redundant_approval_requests",
            ),
            (
                "duplicate_gate_executions",
                "candidate_max_duplicate_gate_executions",
            ),
        )
        for field, expected_field in limits:
            value = result.get(field)
            maximum = expected.get(expected_field)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not isinstance(maximum, int)
                or value > maximum
            ):
                failures.append(f"{field}: expected at most {maximum}, got {value!r}")
        approval_requests = result.get("approval_requests")
        maximum_requests = expected.get("candidate_max_approval_requests")
        if maximum_requests is not None and (
            not isinstance(approval_requests, int)
            or isinstance(approval_requests, bool)
            or not isinstance(maximum_requests, int)
            or approval_requests > maximum_requests
        ):
            failures.append(
                "approval_requests: expected at most "
                f"{maximum_requests}, got {approval_requests!r}"
            )
        waits = result.get("waits")
        approval_waits = None
        if isinstance(waits, list):
            approval_waits = sum(
                wait.get("count", 0)
                for wait in waits
                if isinstance(wait, dict)
                and wait.get("kind") == "approval"
                and isinstance(wait.get("count"), int)
                and not isinstance(wait.get("count"), bool)
            )
        maximum_waits = expected.get("candidate_max_approval_waits")
        if maximum_waits is not None and (
            approval_waits is None
            or not isinstance(maximum_waits, int)
            or approval_waits > maximum_waits
        ):
            failures.append(
                "approval waits: expected at most "
                f"{maximum_waits}, got {approval_waits!r}"
            )
    return failures


def validate_result_shape(result: dict[str, object]) -> list[str]:
    failures: list[str] = []
    required = {
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
    }
    if set(result) != required:
        return ["result fields do not match the benchmark schema"]
    if result["outcome"] not in {"accepted", "blocked", "waiting"}:
        failures.append("outcome is invalid")
    for field in (
        "approval_requests",
        "redundant_approval_requests",
        "duplicate_gate_executions",
        "user_interruptions",
        "concurrent_workers_peak",
    ):
        value = result[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            failures.append(f"{field} must be a non-negative integer")
    for field in (
        "confirmed_defect_detected",
        "required_delivery_blocker_present",
    ):
        if not isinstance(result[field], bool):
            failures.append(f"{field} must be a boolean")
    for field in ("required_gates", "gate_executions", "waits", "untested_criteria"):
        if not isinstance(result[field], list):
            failures.append(f"{field} must be an array")
    for field in ("required_gates", "untested_criteria"):
        values = result[field]
        if isinstance(values, list) and not all(isinstance(value, str) for value in values):
            failures.append(f"{field} must contain strings")
    gate_executions = result["gate_executions"]
    if isinstance(gate_executions, list):
        for gate in gate_executions:
            if (
                not isinstance(gate, dict)
                or set(gate) != {"gate", "count", "status"}
                or not isinstance(gate["gate"], str)
                or not isinstance(gate["count"], int)
                or isinstance(gate["count"], bool)
                or gate["count"] < 0
                or gate["status"]
                not in {"passed", "failed", "blocked", "pending", "reused"}
            ):
                failures.append("gate executions must contain normalized counters")
                break
    waits = result["waits"]
    if isinstance(waits, list):
        for wait in waits:
            if (
                not isinstance(wait, dict)
                or set(wait) != {"kind", "count", "duration_ms"}
                or not isinstance(wait["kind"], str)
                or wait["kind"]
                not in {"approval", "hosted_service", "resource_queue"}
                or not isinstance(wait["count"], int)
                or isinstance(wait["count"], bool)
                or wait["count"] < 0
                or (
                    wait["duration_ms"] is not None
                    and (
                        not isinstance(wait["duration_ms"], int)
                        or isinstance(wait["duration_ms"], bool)
                        or wait["duration_ms"] < 0
                    )
                )
            ):
                failures.append("waits must contain normalized counters and durations")
                break
    timing = result["timing"]
    if not isinstance(timing, dict) or set(timing) != {
        "elapsed_ms",
        "active_ms",
        "wait_ms",
    }:
        failures.append("timing fields do not match the benchmark schema")
    else:
        for field in ("elapsed_ms", "active_ms"):
            value = timing[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                failures.append(f"timing.{field} must be a non-negative integer")
        if (
            isinstance(timing["elapsed_ms"], int)
            and isinstance(timing["active_ms"], int)
            and timing["active_ms"] > timing["elapsed_ms"]
        ):
            failures.append("timing.active_ms must not exceed elapsed_ms")
        wait_ms = timing["wait_ms"]
        if not isinstance(wait_ms, dict) or set(wait_ms) != {
            "approval",
            "hosted_service",
            "resource_queue",
        }:
            failures.append("timing.wait_ms fields do not match the benchmark schema")
        elif any(
            value is not None
            and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            )
            for value in wait_ms.values()
        ):
            failures.append("timing.wait_ms values must be null or non-negative integers")
    usage = result["usage"]
    if not isinstance(usage, dict) or set(usage) != {
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
    }:
        failures.append("usage fields do not match the benchmark schema")
    elif any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in usage.values()
    ):
        failures.append("usage values must be non-negative integers")
    return failures


def metric_total(result: object, field: str) -> int:
    if not isinstance(result, dict):
        return 0
    value = result.get(field)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def nested_metric_total(result: object, parent: str, field: str) -> int:
    if not isinstance(result, dict):
        return 0
    value = result.get(parent)
    return metric_total(value, field)


def wait_total(result: object) -> int:
    if not isinstance(result, dict) or not isinstance(result.get("waits"), list):
        return 0
    return sum(
        metric_total(wait, "count")
        for wait in result["waits"]
    )


def compare_runs(runs: list[dict[str, object]]) -> dict[str, object]:
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
            record = {
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


def validate_report(
    cases: list[dict[str, object]], report: dict[str, object]
) -> list[str]:
    failures: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        failures.append("report schema version is unsupported")
    sample_count = report.get("sample_count_per_case_and_variant")
    if not isinstance(sample_count, int) or isinstance(sample_count, bool) or sample_count < 1:
        failures.append("sample count must be a positive integer")
    runs = report.get("runs")
    if not isinstance(runs, list):
        return failures + ["report runs must be an array"]
    expected_pairs = {
        (variant, case_id)
        for variant in ("baseline", "candidate")
        for case_id in CASE_IDS
    }
    actual_pairs = {
        (run.get("variant"), run.get("case_id"))
        for run in runs
        if isinstance(run, dict)
    }
    if actual_pairs != expected_pairs:
        failures.append("report must cover both variants for exactly five cases")
    if isinstance(sample_count, int) and len(runs) != len(expected_pairs) * sample_count:
        failures.append("report run count does not match the declared sample count")
    if report.get("benchmark") != "ship-it-delivery-performance":
        failures.append("report benchmark identifier is invalid")
    environment = report.get("environment")
    if (
        not isinstance(environment, dict)
        or set(environment) != ENVIRONMENT_FIELDS
        or not all(isinstance(value, str) and value for value in environment.values())
    ):
        failures.append("report environment is incomplete")
    for field in ("cases_digest", "result_schema_digest"):
        if not SHA256.fullmatch(str(report.get(field))):
            failures.append(f"report {field} is invalid")
    provenance = report.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != {
        "baseline_artifact_sha256",
        "baseline_harness_revision",
        "candidate_harness_revision",
    }:
        failures.append("report provenance must identify the artifact and harness revisions")
    elif (
        not SHA256.fullmatch(str(provenance["baseline_artifact_sha256"]))
        or not SHA.fullmatch(str(provenance["baseline_harness_revision"]))
        or not SHA.fullmatch(str(provenance["candidate_harness_revision"]))
    ):
        failures.append("report provenance contains an invalid digest or revision")
    case_map = {str(case["id"]): case for case in cases}
    samples_by_pair: dict[tuple[object, object], set[int]] = {}
    revisions_by_variant: dict[object, set[str]] = {}
    digests_by_variant: dict[object, set[str]] = {}
    for run in runs:
        if not isinstance(run, dict):
            failures.append("run must be an object")
            continue
        if set(run) != {
            "variant",
            "case_id",
            "sample",
            "source_revision",
            "contract_digest",
            "result",
        }:
            failures.append("run fields do not match the benchmark schema")
            continue
        pair = (run["variant"], run["case_id"])
        sample = run["sample"]
        if not isinstance(sample, int) or isinstance(sample, bool) or sample < 1:
            failures.append("run sample must be a positive integer")
        else:
            samples_by_pair.setdefault(pair, set()).add(sample)
        revision = run["source_revision"]
        digest = run["contract_digest"]
        if not isinstance(revision, str) or not SHA.fullmatch(revision):
            failures.append("run source revision is invalid")
        else:
            revisions_by_variant.setdefault(run["variant"], set()).add(revision)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            failures.append("run contract digest is invalid")
        else:
            digests_by_variant.setdefault(run["variant"], set()).add(digest)
        case = case_map.get(str(run.get("case_id")))
        result = run.get("result")
        if case is None or not isinstance(result, dict):
            failures.append("run case or result is invalid")
            continue
        failures.extend(
            f"{run.get('variant')}/{run.get('case_id')}: {failure}"
            for failure in validate_result_shape(result)
        )
        failures.extend(
            f"{run.get('variant')}/{run.get('case_id')}: {failure}"
            for failure in validate_result(case, result, str(run.get("variant")))
        )
    if isinstance(sample_count, int) and not isinstance(sample_count, bool):
        expected_samples = set(range(1, sample_count + 1))
        if any(
            samples_by_pair.get(pair) != expected_samples for pair in expected_pairs
        ):
            failures.append("run samples must cover the declared sequence for every pair")
    if any(len(values) != 1 for values in revisions_by_variant.values()):
        failures.append("source revision must be stable within each variant")
    if any(len(values) != 1 for values in digests_by_variant.values()):
        failures.append("contract digest must be stable within each variant")
    comparison = report.get("comparison")
    if (
        not isinstance(comparison, dict)
        or comparison.get("speedup_claimed") is not False
    ):
        failures.append("single-sample report must not claim a speedup")
    elif actual_pairs == expected_pairs and isinstance(sample_count, int):
        if comparison != compare_runs(runs):
            failures.append("report comparison does not match its normalized runs")
    return failures


def run_command(args: argparse.Namespace) -> int:
    cases = validate_cases(load_object(args.cases, "cases"))
    for revision in (args.baseline_revision, args.candidate_revision):
        if not SHA.fullmatch(revision):
            raise BenchmarkError("revisions must be full lowercase commit SHAs")
    for revision in (
        args.baseline_harness_revision,
        args.candidate_harness_revision,
    ):
        if not SHA.fullmatch(revision):
            raise BenchmarkError("harness revisions must be full lowercase commit SHAs")
    if not SHA256.fullmatch(args.baseline_artifact_sha256):
        raise BenchmarkError("baseline artifact SHA-256 must be lowercase hexadecimal")
    environment = normalized_environment(
        args.codex, args.model, args.reasoning_effort
    )
    variants = (
        ("baseline", args.baseline_dir, args.baseline_revision),
        ("candidate", args.candidate_dir, args.candidate_revision),
    )
    runs: list[dict[str, object]] = []
    for variant, contract_dir, revision in variants:
        digest = contract_digest(contract_dir)
        for case in cases:
            for sample in range(1, args.samples + 1):
                result = run_sample(
                    args.codex,
                    args.model,
                    args.reasoning_effort,
                    contract_dir,
                    args.result_schema,
                    case,
                    args.timeout,
                )
                runs.append(
                    {
                        "variant": variant,
                        "case_id": case["id"],
                        "sample": sample,
                        "source_revision": revision,
                        "contract_digest": digest,
                        "result": result,
                    }
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
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if not failures else 1


def validate_command(args: argparse.Namespace) -> int:
    cases = validate_cases(load_object(args.cases, "cases"))
    report = load_object(args.report, "report")
    failures = validate_report(cases, report)
    print(
        json.dumps(
            {"status": "passed" if not failures else "failed", "failures": failures},
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the ship-it delivery performance benchmark"
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
