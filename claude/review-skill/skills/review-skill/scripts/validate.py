#!/usr/bin/env python3
"""Validate SKILL.md frontmatter fields and directory structure.

Usage:
    ./validate.py <skill-directory> [mode]

Modes:
    all          - Run all checks (default)
    frontmatter  - Frontmatter field checks only
    structure    - Directory structure checks only

Output: One JSON object per line (NDJSON):
    {"kind":"check","check":"<id>","pass":bool,"level":"<lvl>","detail":"<msg>"}

Final line is always a summary:
    {"kind": "summary", "total": N, "passed": N, "failed": N}

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
from typing import Final, cast

# ---------------------------------------------------------------------------
# Ensure we don't write .pyc files into plugin cache
# ---------------------------------------------------------------------------

# Both are needed: the env var prevents child processes (subprocess) from
# writing .pyc files, while the attribute prevents the current interpreter.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

from _skill_check_common import (  # noqa: E402
    EXIT_USAGE_ERROR,
    CheckRecord,
    ResultCollector,
    ResultLevel,
    SkillDocument,
    SkillLoadError,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NAME_MAX_LENGTH: Final[int] = 64
NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]+$")
DESCRIPTION_MAX_LENGTH: Final[int] = 1024
COMPATIBILITY_MAX_LENGTH: Final[int] = 500
TRIGGER_PHRASE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(when|use|for)\b",
    re.IGNORECASE,
)
NON_THIRD_PERSON_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(I can|You can)\b",
    re.IGNORECASE,
)
NAME_RESERVED_WORDS: Final[tuple[str, ...]] = ("anthropic", "claude")
XML_TAG_RE: Final[re.Pattern[str]] = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*)?>")

VALID_MODES: Final[tuple[str, ...]] = ("all", "frontmatter", "structure")
LINT_TOP_FINDINGS_LIMIT: Final[int] = 3
# 30s is generous for any single checker script; avoids blocking on hangs
DELEGATE_TIMEOUT_SECONDS: Final[int] = 30
EXPECTED_EXIT_CODES: Final[frozenset[int]] = frozenset({0, 1})
ERROR_SNIPPET_LENGTH: Final[int] = 200

# Check IDs for non-delegated checks
CHECK_SCRIPT_LINT: Final[str] = "CL-aggregate"
CHECK_FORK_INFO: Final[str] = "FK-recommendation-info"
CHECK_SKILL_EXISTS: Final[str] = "FM-skill-md-exists"

# Script prefix mapping for runtime error IDs
SCRIPT_PREFIX: Final[dict[str, str]] = {
    "check-best-practices.py": "BP",
    "check-config.py": "CF",
    "check-content.py": "CT",
    "check-security.py": "SC",
    "check-file-refs.py": "FR",
    "check-scripts-dir.py": "SD",
    "check-references.py": "RF",
    "check-read-gates.py": "RG",
    "check-preprocessing.py": "PP",
    "check-ask-user.py": "AQ",
    "check-flag-coverage.py": "FC",
    "check-hooks.py": "HK",
    "check-fork-candidate.py": "FK",
    "check-lint.py": "CL",
}

# Frontmatter field names
FIELD_NAME: Final[str] = "name"
FIELD_DESCRIPTION: Final[str] = "description"
FIELD_ALLOWED_TOOLS: Final[str] = "allowed-tools"
FIELD_USER_INVOCABLE: Final[str] = "user-invocable"
FIELD_DMI: Final[str] = "disable-model-invocation"
FIELD_COMPATIBILITY: Final[str] = "compatibility"


# ---------------------------------------------------------------------------
# Frontmatter checks
# ---------------------------------------------------------------------------


def _check_name_reserved(name: str, collector: ResultCollector) -> None:
    """Check whether name contains reserved words (anthropic, claude)."""
    segments = name.split("-")
    reserved_hits = [w for w in NAME_RESERVED_WORDS if w in segments]
    if reserved_hits:
        collector.add(
            CheckRecord(
                check="FM-name-reserved",
                passed=False,
                detail=(
                    f"Name '{name}' contains reserved word(s): "
                    f"{', '.join(reserved_hits)}"
                ),
                tier="C4",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-name-reserved",
                passed=True,
                detail=f"Name '{name}' contains no reserved words",
                tier="C4",
            ),
        )


def _check_name(doc: SkillDocument, collector: ResultCollector) -> None:  # noqa: PLR0912
    """Run name-present, name-format, name-matches-dir, name-reserved checks."""
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
            CheckRecord(
                check="FM-name-present",
                passed=False,
                detail=detail,
                tier="C4",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-name-format",
                passed=False,
                detail=f"Cannot validate format: {detail.lower()}",
                tier="C4",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-name-matches-dir",
                passed=False,
                detail=f"Cannot compare name to directory: {detail.lower()}",
                tier="C4",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-name-reserved",
                passed=False,
                detail=f"Cannot validate reserved words: {detail.lower()}",
                tier="C4",
            ),
        )
        return

    collector.add(
        CheckRecord(
            check="FM-name-present",
            passed=True,
            detail="Field 'name' is present",
            tier="C4",
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
            CheckRecord(
                check="FM-name-format",
                passed=False,
                detail=f"Name '{name}': {'; '.join(errors)}",
                tier="C4",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-name-format",
                passed=True,
                detail=(
                    f"Name '{name}' matches pattern [a-z0-9-]{{1,{NAME_MAX_LENGTH}}}"
                ),
                tier="C4",
            ),
        )

    # matches directory
    if name == dir_name:
        collector.add(
            CheckRecord(
                check="FM-name-matches-dir",
                passed=True,
                detail=f"Name '{name}' matches directory '{dir_name}'",
                tier="C4",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-name-matches-dir",
                passed=False,
                detail=f"Name '{name}' does not match directory '{dir_name}'",
                tier="C4",
            ),
        )

    _check_name_reserved(name, collector)


def _check_desc_xml(description: str, collector: ResultCollector) -> None:
    """Check whether description contains XML tags."""
    xml_match = XML_TAG_RE.search(description)
    if xml_match:
        collector.add(
            CheckRecord(
                check="FM-desc-no-xml",
                passed=False,
                detail=(f"Description contains XML tag: {xml_match.group(0)}"),
                tier="C1",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-desc-no-xml",
                passed=True,
                detail="Description contains no XML tags",
                tier="C1",
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
            CheckRecord(
                check="FM-desc-present",
                passed=False,
                detail=missing_detail,
                tier="C1",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-desc-length",
                passed=False,
                detail=f"Cannot validate length: {missing_detail.lower()}",
                tier="I25",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-desc-trigger",
                passed=False,
                detail=f"Cannot validate trigger phrases: {missing_detail.lower()}",
                tier="C1",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-desc-voice",
                passed=False,
                detail=f"Cannot validate voice: {missing_detail.lower()}",
                tier="P5",
            ),
        )
        collector.add(
            CheckRecord(
                check="FM-desc-no-xml",
                passed=False,
                detail=f"Cannot validate XML tags: {missing_detail.lower()}",
                tier="C1",
            ),
        )
        return

    collector.add(
        CheckRecord(
            check="FM-desc-present",
            passed=True,
            detail="Field 'description' is present",
            tier="C1",
        ),
    )

    # length
    if len(description) > DESCRIPTION_MAX_LENGTH:
        collector.add(
            CheckRecord(
                check="FM-desc-length",
                passed=False,
                detail=(
                    f"Description is {len(description)} chars, "
                    f"exceeds {DESCRIPTION_MAX_LENGTH}-char limit"
                ),
                tier="I25",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-desc-length",
                passed=True,
                detail=(
                    f"Description is {len(description)} chars "
                    f"(limit {DESCRIPTION_MAX_LENGTH})"
                ),
                tier="I25",
            ),
        )

    # trigger phrases (skip if DMI)
    dmi = doc.field(FIELD_DMI).strip().lower()
    if dmi == "true":
        collector.add(
            CheckRecord(
                check="FM-desc-trigger",
                passed=True,
                detail="Trigger phrases not required (disable-model-invocation: true)",
                tier="C1",
            ),
        )
    elif TRIGGER_PHRASE_RE.search(description):
        collector.add(
            CheckRecord(
                check="FM-desc-trigger",
                passed=True,
                detail="Description includes trigger phrase (when/use/for)",
                tier="C1",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-desc-trigger",
                passed=False,
                detail=(
                    "Description should include a trigger phrase "
                    "(when/use/for) for discoverability"
                ),
                tier="C1",
            ),
        )

    # third-person voice
    if NON_THIRD_PERSON_RE.search(description):
        collector.add(
            CheckRecord(
                check="FM-desc-voice",
                passed=False,
                detail=(
                    "Description should use third-person form, not 'I can' or 'You can'"
                ),
                tier="P5",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-desc-voice",
                passed=True,
                detail="Description uses appropriate voice",
                tier="P5",
            ),
        )

    _check_desc_xml(description, collector)


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
            CheckRecord(
                check="FM-tools-present",
                passed=False,
                detail=detail,
                tier="I9",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-tools-present",
                passed=True,
                detail=f"Field 'allowed-tools' is present: {allowed_tools}",
                tier="I9",
            ),
        )


def _check_user_invocable(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run user-invocable-present check."""
    user_invocable = doc.field(FIELD_USER_INVOCABLE).strip().lower()
    if not doc.has_field(FIELD_USER_INVOCABLE):
        collector.add(
            CheckRecord(
                check="FM-invocable-present",
                passed=False,
                detail="Field 'user-invocable' is missing from frontmatter",
            ),
        )
    elif not user_invocable:
        collector.add(
            CheckRecord(
                check="FM-invocable-present",
                passed=False,
                detail="Field 'user-invocable' is present but empty",
            ),
        )
    elif user_invocable in {"true", "false"}:
        collector.add(
            CheckRecord(
                check="FM-invocable-present",
                passed=True,
                detail=f"Field 'user-invocable' is '{user_invocable}'",
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-invocable-present",
                passed=False,
                detail=(
                    "Field 'user-invocable' must be boolean "
                    f"(true/false), got '{user_invocable}'"
                ),
            ),
        )


def _check_compatibility(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run compatibility field length check (optional field)."""
    if not doc.has_field(FIELD_COMPATIBILITY):
        return
    compat = doc.field(FIELD_COMPATIBILITY)
    if len(compat) > COMPATIBILITY_MAX_LENGTH:
        collector.add(
            CheckRecord(
                check="FM-compat-length",
                passed=False,
                detail=(
                    f"Compatibility field is {len(compat)} chars, "
                    f"exceeds {COMPATIBILITY_MAX_LENGTH}-char limit"
                ),
            ),
        )
    else:
        collector.add(
            CheckRecord(
                check="FM-compat-length",
                passed=True,
                detail=(
                    f"Compatibility field is {len(compat)} chars "
                    f"(limit {COMPATIBILITY_MAX_LENGTH})"
                ),
            ),
        )


def run_frontmatter(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run all frontmatter checks."""
    _check_name(doc, collector)
    _check_description(doc, collector)
    _check_allowed_tools(doc, collector)
    _check_user_invocable(doc, collector)
    _check_compatibility(doc, collector)


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

    checks: tuple[CheckRecord, ...]
    summary: dict[str, object] | None
    invalid_lines: tuple[str, ...]


@dataclass(frozen=True)
class ParsedLintOutput:
    """Store parsed NDJSON output from check-lint.py."""

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
    stem = Path(script).name
    prefix = SCRIPT_PREFIX.get(stem, "XX")
    return f"{prefix}-runtime"


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
    checks: list[CheckRecord] = []
    invalid_lines: list[str] = []
    summary: dict[str, object] | None = None

    for line in output.splitlines():
        if not line.strip():
            continue

        obj = _parse_ndjson_line(line)
        if obj is None:
            invalid_lines.append(_snippet(line))
            continue

        kind = obj.get("kind")
        if kind == "summary" or obj.get("summary") is True:
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

        raw_level = obj.get("level", "pass" if passed else "fail")
        level: ResultLevel = (
            cast("ResultLevel", raw_level)
            if isinstance(raw_level, str)
            and raw_level in {"pass", "fail", "info", "skip"}
            else ("pass" if passed else "fail")
        )
        tier = obj.get("tier")
        detail = str(obj.get("detail", ""))
        item = obj.get("item")
        try:
            checks.append(
                CheckRecord(
                    check=check,
                    passed=passed,
                    detail=detail,
                    level=level,
                    tier=tier if isinstance(tier, str) else None,
                    item=item if isinstance(item, str) else None,
                ),
            )
        except ValueError:
            invalid_lines.append(_snippet(line))
            continue

    return ParsedDelegateOutput(
        checks=tuple(checks),
        summary=summary,
        invalid_lines=tuple(invalid_lines),
    )


def _parse_lint_output(output: str) -> ParsedLintOutput:
    """Parse check-lint NDJSON (finding lines + final summary).

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

        kind = obj.get("kind")
        if kind == "summary" or obj.get("summary") is True:
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


def _collect_delegate_output(  # noqa: PLR0911
    script_path: Path,
    skill_dir: Path,
    extra_args: tuple[str, ...] = (),
) -> tuple[ParsedDelegateOutput | None, str | None]:
    """Run and validate one standard delegate output contract."""
    run_result, error = _run_and_validate_script(
        script_path,
        (str(skill_dir), *extra_args),
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
    if passed is not None and failed is not None and passed + failed != total:
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
        CheckRecord(
            check=check or _runtime_check_id(script),
            passed=False,
            detail=detail,
        ),
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
    script: str,
    *checks: str,
    required: bool = True,
) -> DelegateConfig:
    """Build a DelegateConfig with --check args."""
    args: list[str] = []
    for check in checks:
        args.extend(("--check", check))
    return DelegateConfig(script, tuple(args), required=required)


# Ordered identically to the bash orchestrator
STRUCTURE_DELEGATIONS: Final[tuple[DelegateConfig, ...]] = (
    _delegate_checks(
        "check-security.py",
        "SC-no-shell-true",
        "SC-no-eval-exec",
        "SC-no-os-system",
        "SC-no-yaml-load",
        "SC-no-pickle",
    ),
    _delegate_checks(
        "check-references.py",
        "RF-body-lines",
        "RF-body-chars",
        "RF-dup-codeblocks-info",
        "RF-dup-tables-info",
        "RF-phase-numbering",
        "RF-long-ref-toc",
    ),
    _delegate_checks(
        "check-file-refs.py",
        "FR-resolves",
        "FR-no-backslash",
        "FR-no-disallowed",
        "FR-one-level",
        "FR-mentions-file",
        "FR-link-format",
    ),
    _delegate("check-scripts-dir.py"),
    _delegate_checks(
        "check-content.py",
        "CT-no-secrets",
        "CT-no-echo",
        "CT-no-grading",
        "CT-long-prose",
        "CT-unversioned-cmd-info",
    ),
    _delegate_checks(
        "check-config.py",
        "CF-state-xdg",
        "CF-tools-usage",
        "CF-side-effect",
        "CF-mcp-format",
    ),
    _delegate("check-best-practices.py"),
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
        else:
            collector.record_delegate_warning(config.script, error)
        return

    if parsed is None:
        if config.required:
            _emit_delegate_runtime_error(
                collector,
                config.script,
                f"No parsed output from {config.script}",
            )
        else:
            collector.record_delegate_warning(
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

    detail = f"Scripts/ has {crits} critical, {meds} medium finding(s)"
    if top_findings:
        detail += " - " + "; ".join(top_findings)
    return detail


def _handle_lint_scripts(  # noqa: PLR0911
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run check-lint.py and aggregate into a single script-lint result."""
    scripts_dir = skill_dir / "scripts"

    if not scripts_dir.is_dir():
        collector.add(
            CheckRecord(
                check=CHECK_SCRIPT_LINT,
                passed=True,
                detail="No scripts/ directory",
            ),
        )
        return

    lint_script = script_dir / "check-lint.py"
    run_result, error = _run_and_validate_script(
        lint_script,
        (str(scripts_dir), "--json", "--severity", "medium"),
    )
    if error:
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            error,
            check=CHECK_SCRIPT_LINT,
        )
        return
    if run_result is None:
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            "No result from check-lint.py",
            check=CHECK_SCRIPT_LINT,
        )
        return

    parsed = _parse_lint_output(run_result.stdout)
    if parsed.invalid_lines:
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            f"Invalid NDJSON from check-lint.py: {parsed.invalid_lines[0]}",
            check=CHECK_SCRIPT_LINT,
        )
        return

    summary = parsed.summary
    if summary is None:
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            "Missing summary line from check-lint.py",
            check=CHECK_SCRIPT_LINT,
        )
        return

    lint_total = _summary_int(summary, "findings")
    if lint_total is None:
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            "Summary missing integer 'findings' in check-lint.py",
            check=CHECK_SCRIPT_LINT,
        )
        return

    if lint_total != len(parsed.findings):
        _emit_delegate_runtime_error(
            collector,
            lint_script.name,
            (
                "Summary findings mismatch in check-lint.py: "
                f"summary={lint_total}, parsed={len(parsed.findings)}"
            ),
            check=CHECK_SCRIPT_LINT,
        )
        return

    if lint_total == 0:
        collector.add(
            CheckRecord(
                check=CHECK_SCRIPT_LINT,
                passed=True,
                detail="No critical/medium findings in scripts/",
            ),
        )
        return

    collector.add(
        CheckRecord(
            check=CHECK_SCRIPT_LINT,
            passed=False,
            detail=_aggregate_lint_findings(parsed.findings),
        ),
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

    # B6: search for the summary/recommendation record
    summary_obj = None
    for obj in objects:
        if obj.get("kind") == "summary" or "recommendation" in obj:
            summary_obj = obj
            break
    if summary_obj is None:
        return None, "No summary or recommendation record found"
    return summary_obj, None


def _handle_fork_candidate(  # noqa: C901, PLR0911
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run check-fork-candidate.py and emit single fork-candidate-info result."""
    fork_script = script_dir / "check-fork-candidate.py"
    run_result, error = _run_and_validate_script(
        fork_script,
        (str(skill_dir),),
    )
    if error:
        _emit_delegate_runtime_error(
            collector,
            fork_script.name,
            error,
            check=CHECK_FORK_INFO,
        )
        return
    if run_result is None:
        _emit_delegate_runtime_error(
            collector,
            fork_script.name,
            "No result from check-fork-candidate.py",
            check=CHECK_FORK_INFO,
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

    detail = str(summary_obj.get("detail", "")).strip().rstrip(".")
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
            CheckRecord.info(
                CHECK_FORK_INFO,
                detail,
                tier="P9",
            ),
        )
        return

    if recommendation == "none":
        if return_code != 1:
            _emit_delegate_runtime_error(
                collector,
                fork_script.name,
                f"Recommendation is none but exit code is {return_code} (expected 1)",
                check=CHECK_FORK_INFO,
            )
            return
        collector.add(
            CheckRecord.info(
                CHECK_FORK_INFO,
                f"No fork recommendation - {detail}",
                tier="P9",
            ),
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


def _progress(*, verbose: bool, message: str) -> None:
    """Emit progress to stderr when verbose."""
    if verbose:
        sys.stderr.write(f"  {message}\n")


def run_structure(
    doc: SkillDocument,
    script_dir: Path,
    collector: ResultCollector,
    *,
    verbose: bool = False,
) -> None:
    """Run all structure checks via delegation."""
    # Standard delegations
    for config in STRUCTURE_DELEGATIONS:
        _progress(verbose=verbose, message=f"checking {config.script}...")
        _run_structure_delegate(config, script_dir, doc.skill_dir, collector)

    # Special cases
    _progress(verbose=verbose, message="checking check-lint.py...")
    _handle_lint_scripts(script_dir, doc.skill_dir, collector)
    _progress(verbose=verbose, message="checking check-ask-user.py...")
    _run_structure_delegate(
        _delegate("check-ask-user.py", guard_field="total"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Flag coverage (I22)
    _progress(verbose=verbose, message="checking check-flag-coverage.py...")
    _run_structure_delegate(
        _delegate("check-flag-coverage.py"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Hooks validation (I23)
    _progress(verbose=verbose, message="checking check-hooks.py...")
    _run_structure_delegate(
        _delegate("check-hooks.py"),
        script_dir,
        doc.skill_dir,
        collector,
    )

    # Fork candidate (P9, informational)
    _progress(verbose=verbose, message="checking check-fork-candidate.py...")
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Show progress on stderr",
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
            CheckRecord(
                check=CHECK_SKILL_EXISTS,
                passed=False,
                detail=("Invalid arguments (usage: validate.py <skill-dir> [mode])"),
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
            CheckRecord(
                check=CHECK_SKILL_EXISTS,
                passed=False,
                detail=str(error),
            ),
        )
        collector.emit_summary()
        return EXIT_USAGE_ERROR

    collector = ResultCollector()

    if args.mode in {"all", "frontmatter"}:
        run_frontmatter(doc, collector)
    if args.mode in {"all", "structure"}:
        run_structure(doc, script_dir, collector, verbose=args.verbose)

    collector.emit_summary()
    return 1 if collector.failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
