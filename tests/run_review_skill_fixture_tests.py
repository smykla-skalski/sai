#!/usr/bin/env python3
"""Test runner for review-skill validation scripts.

Runs two suites:
1) integration checks via validate.py on fixture skills
2) direct script regression checks for modified checker scripts

Usage:
    ./tests/run_review_skill_fixture_tests.py
    ./tests/run_review_skill_fixture_tests.py --verbose

Exit codes: 0 = all pass, 1 = any fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Union, cast

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FIXTURES_DIR = SCRIPT_DIR / "fixtures" / "review-skill"
CHECKERS_DIR = (
    REPO_ROOT / "claude" / "review-skill" / "skills" / "review-skill" / "scripts"
)
VALIDATE_SCRIPT = CHECKERS_DIR / "validate.py"

ExpectationValue = Union[bool, dict[str, object]]  # noqa: UP007

# Each fixture maps to expected outcomes: {check_id: expectation}
# bool -> expected pass value
# dict -> supports keys: pass, level, detail_contains
EXPECTATIONS: dict[str, dict[str, ExpectationValue]] = {
    "api-side-effect-no-dmi": {
        "CF-side-effect": False,
    },
    "api-side-effect-with-dmi": {
        "CF-side-effect": True,
    },
    "duplicate-tables": {
        "RF-dup-tables-info": True,
    },
    "example-flags-good-coverage": {
        "FC-example-flags": True,
    },
    "example-flags-low-coverage": {
        "FC-example-flags": False,
    },
    "failing-read-gate": {
        "FM-name-present": True,
        "FM-desc-present": True,
        "RG-gate-present": False,
        "RG-passive": False,
    },
    "good-examples": {
        "BP-example-tags": True,
        "BP-over-prompting": True,
    },
    "legacy-shell-info": {
        "SD-legacy-bash-info": True,
    },
    "limited-examples": {
        "BP-example-tags": True,
    },
    "long-description": {
        "FM-desc-length": False,
        "FM-desc-present": True,
    },
    "missing-examples": {
        "BP-example-tags": False,
        "BP-over-prompting": False,
    },
    "overdeclared-tools": {
        "FM-name-present": True,
        "CF-tools-usage": False,
    },
    "passing-skill": {
        "FM-name-present": True,
        "FM-name-format": True,
        "FM-desc-present": True,
        "FM-desc-length": True,
        "FM-tools-present": True,
        "CT-no-secrets": True,
        "CT-no-grading": True,
        "CT-long-prose": True,
        "BP-example-tags": True,
        "FC-hint-doc": True,
        "FC-doc-hint": True,
        "FC-doc-workflow": True,
        "FC-example-flags": True,
    },
    "side-effect-no-dmi": {
        "CF-tools-usage": False,
        "CF-side-effect": False,
    },
}

SCRIPT_CASES: tuple[dict[str, object], ...] = (
    {
        "name": "bp-example-tags-info-threshold",
        "fixture": "limited-examples",
        "command": [
            str(CHECKERS_DIR / "check-best-practices.py"),
            "{fixture}",
            "--check",
            "BP-example-tags",
        ],
        "expectations": {
            "BP-example-tags": {
                "pass": True,
                "level": "info",
                "detail_contains": "Found 2 <example> tag(s)",
            },
        },
    },
    {
        "name": "config-api-side-effect-fail",
        "fixture": "api-side-effect-no-dmi",
        "command": [
            str(CHECKERS_DIR / "check-config.py"),
            "{fixture}",
            "--check",
            "CF-side-effect",
        ],
        "expectations": {
            "CF-side-effect": {
                "pass": False,
                "detail_contains": ["api=", "missing"],
            },
        },
    },
    {
        "name": "config-api-side-effect-pass-with-dmi",
        "fixture": "api-side-effect-with-dmi",
        "command": [
            str(CHECKERS_DIR / "check-config.py"),
            "{fixture}",
            "--check",
            "CF-side-effect",
        ],
        "expectations": {
            "CF-side-effect": {
                "pass": True,
                "detail_contains": ["api=", "is set"],
            },
        },
    },
    {
        "name": "scripts-legacy-shell-info",
        "fixture": "legacy-shell-info",
        "command": [
            str(CHECKERS_DIR / "check-scripts-dir.py"),
            "{fixture}",
            "--check",
            "SD-legacy-bash-info",
        ],
        "expectations": {
            "SD-legacy-bash-info": {
                "pass": True,
                "detail_contains": "Found 1 top-level legacy .sh script(s)",
            },
        },
    },
    {
        "name": "flag-coverage-low",
        "fixture": "example-flags-low-coverage",
        "command": [
            str(CHECKERS_DIR / "check-flag-coverage.py"),
            "{fixture}",
            "--check",
            "FC-example-flags",
        ],
        "expectations": {
            "FC-example-flags": {
                "pass": False,
                "detail_contains": "below 50% threshold",
            },
        },
    },
    {
        "name": "flag-coverage-good",
        "fixture": "example-flags-good-coverage",
        "command": [
            str(CHECKERS_DIR / "check-flag-coverage.py"),
            "{fixture}",
            "--check",
            "FC-example-flags",
        ],
        "expectations": {
            "FC-example-flags": {
                "pass": True,
                "detail_contains": "50%",
            },
        },
    },
    {
        "name": "references-duplicate-tables",
        "fixture": "duplicate-tables",
        "command": [
            str(CHECKERS_DIR / "check-references.py"),
            "{fixture}",
            "--check",
            "RF-dup-tables-info",
        ],
        "expectations": {
            "RF-dup-tables-info": {
                "pass": True,
                "detail_contains": "INFO: 1 markdown table(s)",
            },
        },
    },
)


def run_command(command: list[str]) -> tuple[int, dict[str, dict[str, Any]]]:
    """Run command and return (returncode, check_id -> check_record)."""
    result = subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    checks: dict[str, dict[str, Any]] = {}

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("kind") != "check":
            continue

        check_id = record.get("check")
        if isinstance(check_id, str):
            checks[check_id] = record

    return result.returncode, checks


def _assert_expectation(
    *,
    label: str,
    check_id: str,
    record: dict[str, Any] | None,
    expected: ExpectationValue,
    verbose: bool,
) -> int:
    """Validate one expected record and print mismatch details."""
    if record is None:
        print(f"  FAIL {label}/{check_id}: check not emitted")
        return 1

    if isinstance(expected, bool):
        failures = _assert_pass(
            label=label,
            check_id=check_id,
            actual_pass=record.get("pass"),
            expected_pass=expected,
        )
        if failures > 0:
            return failures
        if verbose:
            status = "pass" if bool(record.get("pass")) else "fail"
            print(f"  OK   {label}/{check_id}: {status}")
        return 0

    failures = 0

    if "pass" in expected:
        failures += _assert_pass(
            label=label,
            check_id=check_id,
            actual_pass=record.get("pass"),
            expected_pass=bool(expected["pass"]),
        )

    if "level" in expected:
        failures += _assert_level(
            label=label,
            check_id=check_id,
            actual_level=record.get("level"),
            expected_level=expected["level"],
        )

    if "detail_contains" in expected:
        failures += _assert_detail_contains(
            label=label,
            check_id=check_id,
            detail=str(record.get("detail", "")),
            raw_contains=expected["detail_contains"],
        )

    if failures == 0 and verbose:
        print(f"  OK   {label}/{check_id}: matched")

    return failures


def _assert_pass(
    *,
    label: str,
    check_id: str,
    actual_pass: object,
    expected_pass: bool,
) -> int:
    """Assert the check pass/fail state."""
    if actual_pass == expected_pass:
        return 0

    expected_str = "pass" if expected_pass else "fail"
    actual_str = "pass" if actual_pass else "fail"
    print(f"  FAIL {label}/{check_id}: expected {expected_str}, got {actual_str}")
    return 1


def _assert_level(
    *,
    label: str,
    check_id: str,
    actual_level: object,
    expected_level: object,
) -> int:
    """Assert the check level field."""
    if actual_level == expected_level:
        return 0

    print(
        f"  FAIL {label}/{check_id}: "
        f"expected level {expected_level!r}, got {actual_level!r}",
    )
    return 1


def _assert_detail_contains(
    *,
    label: str,
    check_id: str,
    detail: str,
    raw_contains: object,
) -> int:
    """Assert that detail contains required snippets."""
    if isinstance(raw_contains, str):
        needles = [raw_contains]
    elif isinstance(raw_contains, (list, tuple, set)):
        needles = [str(item) for item in raw_contains]
    else:
        needles = [str(raw_contains)]

    failures = 0
    for needle in needles:
        if needle in detail:
            continue
        print(f"  FAIL {label}/{check_id}: detail missing {needle!r}")
        failures += 1

    return failures


def run_validate_suite(*, verbose: bool) -> tuple[int, int]:
    """Run validate.py expectations on all fixtures."""
    assertions = 0
    failures = 0

    for fixture_name, expectations in sorted(EXPECTATIONS.items()):
        fixture_dir = FIXTURES_DIR / fixture_name
        if not fixture_dir.is_dir():
            print(f"SKIP {fixture_name}: directory not found")
            continue

        rc, records = run_command(
            [
                sys.executable,
                str(VALIDATE_SCRIPT),
                str(fixture_dir),
            ],
        )
        if rc not in (0, 1):
            print(f"  FAIL {fixture_name}: validate.py exit code {rc}")
            failures += 1
            continue

        fixture_failures = 0
        for check_id, expected in expectations.items():
            assertions += 1
            fixture_failures += _assert_expectation(
                label=fixture_name,
                check_id=check_id,
                record=records.get(check_id),
                expected=expected,
                verbose=verbose,
            )

        if fixture_failures == 0:
            print(f"OK   {fixture_name} ({len(expectations)} assertions)")
        failures += fixture_failures

    return assertions, failures


def run_script_suite(*, verbose: bool) -> tuple[int, int]:
    """Run direct checker regression cases."""
    assertions = 0
    failures = 0

    for case in SCRIPT_CASES:
        name = str(case["name"])
        fixture_name = str(case["fixture"])
        fixture_dir = FIXTURES_DIR / fixture_name
        if not fixture_dir.is_dir():
            print(f"SKIP {name}: fixture directory not found")
            continue

        command_template = cast("list[str]", case["command"])
        command = [part.format(fixture=str(fixture_dir)) for part in command_template]
        rc, records = run_command(command)
        if rc not in (0, 1):
            print(f"  FAIL {name}: script exit code {rc}")
            failures += 1
            continue

        expectations = cast("dict[str, ExpectationValue]", case["expectations"])
        case_failures = 0
        for check_id, expected in expectations.items():
            assertions += 1
            case_failures += _assert_expectation(
                label=name,
                check_id=check_id,
                record=records.get(check_id),
                expected=expected,
                verbose=verbose,
            )

        if case_failures == 0:
            print(f"OK   {name} ({len(expectations)} assertions)")
        failures += case_failures

    return assertions, failures


def run_self_test() -> int:
    """Run validate.py against review-skill itself and return failures."""
    review_skill_dir = REPO_ROOT / "claude" / "review-skill" / "skills" / "review-skill"
    rc, records = run_command(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            str(review_skill_dir),
        ],
    )

    if rc != 0:
        failing = [
            check_id
            for check_id, record in records.items()
            if record.get("pass") is False
        ]
        print(
            f"FAIL self-test: validate.py exit={rc}, failing checks: {sorted(failing)}",
        )
        return 1

    print(f"OK   self-test ({len(records)} checks, all pass)")
    return 0


def main() -> int:
    """Run validate and script regression suites for review-skill fixtures."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("== validate suite ==")
    assertions_a, failures_a = run_validate_suite(verbose=verbose)

    print("\n== script suite ==")
    assertions_b, failures_b = run_script_suite(verbose=verbose)

    total_assertions = assertions_a + assertions_b
    total_failures = failures_a + failures_b

    print(f"\n{total_assertions} assertions, {total_failures} failures")

    total_failures += run_self_test()
    return 1 if total_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
