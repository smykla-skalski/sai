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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from skill_check_common import (
    CheckResult,
    SkillDocument,
    SkillLoadError,
    emit_record,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Ensure we don't write .pyc files into plugin cache
# ---------------------------------------------------------------------------

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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
FIRST_PERSON_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\"?(I can|You can)",
    re.IGNORECASE,
)

VALID_MODES: Final[frozenset[str]] = frozenset({"all", "frontmatter", "structure"})
LINT_TOP_FINDINGS_LIMIT: Final[int] = 3


# ---------------------------------------------------------------------------
# Result collector (replaces bash TOTAL/PASSED/FAILED globals)
# ---------------------------------------------------------------------------


@dataclass
class ResultCollector:
    """Collect check results and stream them as NDJSON."""

    total: int = field(default=0, init=False)
    passed: int = field(default=0, init=False)
    failed: int = field(default=0, init=False)

    def add(self, result: CheckResult) -> None:
        """Record one result and emit it immediately."""
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        emit_record(result.payload())

    def emit_summary(self) -> None:
        """Emit the final summary line."""
        emit_record({
            "summary": True,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
        })


# ---------------------------------------------------------------------------
# Frontmatter checks
# ---------------------------------------------------------------------------


def _check_name(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run name-present, name-format, name-matches-dir checks."""
    name = doc.field("name")
    dir_name = doc.skill_dir.name

    if not name:
        collector.add(CheckResult(
            check="name-present",
            passed=False,
            detail="Field 'name' is missing from frontmatter",
        ))
        return

    collector.add(CheckResult(
        check="name-present",
        passed=True,
        detail="Field 'name' is present",
    ))

    # format validation
    if len(name) > NAME_MAX_LENGTH:
        collector.add(CheckResult(
            check="name-format",
            passed=False,
            detail=f"Name '{name}' exceeds 64 characters ({len(name)})",
        ))
    elif not NAME_RE.match(name):
        collector.add(CheckResult(
            check="name-format",
            passed=False,
            detail=(
                f"Name '{name}' contains invalid characters "
                "(only lowercase, numbers, hyphens)"
            ),
        ))
    elif name.startswith("-") or name.endswith("-"):
        collector.add(CheckResult(
            check="name-format",
            passed=False,
            detail=f"Name '{name}' must not start or end with a hyphen",
        ))
    elif "--" in name:
        collector.add(CheckResult(
            check="name-format",
            passed=False,
            detail=f"Name '{name}' contains consecutive hyphens",
        ))
    else:
        collector.add(CheckResult(
            check="name-format",
            passed=True,
            detail=f"Name '{name}' matches pattern [a-z0-9-]{{1,64}}",
        ))

    # matches directory
    if name == dir_name:
        collector.add(CheckResult(
            check="name-matches-dir",
            passed=True,
            detail=f"Name '{name}' matches directory '{dir_name}'",
        ))
    else:
        collector.add(CheckResult(
            check="name-matches-dir",
            passed=False,
            detail=f"Name '{name}' does not match directory '{dir_name}'",
        ))


def _check_description(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run description-present, description-length, trigger-phrases, third-person."""
    description = doc.field("description")

    if not description:
        collector.add(CheckResult(
            check="description-present",
            passed=False,
            detail="Field 'description' is missing from frontmatter",
        ))
        return

    collector.add(CheckResult(
        check="description-present",
        passed=True,
        detail="Field 'description' is present",
    ))

    # length
    if len(description) > DESCRIPTION_MAX_LENGTH:
        collector.add(CheckResult(
            check="description-length",
            passed=False,
            detail=(
                f"Description is {len(description)} chars, "
                f"exceeds {DESCRIPTION_MAX_LENGTH}-char limit"
            ),
        ))
    else:
        collector.add(CheckResult(
            check="description-length",
            passed=True,
            detail=(
                f"Description is {len(description)} chars "
                f"(limit {DESCRIPTION_MAX_LENGTH})"
            ),
        ))

    # trigger phrases (skip if DMI)
    dmi = doc.field("disable-model-invocation")
    if dmi.lower() == "true":
        collector.add(CheckResult(
            check="description-trigger-phrases",
            passed=True,
            detail="Trigger phrases not required (disable-model-invocation: true)",
        ))
    elif TRIGGER_PHRASE_RE.search(description):
        collector.add(CheckResult(
            check="description-trigger-phrases",
            passed=True,
            detail="Description includes trigger phrase (when/use/for)",
        ))
    else:
        collector.add(CheckResult(
            check="description-trigger-phrases",
            passed=False,
            detail=(
                "Description should include a trigger phrase "
                "(when/use/for) for discoverability"
            ),
        ))

    # third-person voice
    if FIRST_PERSON_RE.match(description):
        collector.add(CheckResult(
            check="description-third-person",
            passed=False,
            detail=(
                "Description should use third-person form, "
                "not 'I can' or 'You can'"
            ),
        ))
    else:
        collector.add(CheckResult(
            check="description-third-person",
            passed=True,
            detail="Description uses appropriate voice",
        ))


def _check_allowed_tools(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run allowed-tools-present check."""
    allowed_tools = doc.field("allowed-tools")
    if not allowed_tools:
        collector.add(CheckResult(
            check="allowed-tools-present",
            passed=False,
            detail="Field 'allowed-tools' is missing from frontmatter",
        ))
    else:
        collector.add(CheckResult(
            check="allowed-tools-present",
            passed=True,
            detail=f"Field 'allowed-tools' is present: {allowed_tools}",
        ))


def _check_user_invocable(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run user-invocable-present check."""
    user_invocable = doc.field("user-invocable")
    if not user_invocable:
        collector.add(CheckResult(
            check="user-invocable-present",
            passed=False,
            detail="Field 'user-invocable' is missing from frontmatter",
        ))
    elif user_invocable in {"true", "false"}:
        collector.add(CheckResult(
            check="user-invocable-present",
            passed=True,
            detail=f"Field 'user-invocable' is '{user_invocable}'",
        ))
    else:
        collector.add(CheckResult(
            check="user-invocable-present",
            passed=False,
            detail=(
                "Field 'user-invocable' must be boolean (true/false), "
                f"got '{user_invocable}'"
            ),
        ))


def run_frontmatter(doc: SkillDocument, collector: ResultCollector) -> None:
    """Run all 9 frontmatter checks."""
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


def _parse_ndjson_line(line: str) -> dict[str, object] | None:
    """Parse one NDJSON line, returning None on failure."""
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _reemit_results(
    output: str,
    collector: ResultCollector,
) -> None:
    """Re-emit non-summary check results from delegate output."""
    for line in output.splitlines():
        obj = _parse_ndjson_line(line)
        if obj is None:
            continue
        if obj.get("summary"):
            continue
        check = obj.get("check")
        passed = obj.get("pass")
        detail = obj.get("detail", "")
        if not isinstance(check, str) or not isinstance(passed, bool):
            continue
        collector.add(CheckResult(
            check=check,
            passed=passed,
            detail=str(detail),
        ))


def _run_delegate(
    script_path: Path,
    skill_dir: Path,
    extra_args: tuple[str, ...] = (),
    *,
    guard_field: str = "",
) -> str:
    """Run a companion script and return its stdout, or empty on skip."""
    if not script_path.is_file() or not os.access(script_path, os.X_OK):
        return ""

    cmd = [str(script_path), str(skill_dir), *extra_args]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""

    output = result.stdout
    if not output:
        return ""

    if not guard_field:
        return output

    return _apply_guard(output, guard_field)


def _apply_guard(output: str, guard_field: str) -> str:
    """Return output if guard_field value > 0, empty string otherwise."""
    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    obj = _parse_ndjson_line(last_line)
    if obj is None:
        return ""
    try:
        val = int(obj.get(guard_field, 0))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    return output if val > 0 else ""


# ---------------------------------------------------------------------------
# Structure delegation table
# ---------------------------------------------------------------------------

# Ordered identically to the bash orchestrator
def _d(
    script: str,
    args: tuple[str, ...] = (),
    *,
    guard_field: str = "",
) -> DelegateConfig:
    """Build a DelegateConfig with compact syntax."""
    return DelegateConfig(script, args, guard_field)


def _chk(script: str, *checks: str) -> DelegateConfig:
    """Build a DelegateConfig with --check args."""
    args: list[str] = []
    for check in checks:
        args.extend(("--check", check))
    return DelegateConfig(script, tuple(args))


# Ordered identically to the bash orchestrator
STRUCTURE_DELEGATIONS: Final[
    tuple[DelegateConfig, ...]
] = (
    _chk("check-references.py", "body-line-count", "body-char-count"),
    _chk("check-file-refs.py", "file-ref-resolves"),
    _d("check-scripts-dir.py"),
    _chk("check-content.py", "no-secrets"),
    _chk("check-file-refs.py", "no-backslash-paths"),
    _chk("check-content.py", "no-useless-echo"),
    _chk("check-references.py", "duplicate-codeblocks-info"),
    _chk("check-references.py", "consistent-phase-numbering"),
    _chk("check-file-refs.py", "no-disallowed-files"),
    _chk("check-file-refs.py", "refs-one-level"),
    _chk("check-references.py", "long-ref-toc"),
    _chk("check-config.py", "persistent-state-xdg"),
    _chk("check-content.py", "no-grading-style"),
    _chk("check-file-refs.py", "skill-md-mentions-file"),
    _chk("check-file-refs.py", "ref-link-format"),
    _d("check-read-gates.py"),
    _chk("check-config.py", "allowed-tools-usage"),
    _chk("check-config.py", "side-effect-guard"),
    _d("check-preprocessing.py", guard_field="directives"),
)

# ---------------------------------------------------------------------------
# Special-case handlers
# ---------------------------------------------------------------------------


def _aggregate_lint_findings(output: str) -> str:
    """Parse lint NDJSON output and build a summary detail string."""
    lines = output.strip().splitlines()
    crits = 0
    meds = 0
    top_findings: list[str] = []
    for line in lines:
        obj = _parse_ndjson_line(line)
        if obj is None or obj.get("summary"):
            continue
        severity = obj.get("severity", "")
        if severity == "critical":
            crits += 1
        elif severity == "medium":
            meds += 1
        if len(top_findings) < LINT_TOP_FINDINGS_LIMIT:
            check_id = obj.get("check", "")
            message = obj.get("message", "")
            if check_id and message:
                top_findings.append(f"{check_id}: {message}")

    detail = f"scripts/ has {crits} critical, {meds} medium finding(s)"
    if top_findings:
        detail += " — " + "; ".join(top_findings)
    return detail


def _run_lint_script(lint_script: Path, scripts_dir: Path) -> str:
    """Run lint-scripts.py and return its stdout."""
    cmd = [
        str(lint_script), str(scripts_dir),
        "--json", "--severity", "medium",
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout


def _handle_lint_scripts(
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run lint-scripts.py and aggregate into a single script-lint result."""
    scripts_dir = skill_dir / "scripts"

    if not scripts_dir.is_dir():
        collector.add(CheckResult(
            check="script-lint",
            passed=True,
            detail="No scripts/ directory",
        ))
        return

    lint_script = script_dir / "lint-scripts.py"
    if not lint_script.is_file() or not os.access(lint_script, os.X_OK):
        return

    output = _run_lint_script(lint_script, scripts_dir)
    if not output:
        return

    lines = output.strip().splitlines()
    summary_obj = _parse_ndjson_line(lines[-1] if lines else "")
    lint_total = 0
    if summary_obj:
        try:
            lint_total = int(summary_obj.get("findings", 0))
        except (TypeError, ValueError):
            lint_total = 0

    if lint_total == 0:
        collector.add(CheckResult(
            check="script-lint",
            passed=True,
            detail="No critical/medium findings in scripts/",
        ))
        return

    collector.add(CheckResult(
        check="script-lint",
        passed=False,
        detail=_aggregate_lint_findings(output),
    ))


def _handle_check_ask_user(
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run check-ask-user.py and re-emit only if total > 0."""
    auq_script = script_dir / "check-ask-user.py"
    output = _run_delegate(auq_script, skill_dir)
    if not output:
        return

    lines = output.strip().splitlines()
    summary_line = lines[-1] if lines else ""
    summary_obj = _parse_ndjson_line(summary_line)
    if summary_obj is None:
        return

    try:
        total = int(summary_obj.get("total", 0))
    except (TypeError, ValueError):
        total = 0

    if total > 0:
        _reemit_results(output, collector)


def _handle_fork_candidate(
    script_dir: Path,
    skill_dir: Path,
    collector: ResultCollector,
) -> None:
    """Run check-fork-candidate.py and emit single fork-candidate-info result."""
    fork_script = script_dir / "check-fork-candidate.py"
    if not fork_script.is_file() or not os.access(fork_script, os.X_OK):
        return

    cmd = [str(fork_script), str(skill_dir)]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return

    output = result.stdout
    if not output:
        return

    last_line = output.strip().splitlines()[-1] if output.strip() else ""
    obj = _parse_ndjson_line(last_line)
    if obj is None:
        return

    recommendation = obj.get("recommendation", "")
    detail = str(obj.get("detail", ""))

    if recommendation in {"strong", "soft"}:
        collector.add(CheckResult(
            check="fork-candidate-info",
            passed=True,
            detail=f"INFO: {detail}",
        ))
    else:
        collector.add(CheckResult(
            check="fork-candidate-info",
            passed=True,
            detail=f"No fork recommendation — {detail}",
        ))


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
        script_path = script_dir / config.script
        output = _run_delegate(
            script_path,
            doc.skill_dir,
            config.args,
            guard_field=config.guard_field,
        )
        if output:
            _reemit_results(output, collector)

    # Special cases
    _handle_lint_scripts(script_dir, doc.skill_dir, collector)
    _handle_check_ask_user(script_dir, doc.skill_dir, collector)

    # Flag coverage (I22)
    flag_script = script_dir / "check-flag-coverage.py"
    output = _run_delegate(flag_script, doc.skill_dir)
    if output:
        _reemit_results(output, collector)

    # Hooks validation (I23)
    hooks_script = script_dir / "check-hooks.py"
    output = _run_delegate(hooks_script, doc.skill_dir)
    if output:
        _reemit_results(output, collector)

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
        choices=sorted(VALID_MODES),
        help="Which checks to run (default: all)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent

    try:
        doc = load_skill_document(args.skill_directory)
    except SkillLoadError:
        # Match bash behavior: emit one failing check and summary
        collector = ResultCollector()
        collector.add(CheckResult(
            check="skill-md-exists",
            passed=False,
            detail=f"SKILL.md not found in {args.skill_directory}",
        ))
        collector.emit_summary()
        return 1

    collector = ResultCollector()

    if args.mode in {"all", "frontmatter"}:
        run_frontmatter(doc, collector)
    if args.mode in {"all", "structure"}:
        run_structure(doc, script_dir, collector)

    collector.emit_summary()
    return 1 if collector.failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
