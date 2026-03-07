#!/usr/bin/env python3
"""Validate content-quality checks for SKILL.md and bundled files.

Sub-checks:
- no-secrets
- no-useless-echo
- no-grading-style

Output is NDJSON, one object per line, with a summary on the final line.
Exit codes: 0 when all pass, 1 when any fail, 2 for usage/input errors.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    FENCE_RE,
    SNIPPET_WIDTH,
    CheckResult,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    load_skill_document,
    read_text,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHECK_NO_SECRETS: Final[str] = "no-secrets"
CHECK_NO_USELESS_ECHO: Final[str] = "no-useless-echo"
CHECK_NO_GRADING_STYLE: Final[str] = "no-grading-style"

GRADING_SIGNAL_THRESHOLD: Final[int] = 2

SHELL_FENCE_LANGUAGES: Final[frozenset[str]] = frozenset({"", "bash", "sh", "shell"})

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

SECRET_PATTERN: Final[Pattern[str]] = re.compile(
    r"AKIA[A-Z0-9]{16}|"
    r"sk-[a-zA-Z0-9]{20,}|"
    r"-----BEGIN[ \t]+(?:RSA |EC )?(?:PRIVATE )?KEY-----|"
    r"Bearer[ \t]+[a-zA-Z0-9._-]{20,}",
)

PLACEHOLDER_PATTERN: Final[Pattern[str]] = re.compile(
    r"1234|0000|xxxx|abcdef|example|test|fake|placeholder|your_|"
    r"INSERT|REPLACE|changeme",
    re.IGNORECASE,
)

USELESS_ECHO_PATTERN: Final[Pattern[str]] = re.compile(r"\$\(\s*echo\s+")
VARIABLE_ECHO_PATTERN: Final[Pattern[str]] = re.compile(r"\$\(\s*echo[^)]*\$[A-Za-z_{]")

GRADING_PATTERNS: Final[tuple[tuple[str, Pattern[str]], ...]] = (
    (
        "point-values",
        re.compile(r"\b[0-9]+\s+(?:points?|pts)\b", re.IGNORECASE),
    ),
    (
        "score-assignments",
        re.compile(r"\b(?:score|rating)\s*:\s*[0-9]", re.IGNORECASE),
    ),
    (
        "percentage-weights",
        re.compile(
            r"\b[0-9]+%\s*(?:weight|of total)|\bweights?\s*:?\s*[0-9]+%",
            re.IGNORECASE,
        ),
    ),
    (
        "letter-grades",
        re.compile(
            r"\bgrade\s*:?\s*[A-F]\b|\b[A-F]\s*\([0-9]+-[0-9]+",
            re.IGNORECASE,
        ),
    ),
    (
        "rubric-keywords",
        re.compile(
            r"\brubric\b|\bscoring\s+matrix\b|\bgrading\s+(?:scale|criteria)\b",
            re.IGNORECASE,
        ),
    ),
)


# ---------------------------------------------------------------------------
# File and fence helpers
# ---------------------------------------------------------------------------


def _contains_real_secret(text: str) -> bool:
    """Return whether text contains a secret-like token not marked as placeholder."""
    for match in SECRET_PATTERN.finditer(text):
        token = match.group(0)
        if PLACEHOLDER_PATTERN.search(token):
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_no_secrets(document: SkillDocument) -> CheckResult:
    """Detect likely secrets or credentials in skill files."""
    hit_files: list[str] = []

    for file_path in document.resource_files:
        content = read_text(file_path)
        if not content:
            continue
        if _contains_real_secret(content):
            hit_files.append(file_path.name)

    if hit_files:
        file_list = " ".join(hit_files)
        return CheckResult(
            check=CHECK_NO_SECRETS,
            passed=False,
            detail=f"Possible secrets or credentials found in: {file_list}",
        )

    return CheckResult(
        check=CHECK_NO_SECRETS,
        passed=True,
        detail="No secrets or credentials detected",
    )


def _fence_language(line: str) -> str:
    """Extract normalized language token from an opening fence line."""
    without_fence = FENCE_RE.sub("", line, count=1)
    language = without_fence.strip().split(maxsplit=1)
    if not language:
        return ""
    return language[0].lower()


def _iter_shell_fence_lines(markdown_text: str) -> list[str]:
    """Return lines inside shell-compatible fenced code blocks."""
    lines_in_shell_fences: list[str] = []
    in_fence = False
    in_shell_fence = False

    for line in markdown_text.splitlines():
        if FENCE_RE.match(line):
            if in_fence:
                in_fence = False
                in_shell_fence = False
            else:
                in_fence = True
                in_shell_fence = _fence_language(line) in SHELL_FENCE_LANGUAGES
            continue

        if in_fence and in_shell_fence:
            lines_in_shell_fences.append(line)

    return lines_in_shell_fences


def _find_useless_echo_hits(markdown_text: str) -> list[str]:
    """Return suspicious `$(echo ...)` lines from shell code fences."""
    hits: list[str] = []

    for line in _iter_shell_fence_lines(markdown_text):
        if not USELESS_ECHO_PATTERN.search(line):
            continue
        if VARIABLE_ECHO_PATTERN.search(line):
            continue
        hits.append(line)

    return hits


def check_no_useless_echo(document: SkillDocument) -> CheckResult:
    """Detect SC2116-like `$(echo ...)` patterns in shell code fences."""
    hit_files: list[str] = []
    first_hit = ""

    for file_path in document.resource_files:
        if file_path.suffix.lower() != ".md":
            continue

        content = read_text(file_path)
        if not content:
            continue

        hits = _find_useless_echo_hits(content)
        if not hits:
            continue

        hit_files.append(file_path.name)
        if not first_hit:
            first_hit = hits[0].strip()[:SNIPPET_WIDTH]

    if hit_files:
        file_list = " ".join(hit_files)
        return CheckResult(
            check=CHECK_NO_USELESS_ECHO,
            passed=False,
            detail=(
                "Useless echo (SC2116) in code blocks: "
                f"{file_list} - first: {first_hit}"
            ),
        )

    return CheckResult(
        check=CHECK_NO_USELESS_ECHO,
        passed=True,
        detail="No useless echo patterns in code blocks",
    )


def _grading_evidence(prose_body: str) -> list[str]:
    """Return matched grading/rubric evidence labels."""
    evidence: list[str] = []

    for label, pattern in GRADING_PATTERNS:
        if pattern.search(prose_body):
            evidence.append(label)

    return evidence


def check_no_grading_style(document: SkillDocument) -> CheckResult:
    """Detect grading/rubric-style language in prose workflow guidance."""
    evidence = _grading_evidence(document.prose_body)
    signal_count = len(evidence)

    if signal_count >= GRADING_SIGNAL_THRESHOLD:
        evidence_text = " ".join(evidence)
        return CheckResult(
            check=CHECK_NO_GRADING_STYLE,
            passed=False,
            detail=(
                "Grading/rubric style detected "
                f"({signal_count} signals: {evidence_text}) - "
                "restructure as imperative workflow"
            ),
        )

    return CheckResult(
        check=CHECK_NO_GRADING_STYLE,
        passed=True,
        detail="No grading/rubric style detected",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    CheckFunction = Callable[[SkillDocument], CheckResult]

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_NO_SECRETS,
    CHECK_NO_USELESS_ECHO,
    CHECK_NO_GRADING_STYLE,
)

CHECK_FUNCTIONS: Final[dict[str, CheckFunction]] = {
    CHECK_NO_SECRETS: check_no_secrets,
    CHECK_NO_USELESS_ECHO: check_no_useless_echo,
    CHECK_NO_GRADING_STYLE: check_no_grading_style,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...],
) -> list[CheckResult]:
    """Run selected checks in stable output order."""
    selected = frozenset(selected_checks)
    checks_to_run = [
        check_name
        for check_name in CHECK_ORDER
        if not selected or check_name in selected
    ]

    return [CHECK_FUNCTIONS[check_name](document) for check_name in checks_to_run]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate content quality checks for a skill directory",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=CHECK_ORDER,
        dest="checks",
        help="Run only the specified check (can be repeated)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run content checks and return the process exit code."""
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
