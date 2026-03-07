#!/usr/bin/env python3
"""Validate content-quality checks for SKILL.md and bundled files.

Sub-checks:
- CT-no-secrets
- CT-no-echo
- CT-no-grading

Output is NDJSON, one object per line, with a summary on the final line.
Exit codes: 0 when all pass, 1 when any fail, 2 for usage/input errors.
"""

from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    SNIPPET_WIDTH,
    CheckRecord,
    SkillDocument,
    iter_fence_lines,
    read_text,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHECK_NO_SECRETS: Final[str] = "CT-no-secrets"
CHECK_NO_USELESS_ECHO: Final[str] = "CT-no-echo"
CHECK_NO_GRADING_STYLE: Final[str] = "CT-no-grading"

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


def check_no_secrets(document: SkillDocument) -> CheckRecord:
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
        return CheckRecord(
            check=CHECK_NO_SECRETS,
            passed=False,
            detail=f"Possible secrets or credentials found in: {file_list}",
            tier="C7",
        )

    return CheckRecord(
        check=CHECK_NO_SECRETS,
        passed=True,
        detail="No secrets or credentials detected",
        tier="C7",
    )


def _find_useless_echo_hits(markdown_text: str) -> list[str]:
    """Return suspicious `$(echo ...)` lines from shell code fences."""
    hits: list[str] = []

    for prose_line in iter_fence_lines(markdown_text, SHELL_FENCE_LANGUAGES):
        if not USELESS_ECHO_PATTERN.search(prose_line.text):
            continue
        if VARIABLE_ECHO_PATTERN.search(prose_line.text):
            continue
        hits.append(prose_line.text)

    return hits


def check_no_useless_echo(document: SkillDocument) -> CheckRecord:
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
        return CheckRecord(
            check=CHECK_NO_USELESS_ECHO,
            passed=False,
            detail=(
                "Useless echo (SC2116) in code blocks: "
                f"{file_list} - first: {first_hit}"
            ),
            tier="I13",
        )

    return CheckRecord(
        check=CHECK_NO_USELESS_ECHO,
        passed=True,
        detail="No useless echo patterns in code blocks",
        tier="I13",
    )


def _grading_evidence(prose_body: str) -> list[str]:
    """Return matched grading/rubric evidence labels."""
    evidence: list[str] = []

    for label, pattern in GRADING_PATTERNS:
        if pattern.search(prose_body):
            evidence.append(label)

    return evidence


def check_no_grading_style(document: SkillDocument) -> CheckRecord:
    """Detect grading/rubric-style language in prose workflow guidance."""
    evidence = _grading_evidence(document.prose_body)
    signal_count = len(evidence)

    if signal_count >= GRADING_SIGNAL_THRESHOLD:
        evidence_text = " ".join(evidence)
        return CheckRecord(
            check=CHECK_NO_GRADING_STYLE,
            passed=False,
            detail=(
                "Grading/rubric style detected "
                f"({signal_count} signals: {evidence_text}) - "
                "restructure as imperative workflow"
            ),
            tier="C6",
        )

    return CheckRecord(
        check=CHECK_NO_GRADING_STYLE,
        passed=True,
        detail="No grading/rubric style detected",
        tier="C6",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    CheckFunction = Callable[[SkillDocument], CheckRecord]

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
) -> list[CheckRecord]:
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


def main(argv: list[str] | None = None) -> int:
    """Run content checks and return the process exit code."""
    return run_check_cli(
        "Validate content quality checks for a skill directory",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
