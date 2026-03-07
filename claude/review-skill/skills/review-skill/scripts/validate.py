#!/usr/bin/env python3
"""Validate SKILL.md frontmatter fields and directory structure.

Usage:
    ./validate.py <skill-directory> [mode]

Modes:
    all          - Run all checks (default)
    frontmatter  - Frontmatter field checks only
    structure    - Directory structure checks only

Output: One JSON object per line:
    {"check": "<id>", "pass": true|false, "detail": "<message>"}

Final line is always a summary:
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes:
    0 - all checks pass
    1 - one or more checks fail
    2 - usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Ensure we don't write .pyc files into plugin cache
# ---------------------------------------------------------------------------

# Both are needed: the env var prevents child processes (subprocess) from
# writing .pyc files, while the attribute prevents the current interpreter.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

from skill_check_common import (  # noqa: E402
    EXIT_USAGE_ERROR,
    CheckResult,
    ResultCollector,
    SkillDocument,
    SkillLoadError,
    emit_record,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NAME_MAX_LENGTH: Final[int] = 64
NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]+$")
DESCRIPTION_MAX_LENGTH: Final[int] = 1024
TRIGGER_PHRASE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(when|use|for)\b",
    re.IGNORECASE,
)
NON_THIRD_PERSON_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(I can|You can)\b",
    re.IGNORECASE,
)

VALID_MODES: Final[tuple[str, ...]] = ("all", "frontmatter", "structure")
LINT_TOP_FINDINGS_LIMIT: Final[int] = 3
DELEGATE_TIMEOUT_SECONDS: Final[int] = 30
EXPECTED_EXIT_CODES: Final[frozenset[int]] = frozenset({0, 1})
ERROR_SNIPPET_LENGTH: Final[int] = 200

# Check IDs for non-delegated checks
CHECK_SCRIPT_LINT: Final[str] = "script-lint"
CHECK_FORK_INFO: Final[str] = "fork-candidate-info"
CHECK_SKILL_EXISTS: Final[str] = "skill-md-exists"

# Frontmatter field names
FIELD_NAME: Final[str] = "name"
FIELD_DESCRIPTION: Final[str] = "description"
FIELD_ALLOWED_TOOLS: Final[str] = "allowed-tools"
FIELD_USER_INVOCABLE: Final[str] = "user-invocable"
FIELD_DMI: Final[str] = "disable-model-invocation"


# ---------------------------------------------------------------------------
# Frontmatter checks
# ---------------------------------------------------------------------------


def _check_name(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run name-present, name-format, name-matches-dir checks."""
    name = doc.field(FIELD_NAME)
    dir_name = doc.skill_dir.name

    # B1: distinguish missing vs empty
    if not doc.has_field(FIELD_NAME):
        detail = "Field 'name' is missing from frontmatter"
    elif not name:
        detail = "Field 'name' is present but empty"
    else:
        detail = ""

    if not name:
        collector.add(
            CheckResult(check="name-present", passed=False, detail=detail),
        )
        collector.add(
            CheckResult(
                check="name-format",
                passed=False,
                detail=f"Cannot validate format: {detail.lower()}",
            ),
        )
        collector.add(
            CheckResult(
                check="name-matches-dir",
                passed=False,
                detail=(
                    "Cannot compare name to directory: "
                    f"{detail.lower()}"
                ),
            ),
        )
        return

    collector.add(
        CheckResult(
            check="name-present",
            passed=True,
            detail="Field 'name' is present",
        ),
    )

    # B4: collect all format errors instead of elif chain
    errors: list[str] = []
    if len(name) > NAME_MAX_LENGTH:
        errors.append(
            f"exceeds {NAME_MAX_LENGTH} characters ({len(name)})",
        )
    if not NAME_RE.match(name):
        errors.append("contains invalid characters (only lowercase, numbers, hyphens)")
    else:
        if name.startswith("-") or name.endswith("-"):
            errors.append("must not start or end with a hyphen")
        if "--" in name:
            errors.append("contains consecutive hyphens")

    if errors:
        collector.add(
            CheckResult(
                check="name-format",
                passed=False,
                detail=f"Name '{name}': {'; '.join(errors)}",
            ),
        )
    else:
        collector.add(
            CheckResult(
                check="name-format",
                passed=True,
                detail=(
                    f"Name '{name}' matches pattern "
                    f"[a-z0-9-]{{1,{NAME_MAX_LENGTH}}}"
                ),
            ),
        )

    # matches directory
    if name == dir_name:
        collector.add(
            CheckResult(
                check="name-matches-dir",
                passed=True,
                detail=f"Name '{name}' matches directory '{dir_name}'",
            ),
        )
    else:
        collector.add(
            CheckResult(
                check="name-matches-dir",
                passed=False,
                detail=(
                    f"Name '{name}' does not match directory "
                    f"'{dir_name}'"
                ),
            ),
        )


def _check_description(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run description-present, description-length, trigger-phrases, third-person."""
    description = doc.field(FIELD_DESCRIPTION)

    # B1: distinguish missing vs empty
    if not doc.has_field(FIELD_DESCRIPTION):
        missing_detail = "Field 'description' is missing from frontmatter"
    elif not description:
        missing_detail = "Field 'description' is present but empty"
    else:
        missing_detail = ""

    if not description:
        collector.add(
            CheckResult(
                check="description-present",
                passed=False,
                detail=missing_detail,
            ),
        )
        collector.add(
            CheckResult(
                check="description-length",
                passed=False,
                detail=f"Cannot validate length: {missing_detail.lower()}",
            ),
        )
        collector.add(
            CheckResult(
                check="description-trigger-phrases",
                passed=False,
                detail=(
                    "Cannot validate trigger phrases: "
                    f"{missing_detail.lower()}"
                ),
            ),
        )
        collector.add(
            CheckResult(
                check="description-third-person",
                passed=False,
                detail=(
                    "Cannot validate voice: "
                    f"{missing_detail.lower()}"
                ),
            ),
        )
        return

    collector.add(
        CheckResult(
            check="description-present",
            passed=True,
            detail="Field 'description' is present",
        )
    )

    # length
    if len(description) > DESCRIPTION_MAX_LENGTH:
        collector.add(
            CheckResult(
                check="description-length",
                passed=False,
                detail=(
                    f"Description is {len(description)} chars, "
                    f"exceeds {DESCRIPTION_MAX_LENGTH}-char limit"
                ),
            )
        )
    else:
        collector.add(
            CheckResult(
                check="description-length",
                passed=True,
                detail=(
                    f"Description is {len(description)} chars "
                    f"(limit {DESCRIPTION_MAX_LENGTH})"
                ),
            )
        )

    # trigger phrases (skip if DMI)
    dmi = doc.field(FIELD_DMI).strip().lower()
    if dmi == "true":
        collector.add(
            CheckResult(
                check="description-trigger-phrases",
                passed=True,
                detail="Trigger phrases not required (disable-model-invocation: true)",
            )
        )
    elif TRIGGER_PHRASE_RE.search(description):
        collector.add(
            CheckResult(
                check="description-trigger-phrases",
                passed=True,
                detail="Description includes trigger phrase (when/use/for)",
            )
        )
    else:
        collector.add(
            CheckResult(
                check="description-trigger-phrases",
                passed=False,
                detail=(
                    "Description should include a trigger phrase "
                    "(when/use/for) for discoverability"
                ),
            )
        )

    # third-person voice
    if NON_THIRD_PERSON_RE.search(description):
        collector.add(
            CheckResult(
                check="description-third-person",
                passed=False,
                detail=(
                    "Description should use third-person form, not 'I can' or 'You can'"
                ),
            )
        )
    else:
        collector.add(
            CheckResult(
                check="description-third-person",
                passed=True,
                detail="Description uses appropriate voice",
            )
        )


def _check_allowed_tools(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run allowed-tools-present check."""
    allowed_tools = doc.field(FIELD_ALLOWED_TOOLS)
    if not doc.has_field(FIELD_ALLOWED_TOOLS):
        detail = "Field 'allowed-tools' is missing from frontmatter"
    elif not allowed_tools:
        detail = "Field 'allowed-tools' is present but empty"
    else:
        detail = ""

    if not allowed_tools:
        collector.add(
            CheckResult(
                check="allowed-tools-present",
                passed=False,
                detail=detail,
            ),
        )
    else:
        collector.add(
            CheckResult(
                check="allowed-tools-present",
                passed=True,
                detail=f"Field 'allowed-tools' is present: {allowed_tools}",
            ),
        )


def _check_user_invocable(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run user-invocable-present check."""
    user_invocable = doc.field(FIELD_USER_INVOCABLE).strip().lower()
    if not doc.has_field(FIELD_USER_INVOCABLE):
        collector.add(
            CheckResult(
                check="user-invocable-present",
                passed=False,
                detail="Field 'user-invocable' is missing from frontmatter",
            ),
        )
    elif not user_invocable:
        collector.add(
            CheckResult(
                check="user-invocable-present",
                passed=False,
                detail="Field 'user-invocable' is present but empty",
            ),
        )
    elif user_invocable in {"true", "false"}:
        collector.add(
            CheckResult(
                check="user-invocable-present",
                passed=True,
                detail=f"Field 'user-invocable' is '{user_invocable}'",
            ),
        )
    else:
        collector.add(
            CheckResult(
                check="user-invocable-present",
                passed=False,
                detail=(
                    "Field 'user-invocable' must be boolean "
                    f"(true/false), got '{user_invocable}'"
                ),
            ),
        )


def run_frontmatter(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run all frontmatter checks."""
    _check_name(doc, collector)
    _check_description(doc, collector)
    _check_allowed_tools(doc, collector)
    _check_user_invocable(doc, collector)


# ---------------------------------------------------------------------------
# Delegation infrastructure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DelegateConfig:
    """Configuration for one delegated companion script."""

    script: str
    args: tuple[str, ...] = ()
    guard_field: str = ""
    required: bool = True


@dataclass(frozen=True)
class ScriptRunResult:
    """Store subprocess execution state for one script invocation."""

    ok: bool
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


@dataclass(frozen=True)
class ParsedDelegateOutput:
    """Store parsed NDJSON output for standard delegate scripts."""

    checks: tuple[CheckResult, ...]
    summary: dict[str, object] | None
    invalid_lines: tuple[str, ...]


@dataclass(frozen=True)
class ParsedLintOutput:
    """Store parsed NDJSON output from lint-scripts.py."""

    findings: tuple[dict[str, object], ...]
    summary: dict[str, object] | None
    invalid_lines: tuple[str, ...]


def _parse_ndjson_line(line: str) -> dict[str, object] | None:
    """Parse one NDJSON line, returning None on failure."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _summary_int(summary: dict[str, object], field: str) -> int | None:
    """Return integer summary field value, or None if invalid."""
    raw_value = summary.get(field)
    # bool check first because isinstance(True, int) is True in Python
    if isinstance(raw_value, bool) or raw_value is None:
        return None
    if isinstance(raw_value, int):
        return raw_value
    return None


def _snippet(text: str, *, width: int = ERROR_SNIPPET_LENGTH) -> str:
    """Return one-line excerpt for error details."""
    stripped = text.strip()
    if not stripped:
        return ""
    first_line = stripped.splitlines()[0]
    return first_line[:width]


def _runtime_check_id(script: str) -> str:
    """Build stable check id for delegated runtime errors."""
    return f"delegate-{Path(script).stem}-runtime"


def _run_script(
    script_path: Path,
    args: tuple[str, ...],
) -> ScriptRunResult:
    """Run script and return structured execution result."""
    if not script_path.is_file():
        return ScriptRunResult(
            ok=False,
            error=f"Script not found: {script_path.name}",
        )

    # Technically racy (TOCTOU), but worth keeping for the clearer error
    # message compared to a generic OSError from subprocess.
    if not os.access(script_path, os.X_OK):
        return ScriptRunResult(
            ok=False,
            error=f"Script is not executable: {script_path.name}",
        )

    cmd = [str(script_path), *args]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=DELEGATE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ScriptRunResult(
            ok=False,
            error=(
                f"Script timed out after {DELEGATE_TIMEOUT_SECONDS}s: "
                f"{script_path.name}"
            ),
        )
    except OSError as error:
        return ScriptRunResult(
            ok=False,
            error=f"Failed to execute {script_path.name}: {error}",
        )

    return ScriptRunResult(
        ok=True,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _run_and_validate_script(
    script_path: Path,
    args: tuple[str, ...],
    *,
    forward_stderr: bool = True,
) -> tuple[ScriptRunResult | None, str | None]:
    """Run a script and validate basic execution contract.

    Returns (result, None) on success or (None, error_message) on failure.
    Checks: script ran OK, returncode exists, returncode in expected set,
    stdout is non-empty. Optionally forwards stderr to sys.stderr.
    """
    run_result = _run_script(script_path, args)
    if not run_result.ok:
        return None, run_result.error

    return_code = run_result.returncode
    if return_code is None:
        return None, f"No return code from {script_path.name}"

    if return_code not in EXPECTED_EXIT_CODES:
        detail = f"Unexpected exit code {return_code} from {script_path.name}"
        stderr_excerpt = _snippet(run_result.stderr)
        if stderr_excerpt:
            detail += f" - stderr: {stderr_excerpt}"
        return None, detail

    if not run_result.stdout.strip():
        return None, f"No stdout from {script_path.name}"

    if forward_stderr and run_result.stderr.strip():
        sys.stderr.write(run_result.stderr)

    return run_result, None


def _parse_delegate_output(output: str) -> ParsedDelegateOutput:
    """Parse standard delegate NDJSON (check lines + final summary)."""
    checks: list[CheckResult] = []
    invalid_lines: list[str] = []
    summary: dict[str, object] | None = None

    for line in output.splitlines():
        if not line.strip():
            continue

        obj = _parse_ndjson_line(line)
        if obj is None:
            invalid_lines.append(_snippet(line))
            continue

        if obj.get("summary") is True:
            if summary is None:
                summary = obj
            else:
                invalid_lines.append(_snippet(line))
            continue

        check = obj.get("check")
        passed = obj.get("pass")
        if not isinstance(check, str) or not isinstance(passed, bool):
            invalid_lines.append(_snippet(line))
            continue

        checks.append(
            CheckResult(
                check=check,
                passed=passed,
                detail=str(obj.get("detail", "")),
            )
        )

    return ParsedDelegateOutput(
        checks=tuple(checks),
        summary=summary,
        invalid_lines=tuple(invalid_lines),
    )


def _parse_lint_output(output: str) -> ParsedLintOutput:
    """Parse lint-scripts NDJSON (finding lines + final summary).

    Shares structure with _parse_delegate_output but uses different record
    schema (findings with severity vs check results with pass/fail).
    """
    findings: list[dict[str, object]] = []
    invalid_lines: list[str] = []
    summary: dict[str, object] | None = None

    for line in output.splitlines():
        if not line.strip():
            continue

        obj = _parse_ndjson_line(line)
        if obj is None:
            invalid_lines.append(_snippet(line))
            continue

        if obj.get("summary") is True:
            if summary is None:
                summary = obj
            else:
                invalid_lines.append(_snippet(line))
            continue

        check_id = obj.get("check")
        message = obj.get("message")
        severity = obj.get("severity")
        if (
            not isinstance(check_id, str)
            or not isinstance(message, str)
            or not isinstance(severity, str)
        ):
            invalid_lines.append(_snippet(line))
            continue
        # B5: reject empty-string fields upfront
        if not check_id or not message or not severity:
            invalid_lines.append(_snippet(line))
            continue

        findings.append(obj)

    return ParsedLintOutput(
        findings=tuple(findings),
        summary=summary,
        invalid_lines=tuple(invalid_lines),
    )


def _collect_delegate_output(
    script_path: Path,
    skill_dir: Path,
    extra_args: tuple[str, ...] = (),
) -> tuple[ParsedDelegateOutput | None, str | None]:
    """Run and validate one standard delegate output contract."""
    run_result, error = _run_and_validate_script(
        script_path, (str(skill_dir), *extra_args),
    )
    if error:
        return None, error
    if run_result is None:
        return None, f"No result from {script_path.name}"

    parsed = _parse_delegate_output(run_result.stdout)
    if parsed.invalid_lines:
        return (
            None,
            (f"Invalid NDJSON from {script_path.name}: {parsed.invalid_lines[0]}"),
        )

    if parsed.summary is None:
        return None, f"Missing summary line from {script_path.name}"

    total = _summary_int(parsed.summary, "total")
    if total is None:
        return None, f"Summary missing integer 'total' in {script_path.name}"
    if total != len(parsed.checks):
        return (
            None,
            (
                f"Summary total mismatch in {script_path.name}: "
                f"summary={total}, checks={len(parsed.checks)}"
            ),
        )

    # B2: verify passed + failed == total
    passed = _summary_int(parsed.summary, "passed")
    failed = _summary_int(parsed.summary, "failed")
    if (
        passed is not None
        and failed is not None
        and passed + failed != total
    ):
        return (
            None,
            (
                f"Summary passed+failed mismatch in "
                f"{script_path.name}: "
                f"{passed}+{failed} != {total}"
            ),
        )

    return parsed, None


def _emit_delegate_runtime_error(
    collector: ResultCollector,
    script: str,
    detail: str,
    *,
    check: str | None = None,
) -> None:
    """Emit one failed runtime check record for delegated execution."""
    collector.add(
        CheckResult(
            check=check or _runtime_check_id(script),
            passed=False,
            detail=detail,
        )
    )


def _emit_delegate_checks(
    parsed: ParsedDelegateOutput,
    collector: ResultCollector,
    *,
    script: str,
    guard_field: str = "",
) -> None:
    """Emit parsed checks, optionally guarded by integer summary field."""
    if guard_field:
        summary = parsed.summary
        if summary is None:
            _emit_delegate_runtime_error(
                collector,
                script,
                f"Missing summary line from {script}",
            )
            return

        guard_value = _summary_int(summary, guard_field)
        if guard_value is None:
            _emit_delegate_runtime_error(
                collector,
                script,
                f"Summary field '{guard_field}' is not an integer in {script}",
            )
            return
        if guard_value <= 0:
            return

    for result in parsed.checks:
        collector.add(result)


# ---------------------------------------------------------------------------
# Structure delegation table
# ---------------------------------------------------------------------------


# Ordered identically to the bash orchestrator
def _delegate(
    script: str,
    args: tuple[str, ...] = (),
    *,
    guard_field: str = "",
    required: bool = True,
) -> DelegateConfig:
    """Build a DelegateConfig with compact syntax."""
    return DelegateConfig(script, args, guard_field, required)


def _delegate_checks(
    script: str, *checks: str, required: bool = True,
) -> DelegateConfig:
    """Build a DelegateConfig with --check args."""
    args: list[str] = []
    for check in checks:
        args.extend(("--check", check))
    return DelegateConfig(script, tuple(args), required=required)


# Ordered identically to the bash orchestrator
STRUCTURE_DELEGATIONS: Final[tuple[DelegateConfig, ...]] = (
    _delegate_checks(
        "check-references.py",
        "body-line-count", "body-char-count",
        "duplicate-codeblocks-info", "consistent-phase-numbering",
        "long-ref-toc",
    ),
    _delegate_checks(
        "check-file-refs.py",
        "file-ref-resolves", "no-backslash-paths",
        "no-disallowed-files", "refs-one-level",
        "skill-md-mentions-file", "ref-link-format",
    ),
    _delegate("check-scripts-dir.py"),
    _delegate_checks(
        "check-content.py",
        "no-secrets", "no-useless-echo", "no-grading-style",
    ),
    _delegate_checks(
        "check-config.py",
        "persistent-state-xdg", "allowed-tools-usage",
        "side-effect-guard",
    ),
    _delegate("check-read-gates.py", guard_field="refs"),
    _delegate("check-preprocessing.py", guard_field="directives"),
)

# ---------------------------------------------------------------------------
# Special-case handlers
# ---------------------------------------------------------------------------


def _run_structure_delegate(
    config: DelegateConfig,
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run one standard structure delegate and emit its check results."""
    script_path = script_dir / config.script
    parsed, error = _collect_delegate_output(
        script_path,
        skill_dir,
        config.args,
    )
    if error:
        if config.required:
            _emit_delegate_runtime_error(collector, config.script, error)
        return

    if parsed is None:
        if config.required:
            _emit_delegate_runtime_error(
                collector,
                config.script,
                f"No parsed output from {config.script}",
            )
        return

    _emit_delegate_checks(
        parsed,
        collector,
        script=config.script,
        guard_field=config.guard_field,
    )


def _aggregate_lint_findings(findings: tuple[dict[str, object], ...]) -> str:
    """Build compact lint summary detail from parsed finding records."""
    crits = 0
    meds = 0
    top_findings: list[str] = []
    for obj in findings:
        severity = obj.get("severity", "")
        if severity == "critical":
            crits += 1
        elif severity == "medium":
            meds += 1

        if len(top_findings) < LINT_TOP_FINDINGS_LIMIT:
            # Parser already validates check_id and message are non-empty strings
            top_findings.append(f"{obj['check']}: {obj['message']}")

    detail = f"scripts/ has {crits} critical, {meds} medium finding(s)"
    if top_findings:
        detail += " - " + "; ".join(top_findings)
    return detail


def _handle_lint_scripts(
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run lint-scripts.py and aggregate into a single script-lint result."""
    scripts_dir = skill_dir / "scripts"

    if not scripts_dir.is_dir():
        collector.add(
            CheckResult(
                check=CHECK_SCRIPT_LINT,
                passed=True,
                detail="No scripts/ directory",
            )
        )
        return

    lint_script = script_dir / "lint-scripts.py"
    run_result, error = _run_and_validate_script(
        lint_script,
        (str(scripts_dir), "--json", "--severity", "medium"),
    )
    if error:
        _emit_delegate_runtime_error(
            collector, lint_script.name, error, check=CHECK_SCRIPT_LINT,
        )
        return
    if run_result is None:
        _emit_delegate_runtime_error(
            collector, lint_script.name,
            "No result from lint-scripts.py", check=CHECK_SCRIPT_LINT,
        )
        return

    parsed = _parse_lint_output(run_result.stdout)
    if parsed.invalid_lines:
        _emit_delegate_runtime_error(
            collector, lint_script.name,
            f"Invalid NDJSON from lint-scripts.py: {parsed.invalid_lines[0]}",
            check=CHECK_SCRIPT_LINT,
        )
        return

    summary = parsed.summary
    if summary is None:
        _emit_delegate_runtime_error(
            collector, lint_script.name,
            "Missing summary line from lint-scripts.py",
            check=CHECK_SCRIPT_LINT,
        )
        return

    lint_total = _summary_int(summary, "findings")
    if lint_total is None:
        _emit_delegate_runtime_error(
            collector, lint_script.name,
            "Summary missing integer 'findings' in lint-scripts.py",
            check=CHECK_SCRIPT_LINT,
        )
        return

    if lint_total != len(parsed.findings):
        _emit_delegate_runtime_error(
            collector, lint_script.name,
            (
                "Summary findings mismatch in lint-scripts.py: "
                f"summary={lint_total}, parsed={len(parsed.findings)}"
            ),
            check=CHECK_SCRIPT_LINT,
        )
        return

    if lint_total == 0:
        collector.add(
            CheckResult(
                check=CHECK_SCRIPT_LINT,
                passed=True,
                detail="No critical/medium findings in scripts/",
            )
        )
        return

    collector.add(
        CheckResult(
            check=CHECK_SCRIPT_LINT,
            passed=False,
            detail=_aggregate_lint_findings(parsed.findings),
        )
    )



def _parse_fork_candidate_summary(
    output: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Parse check-fork-candidate NDJSON and return summary object."""
    objects: list[dict[str, object]] = []
    invalid_lines: list[str] = []

    for line in output.splitlines():
        if not line.strip():
            continue
        obj = _parse_ndjson_line(line)
        if obj is None:
            invalid_lines.append(_snippet(line))
            continue
        objects.append(obj)

    if invalid_lines:
        return None, f"Invalid NDJSON from check-fork-candidate.py: {invalid_lines[0]}"
    if not objects:
        return None, "No NDJSON records from check-fork-candidate.py"

    # B6: search for the recommendation record instead of assuming last line
    summary_obj = None
    for obj in objects:
        if "recommendation" in obj:
            summary_obj = obj
            break
    if summary_obj is None:
        return None, "No record with 'recommendation' field"
    return summary_obj, None


def _handle_fork_candidate(
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run check-fork-candidate.py and emit single fork-candidate-info result."""
    fork_script = script_dir / "check-fork-candidate.py"
    run_result, error = _run_and_validate_script(
        fork_script, (str(skill_dir),),
    )
    if error:
        _emit_delegate_runtime_error(
            collector, fork_script.name, error, check=CHECK_FORK_INFO,
        )
        return
    if run_result is None:
        _emit_delegate_runtime_error(
            collector, fork_script.name,
            "No result from check-fork-candidate.py", check=CHECK_FORK_INFO,
        )
        return

    return_code = run_result.returncode
    summary_obj, error = _parse_fork_candidate_summary(run_result.stdout)
    if error:
        _emit_delegate_runtime_error(
            collector,
            fork_script.name,
            error,
            check=CHECK_FORK_INFO,
        )
        return

    if summary_obj is None:
        _emit_delegate_runtime_error(
            collector,
            fork_script.name,
            "Missing summary from check-fork-candidate.py",
            check=CHECK_FORK_INFO,
        )
        return

    recommendation = summary_obj.get("recommendation")
    if not isinstance(recommendation, str):
        _emit_delegate_runtime_error(
            collector,
            fork_script.name,
            "Field 'recommendation' is missing or not a string",
            check=CHECK_FORK_INFO,
        )
        return

    detail = str(summary_obj.get("detail", "")).strip()
    if not detail:
        detail = "No detail returned by check-fork-candidate.py"

    if recommendation in {"strong", "soft"}:
        if return_code != 0:
            _emit_delegate_runtime_error(
                collector,
                fork_script.name,
                (
                    "Recommendation is strong/soft but exit code is "
                    f"{return_code} (expected 0)"
                ),
                check=CHECK_FORK_INFO,
            )
            return
        collector.add(
            CheckResult(
                check=CHECK_FORK_INFO,
                passed=True,
                detail=f"INFO: {detail}",
            )
        )
        return

    if recommendation == "none":
        if return_code != 1:
            _emit_delegate_runtime_error(
                collector,
                fork_script.name,
                (f"Recommendation is none but exit code is {return_code} (expected 1)"),
                check=CHECK_FORK_INFO,
            )
            return
        collector.add(
            CheckResult(
                check=CHECK_FORK_INFO,
                passed=True,
                detail=f"No fork recommendation - {detail}",
            )
        )
        return

    _emit_delegate_runtime_error(
        collector,
        fork_script.name,
        f"Unknown recommendation value: '{recommendation}'",
        check=CHECK_FORK_INFO,
    )


# ---------------------------------------------------------------------------
# Structure checks
# ---------------------------------------------------------------------------


def run_structure(
    doc: SkillDocument,
    script_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run all structure checks via delegation."""
    # Standard delegations
    for config in STRUCTURE_DELEGATIONS:
        _run_structure_delegate(config, script_dir, doc.skill_dir, collector)

    # Special cases
    _handle_lint_scripts(script_dir, doc.skill_dir, collector)
    _run_structure_delegate(
        _delegate("check-ask-user.py", guard_field="total"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Flag coverage (I22)
    _run_structure_delegate(
        _delegate("check-flag-coverage.py"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Hooks validation (I23)
    _run_structure_delegate(
        _delegate("check-hooks.py"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Fork candidate (P9, informational)
    _handle_fork_candidate(script_dir, doc.skill_dir, collector)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md frontmatter fields and directory structure.",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=VALID_MODES,
        help="Which checks to run (default: all)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    parser = _build_parser()
    # B3: catch argparse's SystemExit so we emit valid NDJSON
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        collector = ResultCollector()
        collector.add(
            CheckResult(
                check=CHECK_SKILL_EXISTS,
                passed=False,
                detail=(
                    "Invalid arguments "
                    "(usage: validate.py <skill-dir> [mode])"
                ),
            ),
        )
        collector.emit_summary()
        return EXIT_USAGE_ERROR

    script_dir = Path(__file__).resolve().parent

    try:
        doc = load_skill_document(args.skill_directory)
    except SkillLoadError as error:
        collector = ResultCollector()
        collector.add(
            CheckResult(
                check=CHECK_SKILL_EXISTS,
                passed=False,
                detail=str(error),
            )
        )
        collector.emit_summary()
        return EXIT_USAGE_ERROR

    collector = ResultCollector()

    if args.mode in {"all", "frontmatter"}:
        run_frontmatter(doc, collector)
    if args.mode in {"all", "structure"}:
        run_structure(doc, script_dir, collector)

    collector.emit_summary()
    return 1 if collector.failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
