#!/usr/bin/env python3
"""Verify flag documentation consistency in SKILL.md.

Compares three zones where flags are declared:
  1. argument-hint frontmatter field (autocomplete hint)
  2. Arguments section in SKILL.md body (formal documentation)
  3. Workflow/body text outside Arguments and Examples (actual usage)

Sub-checks:
  - `FC-hint-doc`      - every --flag in argument-hint appears in Arguments section
  - `FC-doc-hint`      - every --flag in Arguments section appears in argument-hint
  - `FC-doc-workflow`  - every --flag in Arguments section is
                          referenced in workflow body
  - `FC-example-flags` - examples cover at least 50% of documented flags

Usage:
    ./check-flag-coverage.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes: 0 = all pass, 1 = any fail, 2 = usage error.
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
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_HINT_DOC: Final[str] = "FC-hint-doc"
CHECK_DOC_HINT: Final[str] = "FC-doc-hint"
CHECK_DOC_WORKFLOW: Final[str] = "FC-doc-workflow"
CHECK_EXAMPLE_FLAGS: Final[str] = "FC-example-flags"

MIN_FLAGS_FOR_EXAMPLE_CHECK: Final[int] = 3
EXAMPLE_COVERAGE_THRESHOLD: Final[float] = 0.5

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_HINT_DOC,
    CHECK_DOC_HINT,
    CHECK_DOC_WORKFLOW,
    CHECK_EXAMPLE_FLAGS,
)

# ---------------------------------------------------------------------------
# Flag extraction
# ---------------------------------------------------------------------------

FLAG_RE: Final[Pattern[str]] = re.compile(r"--[a-zA-Z][\w-]*")

EXAMPLE_SECTION_PATTERNS: Final[tuple[str, ...]] = (
    r"\bexample\s+invocations?\b",
    r"\bexamples?\b",
)
MIN_EXAMPLE_HEADER_LEVEL: Final[int] = 2


def _extract_flags(text: str) -> set[str]:
    """Extract all --flag patterns from text."""
    return set(FLAG_RE.findall(text))


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------


def _find_section(
    lines: list[str],
    pattern: str,
    fenced: frozenset[int],
) -> tuple[int | None, int | None]:
    """Find section by header regex, return (start_idx, end_idx).

    Matches ## or ### headers outside fenced code blocks. The section
    ends at the next header of equal or higher level, or end of file.
    """
    start: int | None = None
    header_level: int | None = None

    for i, line in enumerate(lines):
        if i in fenced:
            continue
        header_match = re.match(r"^(#{1,6})\s+", line)

        if start is None:
            if header_match and re.search(pattern, line, re.IGNORECASE):
                start = i
                header_level = len(header_match.group(1))
        elif header_match and len(header_match.group(1)) <= (header_level or 0):
            return (start, i)

    if start is not None:
        return (start, len(lines))
    return (None, None)


def _find_all_sections(
    lines: list[str],
    pattern: str,
    fenced: frozenset[int],
) -> list[tuple[int, int]]:
    """Find all sections matching pattern, return list of (start, end) tuples."""
    sections: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if i in fenced:
            i += 1
            continue
        header_match = re.match(r"^(#{1,6})\s+", lines[i])
        if header_match and re.search(pattern, lines[i], re.IGNORECASE):
            start = i
            level = len(header_match.group(1))
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if j in fenced:
                    continue
                hm = re.match(r"^(#{1,6})\s+", lines[j])
                if hm and len(hm.group(1)) <= level:
                    end = j
                    break
            sections.append((start, end))
            i = end
        else:
            i += 1
    return sections


# ---------------------------------------------------------------------------
# Zone extraction
# ---------------------------------------------------------------------------


def _get_arguments_section_flags(
    body_lines: list[str],
    fenced: frozenset[int],
) -> set[str]:
    """Extract --flag patterns from the Arguments section."""
    start, end = _find_section(body_lines, r"\barguments\b", fenced)
    if start is None:
        return set()
    section_text = "\n".join(body_lines[start:end])
    return _extract_flags(section_text)


def _get_workflow_flags(
    body_lines: list[str],
    fenced: frozenset[int],
) -> set[str]:
    """Extract --flag patterns from body excluding Arguments and Example sections."""
    args_start, args_end = _find_section(
        body_lines,
        r"\barguments\b",
        fenced,
    )

    exclude_ranges: list[tuple[int, int]] = []
    if args_start is not None and args_end is not None:
        exclude_ranges.append((args_start, args_end))

    for pattern in EXAMPLE_SECTION_PATTERNS:
        for s, e in _find_all_sections(body_lines, pattern, fenced):
            exclude_ranges.append((s, e))

    for s, e in _find_all_sections(
        body_lines,
        r"\bbundled\s+resources\b",
        fenced,
    ):
        exclude_ranges.append((s, e))

    workflow_lines: list[str] = []
    for i, line in enumerate(body_lines):
        excluded = any(rs <= i < re_ for rs, re_ in exclude_ranges)
        if not excluded:
            workflow_lines.append(line)

    return _extract_flags("\n".join(workflow_lines))


def _get_examples_section_flags(
    body_lines: list[str],
    fenced: frozenset[int],
) -> set[str]:
    """Extract --flag patterns from the first Example* section (level 2+)."""
    for pattern in EXAMPLE_SECTION_PATTERNS:
        for start, end in _find_all_sections(body_lines, pattern, fenced):
            header_match = re.match(r"^(#{1,6})\s+", body_lines[start])
            if header_match and len(header_match.group(1)) >= MIN_EXAMPLE_HEADER_LEVEL:
                return _extract_flags("\n".join(body_lines[start:end]))
    return set()


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def _check_hint_doc(
    hint_flags: set[str],
    doc_flags: set[str],
) -> CheckRecord | None:
    """Check that flags in argument-hint appear in Arguments section."""
    if not hint_flags:
        return None

    if doc_flags:
        missing = sorted(hint_flags - doc_flags)
        if missing:
            return CheckRecord(
                check=CHECK_HINT_DOC,
                passed=False,
                detail=(
                    "Flags in argument-hint not documented in Arguments section: "
                    f"{', '.join(missing)}"
                ),
                tier="I22",
            )
        return CheckRecord(
            check=CHECK_HINT_DOC,
            passed=True,
            detail=f"All {len(hint_flags)} argument-hint flags documented",
            tier="I22",
        )

    return CheckRecord(
        check=CHECK_HINT_DOC,
        passed=False,
        detail=(
            f"Argument-hint has {len(hint_flags)} flags but no Arguments "
            "section found in body"
        ),
        tier="I22",
    )


def _check_doc_hint(
    doc_flags: set[str],
    hint_flags: set[str],
    hint_raw: str,
) -> CheckRecord | None:
    """Check that flags in Arguments section appear in argument-hint."""
    if not doc_flags:
        return None

    if hint_flags:
        missing = sorted(doc_flags - hint_flags)
        if missing:
            return CheckRecord(
                check=CHECK_DOC_HINT,
                passed=False,
                detail=(
                    "Flags in Arguments section missing from argument-hint: "
                    f"{', '.join(missing)}"
                ),
                tier="I22",
            )
        return CheckRecord(
            check=CHECK_DOC_HINT,
            passed=True,
            detail=f"All {len(doc_flags)} documented flags in argument-hint",
            tier="I22",
        )

    if not hint_raw:
        return CheckRecord(
            check=CHECK_DOC_HINT,
            passed=False,
            detail=(
                f"Arguments section documents {len(doc_flags)} flags but "
                "argument-hint field is missing from frontmatter"
            ),
            tier="I22",
        )

    return CheckRecord(
        check=CHECK_DOC_HINT,
        passed=False,
        detail=(
            f"Arguments section documents {len(doc_flags)} flags but "
            f"argument-hint has none: {', '.join(sorted(doc_flags))}"
        ),
        tier="I22",
    )


def _check_doc_workflow(
    doc_flags: set[str],
    workflow_flags: set[str],
) -> CheckRecord | None:
    """Check that flags in Arguments section are referenced in workflow body."""
    if not doc_flags:
        return None

    unreferenced = sorted(doc_flags - workflow_flags)
    if unreferenced:
        return CheckRecord(
            check=CHECK_DOC_WORKFLOW,
            passed=False,
            detail=(
                "Flags documented but not referenced in workflow: "
                f"{', '.join(unreferenced)}"
            ),
            tier="I22",
        )
    return CheckRecord(
        check=CHECK_DOC_WORKFLOW,
        passed=True,
        detail=f"All {len(doc_flags)} documented flags referenced in workflow",
        tier="I22",
    )


def _check_example_flags(
    doc_flags: set[str],
    example_flags: set[str],
) -> CheckRecord | None:
    """Check example section coverage against documented flags."""
    if not doc_flags:
        return None

    if len(doc_flags) < MIN_FLAGS_FOR_EXAMPLE_CHECK:
        return CheckRecord(
            check=CHECK_EXAMPLE_FLAGS,
            passed=True,
            detail=(
                "Example flag coverage check skipped - fewer than 3 documented "
                f"flags ({len(doc_flags)})"
            ),
            tier="I28",
        )

    covered_flags = doc_flags & example_flags
    coverage_ratio = len(covered_flags) / len(doc_flags)
    coverage_percent = round(coverage_ratio * 100)

    if coverage_ratio < EXAMPLE_COVERAGE_THRESHOLD:
        missing = ", ".join(sorted(doc_flags - example_flags))
        return CheckRecord(
            check=CHECK_EXAMPLE_FLAGS,
            passed=False,
            detail=(
                "Example invocations cover "
                f"{len(covered_flags)}/{len(doc_flags)} documented flags "
                f"({coverage_percent}%) - below 50% threshold; missing: {missing}"
            ),
            tier="I28",
        )

    return CheckRecord(
        check=CHECK_EXAMPLE_FLAGS,
        passed=True,
        detail=(
            "Example invocations cover "
            f"{len(covered_flags)}/{len(doc_flags)} documented flags "
            f"({coverage_percent}%)"
        ),
        tier="I28",
    )


CHECK_FUNCTIONS: Final[dict[str, Callable[..., CheckRecord | None]]] = {
    CHECK_HINT_DOC: _check_hint_doc,
    CHECK_DOC_HINT: _check_doc_hint,
    CHECK_DOC_WORKFLOW: _check_doc_workflow,
    CHECK_EXAMPLE_FLAGS: _check_example_flags,
}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    """Run flag coverage checks and return results in stable order."""
    body_lines = document.body.splitlines()
    fenced = build_fenced_line_indices(body_lines)

    hint_raw = document.field("argument-hint")
    hint_flags = _extract_flags(hint_raw)
    doc_flags = _get_arguments_section_flags(body_lines, fenced)
    workflow_flags = _get_workflow_flags(body_lines, fenced)
    example_flags = _get_examples_section_flags(body_lines, fenced)

    if not hint_flags and not doc_flags:
        return []

    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []

    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue

        if check_name == CHECK_HINT_DOC:
            result = _check_hint_doc(hint_flags, doc_flags)
        elif check_name == CHECK_DOC_HINT:
            result = _check_doc_hint(doc_flags, hint_flags, hint_raw)
        elif check_name == CHECK_DOC_WORKFLOW:
            result = _check_doc_workflow(doc_flags, workflow_flags)
        elif check_name == CHECK_EXAMPLE_FLAGS:
            result = _check_example_flags(doc_flags, example_flags)
        else:
            continue

        if result is not None:
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    return run_check_cli(
        "Verify flag documentation consistency in SKILL.md",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
