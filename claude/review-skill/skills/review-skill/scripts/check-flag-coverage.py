#!/usr/bin/env python3
"""Verify flag documentation consistency in SKILL.md.

Compares three zones where flags are declared:
  1. argument-hint frontmatter field (autocomplete hint)
  2. Arguments section in SKILL.md body (formal documentation)
  3. Workflow/body text outside Arguments and Examples (actual usage)

Sub-checks:
  - `FC-HINT-DOC`      - every --flag in argument-hint appears in Arguments section
  - `FC-DOC-HINT`      - every --flag in Arguments section appears in argument-hint
  - `FC-DOC-WORKFLOW`  - every --flag in Arguments section is
                          referenced in workflow body

Usage:
    ./check-flag-coverage.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes: 0 = all pass, 1 = any fail, 2 = usage error.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from skill_check_common import (
    EXIT_USAGE_ERROR,
    FENCE_RE,
    CheckResult,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_HINT_DOC: Final[str] = "FC-HINT-DOC"
CHECK_DOC_HINT: Final[str] = "FC-DOC-HINT"
CHECK_DOC_WORKFLOW: Final[str] = "FC-DOC-WORKFLOW"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_HINT_DOC,
    CHECK_DOC_HINT,
    CHECK_DOC_WORKFLOW,
)

# ---------------------------------------------------------------------------
# Flag extraction
# ---------------------------------------------------------------------------

FLAG_RE: Final[Pattern[str]] = re.compile(r"--[a-zA-Z][\w-]*")


def _extract_flags(text: str) -> set[str]:
    """Extract all --flag patterns from text."""
    return set(FLAG_RE.findall(text))


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------


def _build_fence_set(lines: list[str]) -> set[int]:
    """Return set of line indices that are inside fenced code blocks."""
    fenced: set[int] = set()
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced.add(i)
            in_fence = not in_fence
            continue
        if in_fence:
            fenced.add(i)
    return fenced


def _find_section(
    lines: list[str],
    pattern: str,
    fenced: set[int],
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
    fenced: set[int],
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
    fenced: set[int],
) -> set[str]:
    """Extract --flag patterns from the Arguments section."""
    start, end = _find_section(body_lines, r"\barguments\b", fenced)
    if start is None:
        return set()
    section_text = "\n".join(body_lines[start:end])
    return _extract_flags(section_text)


def _get_workflow_flags(
    body_lines: list[str],
    fenced: set[int],
) -> set[str]:
    """Extract --flag patterns from body excluding Arguments and Example sections."""
    args_start, args_end = _find_section(
        body_lines, r"\barguments\b", fenced,
    )

    exclude_ranges: list[tuple[int, int]] = []
    if args_start is not None and args_end is not None:
        exclude_ranges.append((args_start, args_end))

    for pattern in [r"\bexample\s+invocations?\b", r"\bexamples?\b"]:
        for s, e in _find_all_sections(body_lines, pattern, fenced):
            exclude_ranges.append((s, e))

    for s, e in _find_all_sections(
        body_lines, r"\bbundled\s+resources\b", fenced,
    ):
        exclude_ranges.append((s, e))

    workflow_lines: list[str] = []
    for i, line in enumerate(body_lines):
        excluded = any(rs <= i < re_ for rs, re_ in exclude_ranges)
        if not excluded:
            workflow_lines.append(line)

    return _extract_flags("\n".join(workflow_lines))


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def _check_hint_doc(
    hint_flags: set[str],
    doc_flags: set[str],
) -> CheckResult | None:
    """Check that flags in argument-hint appear in Arguments section."""
    if not hint_flags:
        return None

    if doc_flags:
        missing = sorted(hint_flags - doc_flags)
        if missing:
            return CheckResult(
                check=CHECK_HINT_DOC,
                passed=False,
                detail=(
                    "Flags in argument-hint not documented in Arguments section: "
                    f"{', '.join(missing)}"
                ),
            )
        return CheckResult(
            check=CHECK_HINT_DOC,
            passed=True,
            detail=f"All {len(hint_flags)} argument-hint flags documented",
        )

    return CheckResult(
        check=CHECK_HINT_DOC,
        passed=False,
        detail=(
            f"argument-hint has {len(hint_flags)} flags but no Arguments "
            "section found in body"
        ),
    )


def _check_doc_hint(
    doc_flags: set[str],
    hint_flags: set[str],
    hint_raw: str,
) -> CheckResult | None:
    """Check that flags in Arguments section appear in argument-hint."""
    if not doc_flags:
        return None

    if hint_flags:
        missing = sorted(doc_flags - hint_flags)
        if missing:
            return CheckResult(
                check=CHECK_DOC_HINT,
                passed=False,
                detail=(
                    "Flags in Arguments section missing from argument-hint: "
                    f"{', '.join(missing)}"
                ),
            )
        return CheckResult(
            check=CHECK_DOC_HINT,
            passed=True,
            detail=f"All {len(doc_flags)} documented flags in argument-hint",
        )

    if not hint_raw:
        return CheckResult(
            check=CHECK_DOC_HINT,
            passed=False,
            detail=(
                f"Arguments section documents {len(doc_flags)} flags but "
                "argument-hint field is missing from frontmatter"
            ),
        )

    return CheckResult(
        check=CHECK_DOC_HINT,
        passed=False,
        detail=(
            f"Arguments section documents {len(doc_flags)} flags but "
            f"argument-hint has none: {', '.join(sorted(doc_flags))}"
        ),
    )


def _check_doc_workflow(
    doc_flags: set[str],
    workflow_flags: set[str],
) -> CheckResult | None:
    """Check that flags in Arguments section are referenced in workflow body."""
    if not doc_flags:
        return None

    unreferenced = sorted(doc_flags - workflow_flags)
    if unreferenced:
        return CheckResult(
            check=CHECK_DOC_WORKFLOW,
            passed=False,
            detail=(
                "Flags documented but not referenced in workflow: "
                f"{', '.join(unreferenced)}"
            ),
        )
    return CheckResult(
        check=CHECK_DOC_WORKFLOW,
        passed=True,
        detail=f"All {len(doc_flags)} documented flags referenced in workflow",
    )


CHECK_FUNCTIONS: Final[
    dict[str, Callable[..., CheckResult | None]]
] = {
    CHECK_HINT_DOC: _check_hint_doc,
    CHECK_DOC_HINT: _check_doc_hint,
    CHECK_DOC_WORKFLOW: _check_doc_workflow,
}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckResult]:
    """Run flag coverage checks and return results in stable order."""
    body_lines = document.body.splitlines()
    fenced = _build_fence_set(body_lines)

    hint_raw = document.field("argument-hint")
    hint_flags = _extract_flags(hint_raw)
    doc_flags = _get_arguments_section_flags(body_lines, fenced)
    workflow_flags = _get_workflow_flags(body_lines, fenced)

    if not hint_flags and not doc_flags:
        return []

    selected = frozenset(selected_checks)
    results: list[CheckResult] = []

    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue

        if check_name == CHECK_HINT_DOC:
            result = _check_hint_doc(hint_flags, doc_flags)
        elif check_name == CHECK_DOC_HINT:
            result = _check_doc_hint(doc_flags, hint_flags, hint_raw)
        elif check_name == CHECK_DOC_WORKFLOW:
            result = _check_doc_workflow(doc_flags, workflow_flags)
        else:
            continue

        if result is not None:
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Verify flag documentation consistency in SKILL.md",
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
        help="Run only the specified check (repeatable)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
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
