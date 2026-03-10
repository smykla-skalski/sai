#!/usr/bin/env python3
"""Validate content-quality checks for SKILL.md and bundled files.

Sub-checks:
- CT-no-secrets
- CT-no-echo
- CT-no-grading
- CT-long-prose
- CT-unversioned-cmd-info

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
    build_fenced_line_indices,
    iter_fence_lines,
    iter_reference_inputs,
    read_text,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHECK_NO_SECRETS: Final[str] = "CT-no-secrets"
CHECK_NO_USELESS_ECHO: Final[str] = "CT-no-echo"
CHECK_NO_GRADING_STYLE: Final[str] = "CT-no-grading"
CHECK_LONG_PROSE: Final[str] = "CT-long-prose"
CHECK_UNVERSIONED_CMD: Final[str] = "CT-unversioned-cmd-info"

# 2+ distinct grading signals (e.g. point-values + rubric-keywords) = rubric detected
GRADING_SIGNAL_THRESHOLD: Final[int] = 2
LONG_PROSE_THRESHOLD: Final[int] = 300

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

URL_RE: Final[Pattern[str]] = re.compile(r"https?://\S+")
TABLE_ROW_RE: Final[Pattern[str]] = re.compile(r"^\s*\|")

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

UNVERSIONED_NPX_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:npx|uvx)\s+([a-zA-Z0-9@/_-]+?)(?:\s|$)",
)
UNVERSIONED_PIPX_RE: Final[Pattern[str]] = re.compile(
    r"\bpipx\s+run\s+([a-zA-Z0-9_-]+)(?!\S*(?:==|>=|@))",
)
UNVERSIONED_PIP_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:pip|pip3)\s+install\s+([a-zA-Z0-9_-]+)(?!\S*(?:==|>=|~=|@))",
)
UNVERSIONED_GO_RE: Final[Pattern[str]] = re.compile(
    r"\bgo\s+run\s+(\S+?)(?:\s|$)",
)
VARIABLE_REF_RE: Final[Pattern[str]] = re.compile(r'["\$]')


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
        if file_path.name == "examples.md":
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


def _grading_evidence_from_lines(
    lines: list[str],
    *,
    skip_indices: frozenset[int],
) -> list[str]:
    """Return grading evidence labels from non-skipped lines."""
    filtered = "\n".join(
        line for index, line in enumerate(lines) if index not in skip_indices
    )
    return _grading_evidence(filtered)


def check_no_grading_style(document: SkillDocument) -> CheckRecord:
    """Detect grading/rubric-style language in SKILL.md and referenced guidance."""
    evidence = set(_grading_evidence(document.prose_body))

    ref_files = iter_reference_inputs(document)
    for ref in ref_files:
        evidence.update(
            _grading_evidence_from_lines(
                ref.lines,
                skip_indices=ref.skip_indices,
            ),
        )

    evidence_list = sorted(evidence)
    signal_count = len(evidence_list)

    if signal_count >= GRADING_SIGNAL_THRESHOLD:
        evidence_text = " ".join(evidence_list)
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
        detail=(
            "No grading/rubric style detected "
            f"(scanned SKILL.md and {len(ref_files)} referenced text file(s))"
        ),
        tier="C6",
    )


def _is_url_dominated(line: str) -> bool:
    """Return whether URLs account for most of the line length."""
    url_chars = sum(len(m.group(0)) for m in URL_RE.finditer(line))
    return url_chars > len(line) * 0.5


def check_long_prose_lines(document: SkillDocument) -> CheckRecord:
    """Detect prose lines exceeding the length threshold.

    Ignores fenced code blocks, table rows, and URL-dominated lines.
    """
    body = document.body
    body_lines = body.splitlines()
    fenced = build_fenced_line_indices(body_lines)
    long_lines: list[tuple[int, int]] = []

    for i, line in enumerate(body_lines):
        if i in fenced:
            continue
        if TABLE_ROW_RE.match(line):
            continue
        if len(line) <= LONG_PROSE_THRESHOLD:
            continue
        if _is_url_dominated(line):
            continue
        long_lines.append((i + 1, len(line)))

    if long_lines:
        first_lineno, first_len = long_lines[0]
        return CheckRecord.info(
            check=CHECK_LONG_PROSE,
            detail=(
                f"{len(long_lines)} prose line(s) exceed {LONG_PROSE_THRESHOLD} chars"
                f" - first: L{first_lineno} ({first_len} chars)"
            ),
            tier="I24",
        )

    return CheckRecord.ok(
        check=CHECK_LONG_PROSE,
        detail=f"No prose lines exceed {LONG_PROSE_THRESHOLD} chars",
        tier="I24",
    )


def _has_version_specifier(pkg: str) -> bool:
    """Return whether a package name contains a version specifier (@, ==, >=)."""
    return bool(re.search(r"[@==>=]", pkg))


def check_unversioned_commands(document: SkillDocument) -> CheckRecord:
    """Detect unversioned runner commands in shell code fences."""
    body = document.body
    hits: list[str] = []

    for prose_line in iter_fence_lines(body, SHELL_FENCE_LANGUAGES):
        line_text = prose_line.text
        if VARIABLE_REF_RE.search(line_text):
            continue

        for match in UNVERSIONED_NPX_RE.finditer(line_text):
            pkg = match.group(1)
            if not _has_version_specifier(pkg):
                hits.append(match.group(0).strip())

        hits.extend(m.group(0).strip() for m in UNVERSIONED_PIPX_RE.finditer(line_text))
        hits.extend(m.group(0).strip() for m in UNVERSIONED_PIP_RE.finditer(line_text))

        for match in UNVERSIONED_GO_RE.finditer(line_text):
            pkg = match.group(1)
            if not _has_version_specifier(pkg):
                hits.append(match.group(0).strip())

    if hits:
        return CheckRecord.info(
            CHECK_UNVERSIONED_CMD,
            (
                f"{len(hits)} unversioned runner command(s) in code fences "
                f"- first: {hits[0]}"
            ),
            tier="P22",
        )

    return CheckRecord.ok(
        CHECK_UNVERSIONED_CMD,
        "No unversioned runner commands in code fences",
        tier="P22",
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
    CHECK_LONG_PROSE,
    CHECK_UNVERSIONED_CMD,
)

CHECK_FUNCTIONS: Final[dict[str, CheckFunction]] = {
    CHECK_NO_SECRETS: check_no_secrets,
    CHECK_NO_USELESS_ECHO: check_no_useless_echo,
    CHECK_NO_GRADING_STYLE: check_no_grading_style,
    CHECK_LONG_PROSE: check_long_prose_lines,
    CHECK_UNVERSIONED_CMD: check_unversioned_commands,
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
