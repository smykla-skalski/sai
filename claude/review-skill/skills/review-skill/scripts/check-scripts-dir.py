#!/usr/bin/env python3
"""Validate script invocation and runnable script permissions for a skill.

Sub-checks:
- `script-invocation-prefix`
- `no-bash-prefix`
- `script-executable`

Output is NDJSON with one final summary line.
Exit codes:
- 0 when all checks pass
- 1 when any check fails
- 2 for usage/input errors
"""

from __future__ import annotations

import argparse
import re
import stat
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from skill_check_common import (
    EXIT_USAGE_ERROR,
    FENCE_RE,
    CheckResult,
    ProseLine,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    extract_prose_lines,
    format_hit,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

SCRIPT_INVOCATION_PREFIX_CHECK: Final[str] = "script-invocation-prefix"
NO_BASH_PREFIX_CHECK: Final[str] = "no-bash-prefix"
SCRIPT_EXECUTABLE_CHECK: Final[str] = "script-executable"

CHECK_ORDER: Final[tuple[str, ...]] = (
    SCRIPT_INVOCATION_PREFIX_CHECK,
    NO_BASH_PREFIX_CHECK,
    SCRIPT_EXECUTABLE_CHECK,
)

# ---------------------------------------------------------------------------
# Patterns and constants
# ---------------------------------------------------------------------------

SCRIPT_PATH_RE: Final[Pattern[str]] = re.compile(
    r"scripts/[a-zA-Z0-9._-]+\.(?:sh|py)\b",
)
HEADING_LINE_RE: Final[Pattern[str]] = re.compile(r"^\s*#{1,6}\s")
BASH_PREFIX_RE: Final[Pattern[str]] = re.compile(r"^\s*bash\b")

SCRIPT_EXTENSIONS: Final[frozenset[str]] = frozenset({".sh", ".py"})
REQUIRED_PREFIX_ENDINGS: Final[tuple[str, ...]] = (
    "${CLAUDE_SKILL_DIR}/",
    "$SKILL_DIR/",
)
SHEBANG_PREFIX: Final[str] = "#!"
EXECUTABLE_MODE_MASK: Final[int] = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_required_prefix(line_text: str, script_start: int) -> bool:
    """Return whether script path has required variable prefix immediately before it."""
    prefix_region = line_text[:script_start]
    return prefix_region.endswith(REQUIRED_PREFIX_ENDINGS)


def _iter_fenced_code_lines(body: str) -> Iterator[ProseLine]:
    """Yield lines that are inside any fenced code block."""
    in_fence = False

    for index, line in enumerate(body.splitlines()):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue

        if in_fence:
            yield ProseLine(index=index, text=line)


def _read_first_line(path: Path) -> str:
    """Read the first line of a file using UTF-8 replacement handling."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            return handle.readline()
    except OSError:
        return ""


def _is_runnable_entrypoint(path: Path) -> bool:
    """Return whether a file is a runnable script entrypoint.

    Rules:
    - regular file
    - extension in {`.sh`, `.py`}
    - shebang on the first line
    """
    if not path.is_file() or path.name.startswith("."):
        return False
    if path.suffix.lower() not in SCRIPT_EXTENSIONS:
        return False
    return _read_first_line(path).startswith(SHEBANG_PREFIX)


def _iter_runnable_scripts(scripts_dir: Path) -> Iterator[Path]:
    """Yield runnable entrypoint scripts in stable sorted order."""
    for path in sorted(scripts_dir.iterdir()):
        if _is_runnable_entrypoint(path):
            yield path


def _has_executable_bit(path: Path) -> bool:
    """Return whether any executable mode bit is set on file."""
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return (mode & EXECUTABLE_MODE_MASK) != 0


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_script_invocation_prefix(document: SkillDocument) -> list[CheckResult]:
    """Validate variable prefix usage for script references in prose."""
    if not (document.skill_dir / "scripts").is_dir():
        return []

    violations: list[str] = []
    for line in extract_prose_lines(document.body):
        if HEADING_LINE_RE.match(line.text):
            continue

        for match in SCRIPT_PATH_RE.finditer(line.text):
            if _has_required_prefix(line.text, match.start()):
                continue
            violations.append(
                format_hit(
                    line.index,
                    line.text,
                    body_start_line=document.body_start_line,
                ),
            )

    if violations:
        return [
            CheckResult(
                check=SCRIPT_INVOCATION_PREFIX_CHECK,
                passed=False,
                detail=(
                    f"Found {len(violations)} script reference(s) without "
                    "${CLAUDE_SKILL_DIR} prefix - use "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." - '
                    f"first: {violations[0]}"
                ),
            ),
        ]

    return [
        CheckResult(
            check=SCRIPT_INVOCATION_PREFIX_CHECK,
            passed=True,
            detail="All script references use ${CLAUDE_SKILL_DIR} prefix",
        ),
    ]


def check_no_bash_prefix(document: SkillDocument) -> list[CheckResult]:
    """Validate that script invocations do not start with `bash` prefix."""
    if not (document.skill_dir / "scripts").is_dir():
        return []

    violations: list[str] = []
    for line in _iter_fenced_code_lines(document.body):
        if not BASH_PREFIX_RE.match(line.text):
            continue
        if SCRIPT_PATH_RE.search(line.text) is None:
            continue
        violations.append(
            format_hit(
                line.index,
                line.text,
                body_start_line=document.body_start_line,
            ),
        )

    if violations:
        return [
            CheckResult(
                check=NO_BASH_PREFIX_CHECK,
                passed=False,
                detail=(
                    f"Found {len(violations)} script invocation(s) using bash "
                    "prefix - invoke directly via "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." and set executable bit '
                    f"- first: {violations[0]}"
                ),
            ),
        ]

    return [
        CheckResult(
            check=NO_BASH_PREFIX_CHECK,
            passed=True,
            detail="No bash-prefixed script invocations found",
        ),
    ]


def check_script_executable(document: SkillDocument) -> list[CheckResult]:
    """Validate executable bits for runnable script entrypoints only."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    runnable_scripts = list(_iter_runnable_scripts(scripts_dir))
    if not runnable_scripts:
        return [
            CheckResult(
                check=SCRIPT_EXECUTABLE_CHECK,
                passed=True,
                detail="No runnable script entrypoints found in scripts/",
            ),
        ]

    results: list[CheckResult] = []
    for path in runnable_scripts:
        if _has_executable_bit(path):
            results.append(
                CheckResult(
                    check=SCRIPT_EXECUTABLE_CHECK,
                    passed=True,
                    detail=f"Script '{path.name}' has executable bit set",
                ),
            )
        else:
            results.append(
                CheckResult(
                    check=SCRIPT_EXECUTABLE_CHECK,
                    passed=False,
                    detail=(
                        f"Script '{path.name}' missing executable bit "
                        "- run chmod +x"
                    ),
                ),
            )
    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[
    dict[str, Callable[[SkillDocument], list[CheckResult]]]
] = {
    SCRIPT_INVOCATION_PREFIX_CHECK: check_script_invocation_prefix,
    NO_BASH_PREFIX_CHECK: check_no_bash_prefix,
    SCRIPT_EXECUTABLE_CHECK: check_script_executable,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckResult]:
    """Run all script-dir checks and return results in stable order."""
    selected = frozenset(selected_checks)
    results: list[CheckResult] = []

    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        results.extend(CHECK_FUNCTIONS[check_name](document))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate scripts directory invocation and executability checks.",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=CHECK_ORDER,
        dest="checks",
        help="Run only specified check (repeatable)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI entry point and return process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        document = load_skill_document(args.skill_directory)
    except SkillLoadError as error:
        emit_error(f"Error: {error}")
        return EXIT_USAGE_ERROR

    selected_checks = tuple(args.checks or ())
    return emit_results(run_checks(document, selected_checks))


if __name__ == "__main__":
    raise SystemExit(main())
