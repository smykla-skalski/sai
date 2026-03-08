#!/usr/bin/env python3
"""Validate SKILL.md body and references structure checks.

Implemented checks:
- `RF-body-lines`
- `RF-body-chars`
- `RF-dup-codeblocks-info` (informational)
- `RF-dup-tables-info` (informational)
- `RF-phase-numbering`
- `RF-long-ref-toc`
- `RF-dup-prose-info` (informational)

Output is NDJSON with a final summary line.
Exit codes:
- 0 when all emitted checks pass
- 1 when one or more emitted checks fail
- 2 for usage/input errors
"""

from __future__ import annotations

import hashlib
import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    FENCE_RE,
    CheckRecord,
    SkillDocument,
    read_text,
    run_check_cli,
    strip_fenced_code_blocks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LINE_LIMIT: Final[int] = 500
CHAR_LIMIT: Final[int] = 20_000
MIN_DUPLICATE_CONTENT_LINES: Final[int] = 3
MIN_PHASE_COUNT: Final[int] = 2
LONG_REFERENCE_THRESHOLD: Final[int] = 100

CHECK_BODY_LINES: Final[str] = "RF-body-lines"
CHECK_BODY_CHARS: Final[str] = "RF-body-chars"
CHECK_DUP_CODEBLOCKS: Final[str] = "RF-dup-codeblocks-info"
CHECK_DUP_TABLES: Final[str] = "RF-dup-tables-info"
CHECK_PHASE_NUMBERING: Final[str] = "RF-phase-numbering"
CHECK_LONG_REF_TOC: Final[str] = "RF-long-ref-toc"
CHECK_DUP_PROSE: Final[str] = "RF-dup-prose-info"
DUP_PROSE_JACCARD_THRESHOLD: Final[float] = 0.35
MIN_PROSE_PARAGRAPH_SENTENCES: Final[int] = 2

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

PHASE_NUMBER_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,4}\s+Phase\s+(\d+)",
    re.IGNORECASE,
)
TOC_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,3} (Contents|Table of Contents)",
    re.MULTILINE | re.IGNORECASE,
)
TABLE_ROW_RE: Final[Pattern[str]] = re.compile(r"^\s*\|")
HEADING_LINE_RE: Final[Pattern[str]] = re.compile(r"^\s*#")
SENTENCE_END_RE: Final[Pattern[str]] = re.compile(r"[.!?]")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _digest_block(lines: list[str], min_lines: int) -> str | None:
    """Return SHA256 digest if lines meet minimum threshold, else None."""
    if len(lines) < min_lines:
        return None
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _hash_code_blocks(text: str) -> set[str]:
    """Return SHA256 hashes of fenced code blocks with 3+ lines."""
    hashes: set[str] = set()
    in_block = False
    block_lines: list[str] = []

    for line in text.splitlines():
        if FENCE_RE.match(line):
            if in_block:
                digest = _digest_block(block_lines, MIN_DUPLICATE_CONTENT_LINES)
                if digest:
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


def _hash_markdown_tables(text: str) -> set[str]:
    """Return SHA256 hashes of markdown tables with 3+ consecutive rows."""
    hashes: set[str] = set()
    table_lines: list[str] = []
    in_fence = False

    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            digest = _digest_block(table_lines, MIN_DUPLICATE_CONTENT_LINES)
            if digest:
                hashes.add(digest)
            table_lines = []
            continue

        if in_fence:
            continue

        if TABLE_ROW_RE.match(line):
            table_lines.append(line.strip())
            continue

        digest = _digest_block(table_lines, MIN_DUPLICATE_CONTENT_LINES)
        if digest:
            hashes.add(digest)
        table_lines = []

    digest = _digest_block(table_lines, MIN_DUPLICATE_CONTENT_LINES)
    if digest:
        hashes.add(digest)

    return hashes


def _extract_prose_paragraphs(text: str) -> list[str]:
    """Extract normalized prose paragraphs with 2+ sentences.

    Strips fenced code blocks and table rows. Groups consecutive non-empty,
    non-heading lines into paragraphs. Normalizes: lowercase, collapse
    whitespace.
    """
    stripped = strip_fenced_code_blocks(text)
    paragraphs: list[str] = []
    current: list[str] = []

    for line in stripped.splitlines():
        trimmed = line.strip()
        if not trimmed or HEADING_LINE_RE.match(trimmed) or TABLE_ROW_RE.match(trimmed):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(trimmed)

    if current:
        paragraphs.append(" ".join(current))

    result: list[str] = []
    for para in paragraphs:
        sentence_count = len(SENTENCE_END_RE.findall(para))
        if sentence_count >= MIN_PROSE_PARAGRAPH_SENTENCES:
            result.append(re.sub(r"\s+", " ", para.lower().strip()))

    return result


def _char_ngram_jaccard(a: str, b: str, n: int = 4) -> float:
    """Compute character n-gram Jaccard similarity between two strings."""
    if len(a) < n and len(b) < n:
        return 0.0
    set_a = {a[i : i + n] for i in range(len(a) - n + 1)}
    set_b = {b[i : i + n] for i in range(len(b) - n + 1)}
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def _check_body_line_count(document: SkillDocument) -> list[CheckRecord]:
    """Check body line count against limit."""
    if document.body_start_line <= 1:
        return [
            CheckRecord(
                check=CHECK_BODY_LINES,
                passed=False,
                detail="Could not locate frontmatter closing delimiter",
                tier="C2",
            ),
        ]

    total_lines = len(document.content.splitlines())
    body_lines = total_lines - (document.body_start_line - 1)

    return [
        CheckRecord(
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
            tier="C2",
        ),
    ]


def _check_body_char_count(document: SkillDocument) -> list[CheckRecord]:
    """Check body character count against limit."""
    if document.body_start_line <= 1:
        return []

    body_chars = len(document.body.encode("utf-8"))

    return [
        CheckRecord(
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
            tier="I24",
        ),
    ]


def _check_duplicate_codeblocks(document: SkillDocument) -> list[CheckRecord]:
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
        return [
            CheckRecord.info(
                CHECK_DUP_CODEBLOCKS,
                (
                    f"{duplicate_count} code block(s) (3+ lines) shared "
                    f"between SKILL.md and references: {refs_joined} - review "
                    "whether each is intentional for progressive disclosure"
                ),
                tier="P8",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_DUP_CODEBLOCKS,
            passed=True,
            detail="No shared code blocks between SKILL.md and references",
            tier="P8",
        ),
    ]


def _check_duplicate_tables(document: SkillDocument) -> list[CheckRecord]:
    """Build informational result for shared markdown tables."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    skill_hashes = _hash_markdown_tables(document.body)
    duplicate_count = 0
    duplicate_refs: list[str] = []

    for reference_file in sorted(references_dir.glob("*.md")):
        if not reference_file.is_file():
            continue

        reference_hashes = _hash_markdown_tables(read_text(reference_file))
        match_count = len(skill_hashes & reference_hashes)
        if match_count > 0:
            duplicate_count += match_count
            duplicate_refs.append(reference_file.name)

    if duplicate_refs:
        refs_joined = " ".join(duplicate_refs)
        return [
            CheckRecord.info(
                CHECK_DUP_TABLES,
                (
                    f"{duplicate_count} markdown table(s) (3+ rows) shared "
                    f"between SKILL.md and references: {refs_joined} - review "
                    "whether duplication is intentional"
                ),
                tier="P15",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_DUP_TABLES,
            passed=True,
            detail="No shared markdown tables between SKILL.md and references",
            tier="P15",
        ),
    ]


def _check_phase_numbering(document: SkillDocument) -> list[CheckRecord]:
    """Build consistency results for phase numbering in references."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    skill_phases = _extract_phase_numbers(document.prose_body)
    if len(skill_phases) < MIN_PHASE_COUNT:
        return []

    results: list[CheckRecord] = []
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
                CheckRecord(
                    check=CHECK_PHASE_NUMBERING,
                    passed=True,
                    detail=(
                        f"Phase ranges in '{reference_file.name}' and SKILL.md "
                        "are complementary (no overlap)"
                    ),
                    tier="I14",
                ),
            )
            continue

        if skill_phases == reference_phases:
            results.append(
                CheckRecord(
                    check=CHECK_PHASE_NUMBERING,
                    passed=True,
                    detail=f"Phase numbers in '{reference_file.name}' match SKILL.md",
                    tier="I14",
                ),
            )
            continue

        skill_list = ",".join(str(value) for value in skill_phases)
        reference_list = ",".join(str(value) for value in reference_phases)
        results.append(
            CheckRecord(
                check=CHECK_PHASE_NUMBERING,
                passed=False,
                detail=(
                    "Phase numbering mismatch: SKILL.md has "
                    f"[{skill_list}] but {reference_file.name} has "
                    f"[{reference_list}] (overlapping phases differ)"
                ),
                tier="I14",
            ),
        )

    return results


def _check_long_ref_toc(document: SkillDocument) -> list[CheckRecord]:
    """Build checks for table of contents in long reference files."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    results: list[CheckRecord] = []

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
            CheckRecord(
                check=CHECK_LONG_REF_TOC,
                passed=passed,
                detail=detail,
                tier="P1",
            ),
        )

    return results


def _check_dup_prose(document: SkillDocument) -> list[CheckRecord]:
    """Build informational result for similar prose between SKILL.md and references."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    skill_paragraphs = _extract_prose_paragraphs(document.body)
    if not skill_paragraphs:
        return []

    similar_pairs: list[str] = []

    for reference_file in sorted(references_dir.glob("*.md")):
        if not reference_file.is_file():
            continue

        ref_paragraphs = _extract_prose_paragraphs(read_text(reference_file))
        for sp in skill_paragraphs:
            for rp in ref_paragraphs:
                if _char_ngram_jaccard(sp, rp) >= DUP_PROSE_JACCARD_THRESHOLD:
                    similar_pairs.append(reference_file.name)
                    break
            if similar_pairs and similar_pairs[-1] == reference_file.name:
                break

    if similar_pairs:
        refs_joined = " ".join(similar_pairs)
        return [
            CheckRecord.info(
                CHECK_DUP_PROSE,
                (
                    f"Similar prose paragraph(s) found between SKILL.md and "
                    f"references: {refs_joined} - review for unnecessary "
                    "duplication"
                ),
                tier="I4",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_DUP_PROSE,
            passed=True,
            detail="No similar prose paragraphs between SKILL.md and references",
            tier="I4",
        ),
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_BODY_LINES,
    CHECK_BODY_CHARS,
    CHECK_DUP_CODEBLOCKS,
    CHECK_DUP_TABLES,
    CHECK_PHASE_NUMBERING,
    CHECK_LONG_REF_TOC,
    CHECK_DUP_PROSE,
)

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], list[CheckRecord]]]] = {
    CHECK_BODY_LINES: _check_body_line_count,
    CHECK_BODY_CHARS: _check_body_char_count,
    CHECK_DUP_CODEBLOCKS: _check_duplicate_codeblocks,
    CHECK_DUP_TABLES: _check_duplicate_tables,
    CHECK_PHASE_NUMBERING: _check_phase_numbering,
    CHECK_LONG_REF_TOC: _check_long_ref_toc,
    CHECK_DUP_PROSE: _check_dup_prose,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    """Run selected checks in stable output order."""
    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []
    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        results.extend(CHECK_FUNCTIONS[check_name](document))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and return process exit code."""
    return run_check_cli(
        "Validate body and reference structure checks for SKILL.md",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
