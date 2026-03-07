#!/usr/bin/env python3
"""Test runner for review-skill validation scripts.

Runs validate.py against fixture skill directories and verifies
expected check outcomes (pass/fail per check ID).

Usage:
    ./run-tests.py
    ./run-tests.py --verbose

Exit codes: 0 = all pass, 1 = any fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = SCRIPT_DIR / "fixtures"
VALIDATE_SCRIPT = SCRIPT_DIR.parent / "skills" / "review-skill" / "scripts" / "validate.py"

# Each fixture maps to expected outcomes: {check_id: True/False}
# True = must pass, False = must fail, absent = don't care
EXPECTATIONS: dict[str, dict[str, bool]] = {
    "passing-skill": {
        "FM-name-present": True,
        "FM-name-format": True,
        "FM-desc-present": True,
        "FM-desc-length": True,
        "FM-tools-present": True,
        "CT-no-secrets": True,
        "CT-no-grading": True,
        "CT-long-prose": True,
    },
    "failing-read-gate": {
        "FM-name-present": True,
        "FM-desc-present": True,
        "RG-gate-present": False,
        "RG-passive": False,
    },
    "overdeclared-tools": {
        "FM-name-present": True,
        "CF-tools-usage": False,
    },
    "long-description": {
        "FM-desc-length": False,
        "FM-desc-present": True,
    },
}


def run_validate(fixture_dir: Path) -> dict[str, bool]:
    """Run validate.py and return {check_id: passed} map."""
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(fixture_dir)],
        capture_output=True,
        text=True,
    )
    checks: dict[str, bool] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            if record.get("kind") == "check":
                check_id = record["check"]
                passed = record["pass"]
                checks[check_id] = passed
        except (json.JSONDecodeError, KeyError):
            continue
    return checks


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    total_assertions = 0
    total_failures = 0

    for fixture_name, expectations in sorted(EXPECTATIONS.items()):
        fixture_dir = FIXTURES_DIR / fixture_name
        if not fixture_dir.is_dir():
            print(f"SKIP {fixture_name}: directory not found")
            continue

        actual = run_validate(fixture_dir)
        fixture_failures = 0

        for check_id, expected_pass in expectations.items():
            total_assertions += 1
            actual_pass = actual.get(check_id)

            if actual_pass is None:
                print(f"  FAIL {fixture_name}/{check_id}: check not emitted")
                fixture_failures += 1
            elif actual_pass != expected_pass:
                expected_str = "pass" if expected_pass else "fail"
                actual_str = "pass" if actual_pass else "fail"
                print(
                    f"  FAIL {fixture_name}/{check_id}: "
                    f"expected {expected_str}, got {actual_str}"
                )
                fixture_failures += 1
            elif verbose:
                status = "pass" if actual_pass else "fail"
                print(f"  OK   {fixture_name}/{check_id}: {status}")

        if fixture_failures == 0:
            print(f"OK   {fixture_name} ({len(expectations)} assertions)")
        else:
            total_failures += fixture_failures

    print(f"\n{total_assertions} assertions, {total_failures} failures")

    # Also run self-test (validate against review-skill itself)
    review_skill_dir = SCRIPT_DIR.parent / "skills" / "review-skill"
    self_checks = run_validate(review_skill_dir)
    self_fails = [c for c, p in self_checks.items() if not p]
    if self_fails:
        print(f"FAIL self-test: {len(self_fails)} check(s) failed: {self_fails}")
        total_failures += len(self_fails)
    else:
        print(f"OK   self-test ({len(self_checks)} checks, all pass)")

    return 1 if total_failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
