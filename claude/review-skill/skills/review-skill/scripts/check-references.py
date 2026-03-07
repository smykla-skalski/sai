#!/usr/bin/env python3
"""Validate SKILL.md body and references structure checks.

Implemented checks:
- `body-line-count`
- `body-char-count`
- `duplicate-codeblocks-info` (informational)
- `consistent-phase-numbering`
- `long-ref-toc`

Output is NDJSON with a final summary line.
Exit codes:
- 0 when all emitted checks pass
- 1 when one or more emitted checks fail
- 2 for usage/input errors
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    FENCE_RE,
    CheckResult,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    load_skill_document,
    read_text,
    strip_fenced_code_blocks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LINE_LIMIT: Final[int] = 500
CHAR_LIMIT: Final[int] = 20_000
MIN_DUPLICATE_BLOCK_LINES: Final[int] = 3
MIN_PHASE_COUNT: Final[int] = 2
LONG_REFERENCE_THRESHOLD: Final[int] = 100

CHECK_BODY_LINES: Final[str] = "body-line-count"
CHECK_BODY_CHARS: Final[str] = "body-char-count"
CHECK_DUP_CODEBLOCKS: Final[str] = "duplicate-codeblocks-info"
CHECK_PHASE_NUMBERING: Final[str] = "consistent-phase-numbering"
CHECK_LONG_REF_TOC: Final[str] = "long-ref-toc"

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

PHASE_NUMBER_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,4}\s+Phase\s+(\d+)",
    re.IGNORECASE,
)
TOC_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,2} (Contents|Table of Contents)",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_code_blocks(text: str) -> set[str]:
    """Return SHA256 hashes of fenced code blocks with 3+ lines."""
    hashes: set[str] = set()
    in_block = False
    block_lines: list[str] = []

    for line in text.splitlines():
        if FENCE_RE.match(line):
            if in_block:
                if len(block_lines) >= MIN_DUPLICATE_BLOCK_LINES:
                    normalized = "\n".join(block_lines)
                    digest = hashlib.sha256(
                        normalized.encode("utf-8"),
                    ).hexdigest()
                    hashes.add(digest)
                in_block = False
                block_lines = []
            else:
                in_block = True
                block_lines = []
            continue

        if in_block:
            block_lines.append(line.strip())

    return hashes


def _extract_phase_numbers(text: str) -> list[int]:
    """Extract sorted unique phase numbers from markdown headings."""
    phases: set[int] = set()

    for line in text.splitlines():
        match = PHASE_NUMBER_RE.search(line)
        if match:
            phases.add(int(match.group(1)))

    return sorted(phases)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def _check_body_line_count(document: SkillDocument) -> list[CheckResult]:
    """Check body line count against limit."""
    if document.body_start_line <= 1:
        return [
            CheckResult(
                check=CHECK_BODY_LINES,
                passed=False,
                detail="Could not locate frontmatter closing delimiter",
            ),
        ]

    total_lines = len(document.content.splitlines())
    body_lines = total_lines - (document.body_start_line - 1)

    return [
        CheckResult(
            check=CHECK_BODY_LINES,
            passed=body_lines <= LINE_LIMIT,
            detail=(
                f"SKILL.md body is {body_lines} lines (limit {LINE_LIMIT})"
                if body_lines <= LINE_LIMIT
                else (
                    f"SKILL.md body is {body_lines} lines, "
                    f"exceeds {LINE_LIMIT}-line limit"
                )
            ),
        ),
    ]


def _check_body_char_count(document: SkillDocument) -> list[CheckResult]:
    """Check body character count against limit."""
    if document.body_start_line <= 1:
        return []

    body_chars = len(document.body.encode("utf-8"))

    return [
        CheckResult(
            check=CHECK_BODY_CHARS,
            passed=body_chars <= CHAR_LIMIT,
            detail=(
                f"SKILL.md body is {body_chars} chars (limit {CHAR_LIMIT})"
                if body_chars <= CHAR_LIMIT
                else (
                    f"SKILL.md body is {body_chars} chars, "
                    f"exceeds {CHAR_LIMIT}-char limit (~5000 tokens)"
                )
            ),
        ),
    ]


def _check_duplicate_codeblocks(document: SkillDocument) -> list[CheckResult]:
    """Build informational result for shared code blocks."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    skill_hashes = _hash_code_blocks(document.body)
    duplicate_count = 0
    duplicate_refs: list[str] = []

    for reference_file in sorted(references_dir.glob("*.md")):
        if not reference_file.is_file():
            continue

        reference_hashes = _hash_code_blocks(read_text(reference_file))
        match_count = len(skill_hashes & reference_hashes)
        if match_count > 0:
            duplicate_count += match_count
            duplicate_refs.append(reference_file.name)

    if duplicate_refs:
        refs_joined = " ".join(duplicate_refs)
        detail = (
            f"INFO: {duplicate_count} code block(s) (3+ lines) shared "
            f"between SKILL.md and references: {refs_joined} - review whether "
            "each is intentional for progressive disclosure"
        )
    else:
        detail = "No shared code blocks between SKILL.md and references"

    return [
        CheckResult(
            check=CHECK_DUP_CODEBLOCKS,
            passed=True,
            detail=detail,
        ),
    ]


def _check_phase_numbering(document: SkillDocument) -> list[CheckResult]:
    """Build consistency results for phase numbering in references."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    skill_phases = _extract_phase_numbers(document.prose_body)
    if len(skill_phases) < MIN_PHASE_COUNT:
        return []

    results: list[CheckResult] = []
    skill_phase_set = set(skill_phases)

    for reference_file in sorted(references_dir.glob("*.md")):
        if not reference_file.is_file():
            continue

        reference_text = strip_fenced_code_blocks(read_text(reference_file))
        reference_phases = _extract_phase_numbers(reference_text)
        if len(reference_phases) < MIN_PHASE_COUNT:
            continue

        reference_phase_set = set(reference_phases)
        overlap_count = len(skill_phase_set & reference_phase_set)

        if overlap_count == 0:
            results.append(
                CheckResult(
                    check=CHECK_PHASE_NUMBERING,
                    passed=True,
                    detail=(
                        f"Phase ranges in '{reference_file.name}' and SKILL.md "
                        "are complementary (no overlap)"
                    ),
                ),
            )
            continue

        if skill_phases == reference_phases:
            results.append(
                CheckResult(
                    check=CHECK_PHASE_NUMBERING,
                    passed=True,
                    detail=f"Phase numbers in '{reference_file.name}' match SKILL.md",
                ),
            )
            continue

        skill_list = ",".join(str(value) for value in skill_phases)
        reference_list = ",".join(str(value) for value in reference_phases)
        results.append(
            CheckResult(
                check=CHECK_PHASE_NUMBERING,
                passed=False,
                detail=(
                    "Phase numbering mismatch: SKILL.md has "
                    f"[{skill_list}] but {reference_file.name} has "
                    f"[{reference_list}] (overlapping phases differ)"
                ),
            ),
        )

    return results


def _check_long_ref_toc(document: SkillDocument) -> list[CheckResult]:
    """Build checks for table of contents in long reference files."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    results: list[CheckResult] = []

    for reference_file in sorted(references_dir.glob("*.md")):
        if not reference_file.is_file():
            continue

        reference_text = read_text(reference_file)
        line_count = len(reference_text.splitlines())
        if line_count <= LONG_REFERENCE_THRESHOLD:
            continue

        has_toc = TOC_HEADING_RE.search(reference_text) is not None
        if has_toc:
            detail = (
                f"Reference '{reference_file.name}' ({line_count} lines) "
                "has table of contents"
            )
            passed = True
        else:
            detail = (
                f"Reference '{reference_file.name}' ({line_count} lines) "
                "exceeds 100 lines but has no '# Contents' "
                "or '# Table of Contents' heading"
            )
            passed = False

        results.append(
            CheckResult(check=CHECK_LONG_REF_TOC, passed=passed, detail=detail),
        )

    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_BODY_LINES,
    CHECK_BODY_CHARS,
    CHECK_DUP_CODEBLOCKS,
    CHECK_PHASE_NUMBERING,
    CHECK_LONG_REF_TOC,
)

CHECK_FUNCTIONS: Final[
    dict[str, Callable[[SkillDocument], list[CheckResult]]]
] = {
    CHECK_BODY_LINES: _check_body_line_count,
    CHECK_BODY_CHARS: _check_body_char_count,
    CHECK_DUP_CODEBLOCKS: _check_duplicate_codeblocks,
    CHECK_PHASE_NUMBERING: _check_phase_numbering,
    CHECK_LONG_REF_TOC: _check_long_ref_toc,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckResult]:
    """Run selected checks in stable output order."""
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
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate body and reference structure checks for SKILL.md",
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
    """Run the CLI entrypoint and return process exit code."""
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
