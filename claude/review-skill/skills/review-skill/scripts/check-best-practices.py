#!/usr/bin/env python3
"""Validate best-practice coverage checks for SKILL.md.

Sub-checks:
  - `BP-example-tags`
  - `BP-over-prompting`
  - `BP-negative-instr-info`
  - `BP-error-section-info`
  - `BP-scope-boundary-info`
  - `BP-constraint-refresh-info`

Usage:
    ./check-best-practices.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes:
    0 - all emitted checks pass
    1 - one or more emitted checks fail
    2 - usage error
"""

from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    CheckRecord,
    SkillDocument,
    build_fenced_line_indices,
    compile_patterns,
    format_hit,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Check IDs and thresholds
# ---------------------------------------------------------------------------

CHECK_EXAMPLE_TAGS: Final[str] = "BP-example-tags"
CHECK_OVER_PROMPTING: Final[str] = "BP-over-prompting"
CHECK_NEGATIVE_INSTR: Final[str] = "BP-negative-instr-info"
CHECK_ERROR_SECTION: Final[str] = "BP-error-section-info"
CHECK_SCOPE_BOUNDARY: Final[str] = "BP-scope-boundary-info"
CHECK_CONSTRAINT_REFRESH: Final[str] = "BP-constraint-refresh-info"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_EXAMPLE_TAGS,
    CHECK_OVER_PROMPTING,
    CHECK_NEGATIVE_INSTR,
    CHECK_ERROR_SECTION,
    CHECK_SCOPE_BOUNDARY,
    CHECK_CONSTRAINT_REFRESH,
)

EXAMPLE_TAG_PASS_THRESHOLD: Final[int] = 3
OVER_PROMPT_FAIL_THRESHOLD: Final[int] = 3
PHASE_REFRESH_THRESHOLD: Final[int] = 4

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

EXAMPLE_OPEN_RE: Final[Pattern[str]] = re.compile(
    r"<example(?:\s[^>]*)?>", re.IGNORECASE,
)
EXAMPLE_CLOSE_RE: Final[Pattern[str]] = re.compile(r"</example>", re.IGNORECASE)
HEADING_RE: Final[Pattern[str]] = re.compile(r"^\s*#")

OVER_PROMPT_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"\bCRITICAL\b"),
    re.compile(r"\bYou MUST\b"),
    re.compile(r"(?<!You )\bMUST\b"),
    re.compile(r"\bALWAYS\b"),
    re.compile(r"\bNEVER\b"),
    re.compile(r"\bIMPORTANT\b"),
)

NEGATIVE_INSTR_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bDO\s+NOT\b",
        r"\bNEVER\b",
        r"\bdo\s+not\b",
        r"\b[Dd]on't\b",
    ),
)

ERROR_SECTION_RE: Final[Pattern[str]] = re.compile(
    r"^#{2,6}\s+.*(error|failure|edge case|troubleshoot)",
    re.IGNORECASE,
)

SCOPE_BOUNDARY_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bwhen\s+not\s+to\b",
        r"\bavoid\s+using\b",
        r"\bnot\s+designed\s+for\b",
        r"\blimitations?\b",
    ),
)

PHASE_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,4}\s+Phase\s+\d+",
    re.IGNORECASE,
)

CONSTRAINT_REFRESH_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\breminder\b",
        r"\brecall\b",
        r"\bre-?read\b",
        r"\bre-?anchor\b",
    ),
)

REFRESH_FALSE_POSITIVE_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bthe\s+(rewritten|output|result|generated)\b",
        r"\byour\s+(output|result|rewrite)\b",
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_example_line_indices(
    lines: list[str],
    fenced_indices: frozenset[int],
) -> frozenset[int]:
    """Return line indices inside <example> ... </example> blocks."""
    in_example = False
    indices: set[int] = set()

    for index, line in enumerate(lines):
        if index in fenced_indices:
            continue

        has_open = EXAMPLE_OPEN_RE.search(line) is not None
        has_close = EXAMPLE_CLOSE_RE.search(line) is not None

        if in_example or has_open:
            indices.add(index)
        if has_open and not has_close:
            in_example = True
        if has_close:
            in_example = False

    return frozenset(indices)


def _has_constraint_refresh(prose_body: str) -> bool:
    """Check for genuine constraint refresh language, filtering false positives.

    Excludes lines that contain negative instruction patterns (DO NOT re-read)
    and output-reading contexts (Re-read the rewritten text).
    """
    for line in prose_body.splitlines():
        if not any(p.search(line) for p in CONSTRAINT_REFRESH_PATTERNS):
            continue
        if any(p.search(line) for p in NEGATIVE_INSTR_PATTERNS):
            continue
        if any(p.search(line) for p in REFRESH_FALSE_POSITIVE_PATTERNS):
            continue
        return True
    return False


def _is_ignored_line(
    index: int,
    line: str,
    *,
    fenced_indices: frozenset[int],
    example_indices: frozenset[int],
) -> bool:
    """Return whether a line should be ignored for prose-only checks."""
    return (
        index in fenced_indices
        or index in example_indices
        or HEADING_RE.match(line.strip()) is not None
    )


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_example_tags(document: SkillDocument) -> CheckRecord:
    """Validate that SKILL.md contains <example> tags."""
    example_count = len(EXAMPLE_OPEN_RE.findall(document.body))

    if example_count == 0:
        return CheckRecord.fail(
            CHECK_EXAMPLE_TAGS,
            (
                "No <example> tags found in SKILL.md body - wrap concrete "
                "examples in <example>...</example>"
            ),
            tier="I26",
        )

    if example_count < EXAMPLE_TAG_PASS_THRESHOLD:
        return CheckRecord.info(
            CHECK_EXAMPLE_TAGS,
            (
                f"Found {example_count} <example> tag(s) - 3 or more improves "
                "coverage diversity"
            ),
            tier="I26",
        )

    return CheckRecord.ok(
        CHECK_EXAMPLE_TAGS,
        f"Found {example_count} <example> tag(s) in SKILL.md body",
        tier="I26",
    )


def check_over_prompting(document: SkillDocument) -> CheckRecord:
    """Detect aggressive emphasis patterns in prose guidance."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)
    example_indices = _build_example_line_indices(lines, fenced_indices)

    hit_count = 0
    first_evidence: str | None = None

    for index, line in enumerate(lines):
        if _is_ignored_line(
            index,
            line,
            fenced_indices=fenced_indices,
            example_indices=example_indices,
        ):
            continue

        line_hits = sum(len(pattern.findall(line)) for pattern in OVER_PROMPT_PATTERNS)
        if line_hits == 0:
            continue

        hit_count += line_hits
        if first_evidence is None:
            first_evidence = format_hit(
                index, line, body_start_line=document.body_start_line,
            )

    if hit_count >= OVER_PROMPT_FAIL_THRESHOLD:
        return CheckRecord.fail(
            CHECK_OVER_PROMPTING,
            (
                f"Detected {hit_count} aggressive emphasis pattern hit(s) "
                "outside headings/examples (threshold 3) - first: "
                f"{first_evidence}"
            ),
            tier="I27",
        )

    if hit_count > 0:
        return CheckRecord.info(
            CHECK_OVER_PROMPTING,
            (
                f"Detected {hit_count} aggressive emphasis pattern hit(s) "
                "outside headings/examples (below fail threshold of 3) - first: "
                f"{first_evidence}"
            ),
            tier="I27",
        )

    return CheckRecord.ok(
        CHECK_OVER_PROMPTING,
        "No aggressive emphasis patterns detected outside headings/examples",
        tier="I27",
    )


def check_negative_instruction_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for negative-instruction density."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)
    example_indices = _build_example_line_indices(lines, fenced_indices)
    hit_count = 0
    first_hit: str | None = None

    for index, line in enumerate(lines):
        if index in fenced_indices or index in example_indices:
            continue
        if not any(pattern.search(line) for pattern in NEGATIVE_INSTR_PATTERNS):
            continue
        hit_count += 1
        if first_hit is None:
            first_hit = format_hit(
                index, line, body_start_line=document.body_start_line,
            )

    if hit_count == 0:
        return CheckRecord.info(
            CHECK_NEGATIVE_INSTR,
            "No negative instruction patterns detected",
            tier="P11",
        )

    return CheckRecord.info(
        CHECK_NEGATIVE_INSTR,
        (
            f"Found {hit_count} negative instruction pattern(s) - consider "
            f"adding positive alternatives nearby - first: {first_hit}"
        ),
        tier="P11",
    )


def check_error_section_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for explicit error/failure sections."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)

    for index, line in enumerate(lines):
        if index in fenced_indices:
            continue
        if ERROR_SECTION_RE.search(line):
            return CheckRecord.ok(
                CHECK_ERROR_SECTION,
                "Error/failure section heading detected",
                tier="P12",
            )

    return CheckRecord.info(
        CHECK_ERROR_SECTION,
        "No error/failure/edge-case troubleshooting section heading detected",
        tier="P12",
    )


def check_scope_boundary_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for scope-boundary guidance."""
    if any(pattern.search(document.prose_body) for pattern in SCOPE_BOUNDARY_PATTERNS):
        return CheckRecord.ok(
            CHECK_SCOPE_BOUNDARY,
            "Scope-boundary language detected in SKILL.md body",
            tier="P13",
        )

    return CheckRecord.info(
        CHECK_SCOPE_BOUNDARY,
        (
            "No scope-boundary language detected (for example: when not "
            "to use, avoid using, not designed for, limitations)"
        ),
        tier="P13",
    )


def check_constraint_refresh_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for constraint refresh in long workflows."""
    phase_count = sum(
        1 for line in document.prose_body.splitlines() if PHASE_HEADING_RE.search(line)
    )

    if phase_count < PHASE_REFRESH_THRESHOLD:
        return CheckRecord.skip(
            CHECK_CONSTRAINT_REFRESH,
            (
                "Constraint refresh check skipped - fewer than 4 phases "
                f"detected ({phase_count})"
            ),
            tier="P14",
        )

    if _has_constraint_refresh(document.prose_body):
        return CheckRecord.ok(
            CHECK_CONSTRAINT_REFRESH,
            (
                f"Constraint refresh language detected with {phase_count} phase "
                "heading(s)"
            ),
            tier="P14",
        )

    return CheckRecord.info(
        CHECK_CONSTRAINT_REFRESH,
        (
            f"Found {phase_count} phase heading(s) but no explicit "
            "constraint refresh language (reminder, recall, re-read, re-anchor)"
        ),
        tier="P14",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], CheckRecord]]] = {
    CHECK_EXAMPLE_TAGS: check_example_tags,
    CHECK_OVER_PROMPTING: check_over_prompting,
    CHECK_NEGATIVE_INSTR: check_negative_instruction_info,
    CHECK_ERROR_SECTION: check_error_section_info,
    CHECK_SCOPE_BOUNDARY: check_scope_boundary_info,
    CHECK_CONSTRAINT_REFRESH: check_constraint_refresh_info,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    """Run best-practice checks and return emitted records in order."""
    selected = frozenset(selected_checks)
    return [
        CHECK_FUNCTIONS[check_name](document)
        for check_name in CHECK_ORDER
        if not selected or check_name in selected
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    return run_check_cli(
        "Validate best-practice coverage checks for SKILL.md",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
