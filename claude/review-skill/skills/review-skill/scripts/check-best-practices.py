#!/usr/bin/env python3
"""Validate best-practice coverage checks for SKILL.md and references.

Sub-checks:
  - `BP-example-tags`
  - `BP-over-prompting`
  - `BP-negative-instr-info`
  - `BP-error-section-info`
  - `BP-scope-boundary-info`
  - `BP-constraint-refresh-info`
  - `BP-section-order-info`
  - `BP-why-rationale-info`
  - `BP-example-diversity-info`
  - `BP-feedback-loop-info`
  - `BP-eval-dir-info`
  - `BP-unversioned-tools-info`

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
    ReferenceFile,
    SkillDocument,
    SkipConfig,
    build_fenced_line_indices,
    compile_patterns,
    format_hit,
    is_instructional_prose_line,
    iter_reference_inputs,
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
CHECK_SECTION_ORDER: Final[str] = "BP-section-order-info"
CHECK_WHY_RATIONALE: Final[str] = "BP-why-rationale-info"
CHECK_EXAMPLE_DIVERSITY: Final[str] = "BP-example-diversity-info"
CHECK_FEEDBACK_LOOP: Final[str] = "BP-feedback-loop-info"
CHECK_EVAL_DIR: Final[str] = "BP-eval-dir-info"
CHECK_UNVERSIONED_TOOLS: Final[str] = "BP-unversioned-tools-info"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_EXAMPLE_TAGS,
    CHECK_OVER_PROMPTING,
    CHECK_NEGATIVE_INSTR,
    CHECK_ERROR_SECTION,
    CHECK_SCOPE_BOUNDARY,
    CHECK_CONSTRAINT_REFRESH,
    CHECK_SECTION_ORDER,
    CHECK_WHY_RATIONALE,
    CHECK_EXAMPLE_DIVERSITY,
    CHECK_FEEDBACK_LOOP,
    CHECK_EVAL_DIR,
    CHECK_UNVERSIONED_TOOLS,
)

EXAMPLE_TAG_PASS_THRESHOLD: Final[int] = 3
OVER_PROMPT_FAIL_THRESHOLD: Final[int] = 2
PHASE_REFRESH_THRESHOLD: Final[int] = 4

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

EXAMPLE_OPEN_RE: Final[Pattern[str]] = re.compile(
    r"<example(?:\s[^>]*)?>",
    re.IGNORECASE,
)
EXAMPLE_CLOSE_RE: Final[Pattern[str]] = re.compile(r"</example>", re.IGNORECASE)
HEADING_RE: Final[Pattern[str]] = re.compile(r"^\s*#")

INLINE_CODE_RE: Final[Pattern[str]] = re.compile(r"`[^`]*`")
DOUBLE_QUOTED_RE: Final[Pattern[str]] = re.compile(r'"[^"]*"')
SINGLE_QUOTED_RE: Final[Pattern[str]] = re.compile(r"'[^']*'")

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

HEADING_H2_RE: Final[Pattern[str]] = re.compile(r"^##\s+(.*)")

MIN_CLASSIFIABLE_HEADINGS: Final[int] = 2

CANONICAL_SECTION_ORDER: Final[tuple[str, ...]] = (
    "overview",
    "arguments",
    "state",
    "workflow",
    "output",
    "errors",
    "examples",
)

CAUSAL_CONNECTOR_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bbecause\b",
        r"\bsince\b(?!\s+\d{4})(?!\s+last\b)",
        r"\bso\s+that\b",
        r"\bto\s+prevent\b",
        r"\bto\s+avoid\b",
        r"\bto\s+ensure\b",
        r"\botherwise\b",
        r"\bthis\s+(?:prevents|ensures|avoids)\b",
        r"\breason:",
    ),
)

WHY_RATIONALE_COVERAGE_THRESHOLD: Final[float] = 0.5

IO_PAIR_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"->",
        r"-->",
        r"\binput\s*:",
        r"\boutput\s*:",
        r"\bresult\s*:",
        r"\bbefore\s*:",
        r"\bafter\s*:",
        r"\bgiven\s*:",
        r"\bexpect\s*:",
    ),
)

VERIFICATION_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:verify|validate|check)\b.*\b(?:output|result|artifact|generated|quality)\b",
    re.IGNORECASE,
)

LOOP_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\b(?:loop|repeat|retry|re-run|iterate)\b",
        r"\bfix\s+and\s+re",
        r"\breturn\s+to\b",
        r"\bgo\s+back\b",
        r"\buntil\b.*\bpass\b",
    ),
)

VERIFICATION_WINDOW: Final[int] = 5

UNVERSIONED_TOOL_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:pip|pip3)\s+install\s+([a-zA-Z0-9_-]+)(?!\S*(?:==|>=|~=|@))",
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



def _strip_non_instruction_segments(line: str) -> str:
    """Remove inline-code and quoted snippets before over-prompting scans."""
    return SINGLE_QUOTED_RE.sub(
        "",
        DOUBLE_QUOTED_RE.sub("", INLINE_CODE_RE.sub("", line)),
    )


def _scan_over_prompting_text(
    text: str,
    *,
    body_start_line: int,
    source: str,
    extra_skip_indices: frozenset[int] = frozenset(),
) -> tuple[int, str | None]:
    """Count over-prompting hits and return first evidence for one source."""
    lines = text.splitlines()
    fenced_indices = build_fenced_line_indices(lines)
    example_indices = _build_example_line_indices(lines, fenced_indices)

    hit_count = 0
    first_evidence: str | None = None

    for index, line in enumerate(lines):
        if index in extra_skip_indices:
            continue
        if _is_ignored_line(
            index,
            line,
            fenced_indices=fenced_indices,
            example_indices=example_indices,
        ):
            continue

        sanitized = _strip_non_instruction_segments(line)
        line_hits = sum(
            len(pattern.findall(sanitized)) for pattern in OVER_PROMPT_PATTERNS
        )
        if line_hits == 0:
            continue

        hit_count += line_hits
        if first_evidence is None:
            first_evidence = (
                f"{source} {format_hit(index, line, body_start_line=body_start_line)}"
            )

    return hit_count, first_evidence


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
    """Detect aggressive emphasis in SKILL.md and referenced guidance files."""
    hit_count = 0
    first_evidence: str | None = None

    skill_hits, skill_evidence = _scan_over_prompting_text(
        document.body,
        body_start_line=document.body_start_line,
        source="SKILL.md",
    )
    hit_count += skill_hits
    if first_evidence is None and skill_evidence is not None:
        first_evidence = skill_evidence

    ref_files = iter_reference_inputs(
        document,
        skip=SkipConfig(fenced=False),
    )
    for ref in ref_files:
        referenced_hits, referenced_evidence = _scan_over_prompting_text(
            "\n".join(ref.lines),
            body_start_line=1,
            source=ref.rel_path,
            extra_skip_indices=ref.skip_indices,
        )
        hit_count += referenced_hits
        if first_evidence is None and referenced_evidence is not None:
            first_evidence = referenced_evidence

    scanned_detail = (
        f"scanned SKILL.md and {len(ref_files)} referenced text file(s)"
    )

    if hit_count >= OVER_PROMPT_FAIL_THRESHOLD:
        return CheckRecord.fail(
            CHECK_OVER_PROMPTING,
            (
                f"Detected {hit_count} aggressive emphasis pattern hit(s) "
                "outside headings/examples (threshold 2) - first: "
                f"{first_evidence} ({scanned_detail})"
            ),
            tier="I27",
        )

    if hit_count > 0:
        return CheckRecord.info(
            CHECK_OVER_PROMPTING,
            (
                f"Detected {hit_count} aggressive emphasis pattern hit(s) "
                "outside headings/examples (below fail threshold of 2) - first: "
                f"{first_evidence} ({scanned_detail})"
            ),
            tier="I27",
        )

    return CheckRecord.ok(
        CHECK_OVER_PROMPTING,
        (
            "No aggressive emphasis patterns detected outside "
            f"headings/examples ({scanned_detail})"
        ),
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
                index,
                line,
                body_start_line=document.body_start_line,
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


def _extract_example_contents(
    lines: list[str],
    fenced_indices: frozenset[int],
) -> list[str]:
    """Extract text content between <example>...</example> tags.

    Supports both multiline blocks and inline one-line tags.
    """
    examples: list[str] = []
    current: list[str] = []
    in_example = False

    for index, line in enumerate(lines):
        if index in fenced_indices:
            continue

        if in_example and not line:
            current.append("")
            continue

        cursor = 0
        while cursor < len(line):
            if in_example:
                close_match = EXAMPLE_CLOSE_RE.search(line, cursor)
                if close_match is None:
                    current.append(line[cursor:])
                    break

                current.append(line[cursor : close_match.start()])
                examples.append("\n".join(current))
                current = []
                in_example = False
                cursor = close_match.end()
                continue

            open_match = EXAMPLE_OPEN_RE.search(line, cursor)
            if open_match is None:
                break

            in_example = True
            current = []
            cursor = open_match.end()

            close_match = EXAMPLE_CLOSE_RE.search(line, cursor)
            if close_match is None:
                if cursor < len(line):
                    current.append(line[cursor:])
                break

            current.append(line[cursor : close_match.start()])
            examples.append("\n".join(current))
            current = []
            in_example = False
            cursor = close_match.end()

    return examples


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: strip, lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _count_reference_constraints_with_rationale(
    ref_inputs: tuple[ReferenceFile, ...],
    constraint_patterns: tuple[Pattern[str], ...],
) -> tuple[int, int]:
    """Return (constraints, with_rationale) from referenced guidance files."""
    total_constraints = 0
    total_with_rationale = 0

    for ref in ref_inputs:
        for index, line in enumerate(ref.lines):
            if index in ref.skip_indices:
                continue
            if not is_instructional_prose_line(line):
                continue
            if not any(pattern.search(line) for pattern in constraint_patterns):
                continue

            total_constraints += 1
            ref_window_lines = [
                ref.lines[j]
                for j in range(index, min(index + 3, len(ref.lines)))
                if j not in ref.skip_indices
            ]
            ref_window_text = " ".join(ref_window_lines)
            if any(
                pattern.search(ref_window_text) for pattern in CAUSAL_CONNECTOR_PATTERNS
            ):
                total_with_rationale += 1

    return total_constraints, total_with_rationale


def _count_reference_verification_loops(
    ref_inputs: tuple[ReferenceFile, ...],
) -> tuple[int, int]:
    """Return (verification_steps, with_loop) from referenced guidance files."""
    total_verify_steps = 0
    total_with_loop = 0

    for ref in ref_inputs:
        for index, line in enumerate(ref.lines):
            if index in ref.skip_indices:
                continue
            if not is_instructional_prose_line(line):
                continue
            if VERIFICATION_RE.search(line) is None:
                continue

            total_verify_steps += 1
            start = max(0, index - VERIFICATION_WINDOW)
            end = min(len(ref.lines), index + VERIFICATION_WINDOW + 1)
            ref_window_text = " ".join(
                ref.lines[j]
                for j in range(start, end)
                if j not in ref.skip_indices
            )
            if any(pattern.search(ref_window_text) for pattern in LOOP_PATTERNS):
                total_with_loop += 1

    return total_verify_steps, total_with_loop


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_HEADING_CLASSIFIERS: Final[tuple[tuple[Pattern[str], str], ...]] = (
    (re.compile(r"\bargument", re.IGNORECASE), "arguments"),
    (re.compile(r"\b(?:error|failure|troubleshoot)", re.IGNORECASE), "errors"),
    (re.compile(r"\b(?:workflow|phase|step)\b", re.IGNORECASE), "workflow"),
    (re.compile(r"\b(?:example|invocation|usage)\b", re.IGNORECASE), "examples"),
    (re.compile(r"\b(?:output|format|result)\b", re.IGNORECASE), "output"),
    (re.compile(r"\b(?:state|persist|storage)\b", re.IGNORECASE), "state"),
)


def _classify_heading(text: str, *, is_first: bool) -> str | None:
    """Classify an H2 heading text into a canonical section category."""
    for pattern, category in _HEADING_CLASSIFIERS:
        if pattern.search(text):
            return category
    if is_first:
        return "overview"
    return None


def check_section_order_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal when body sections deviate from canonical order."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)

    classified: list[str] = []
    first_seen = False
    for index, line in enumerate(lines):
        if index in fenced_indices:
            continue
        match = HEADING_H2_RE.match(line)
        if match is None:
            continue
        category = _classify_heading(match.group(1), is_first=not first_seen)
        first_seen = True
        if category is not None:
            classified.append(category)

    if len(classified) < MIN_CLASSIFIABLE_HEADINGS:
        return CheckRecord.skip(
            CHECK_SECTION_ORDER,
            (
                "Section order check skipped - fewer than 2 classifiable "
                f"H2 headings ({len(classified)})"
            ),
            tier="P17",
        )

    canonical_indices = [CANONICAL_SECTION_ORDER.index(cat) for cat in classified]
    inversions = [
        f"{classified[i]} > {classified[i + 1]}"
        for i in range(len(canonical_indices) - 1)
        if canonical_indices[i] > canonical_indices[i + 1]
    ]

    if inversions:
        return CheckRecord.info(
            CHECK_SECTION_ORDER,
            f"{len(inversions)} section order inversion(s): {', '.join(inversions)}",
            tier="P17",
        )

    return CheckRecord.ok(
        CHECK_SECTION_ORDER,
        f"Body section order follows canonical flow ({len(classified)} sections)",
        tier="P17",
    )


def check_why_rationale_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal when constraints lack WHY rationale."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)
    example_indices = _build_example_line_indices(lines, fenced_indices)

    all_constraint_patterns = OVER_PROMPT_PATTERNS + NEGATIVE_INSTR_PATTERNS
    constraint_indices: list[int] = []
    for index, line in enumerate(lines):
        if _is_ignored_line(
            index,
            line,
            fenced_indices=fenced_indices,
            example_indices=example_indices,
        ):
            continue
        if any(p.search(line) for p in all_constraint_patterns):
            constraint_indices.append(index)

    with_rationale = 0
    for ci in constraint_indices:
        window_lines = [
            lines[j]
            for j in range(ci, min(ci + 3, len(lines)))
            if j not in fenced_indices
        ]
        window_text = " ".join(window_lines)
        if any(p.search(window_text) for p in CAUSAL_CONNECTOR_PATTERNS):
            with_rationale += 1

    ref_inputs = iter_reference_inputs(document)
    reference_constraints, reference_with_rationale = (
        _count_reference_constraints_with_rationale(ref_inputs, all_constraint_patterns)
    )
    with_rationale += reference_with_rationale

    total = len(constraint_indices) + reference_constraints
    if total == 0:
        return CheckRecord.skip(
            CHECK_WHY_RATIONALE,
            "WHY rationale check skipped - no constraint patterns found",
            tier="I29",
        )

    ratio = with_rationale / total if total > 0 else 0.0

    if ratio >= WHY_RATIONALE_COVERAGE_THRESHOLD:
        return CheckRecord.ok(
            CHECK_WHY_RATIONALE,
            f"{with_rationale} of {total} constraint(s) have WHY rationale",
            tier="I29",
        )

    return CheckRecord.info(
        CHECK_WHY_RATIONALE,
        (
            f"{with_rationale} of {total} constraint(s) have WHY rationale "
            "- add because/so that/to prevent for non-obvious rules"
        ),
        tier="I29",
    )


def check_example_diversity_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal when examples lack I/O pairs or are identical."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)
    examples = _extract_example_contents(lines, fenced_indices)

    if not examples:
        return CheckRecord.skip(
            CHECK_EXAMPLE_DIVERSITY,
            "Example diversity check skipped - no <example> tags found",
            tier="I3",
        )

    has_io_pair = any(any(p.search(ex) for p in IO_PAIR_PATTERNS) for ex in examples)
    normalized = [_normalize_text(ex) for ex in examples]
    all_identical = len(set(normalized)) == 1 and len(normalized) > 1

    findings: list[str] = []
    if not has_io_pair:
        findings.append("no I/O pairs found")
    if all_identical:
        findings.append(f"{len(normalized)} identical examples")

    if findings:
        return CheckRecord.info(
            CHECK_EXAMPLE_DIVERSITY,
            f"Example diversity signal: {', '.join(findings)}",
            tier="I3",
        )

    return CheckRecord.ok(
        CHECK_EXAMPLE_DIVERSITY,
        f"Examples are diverse ({len(examples)} example(s) with I/O pairs)",
        tier="I3",
    )


def check_feedback_loop_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal when verify steps lack loop language."""
    lines = document.body.splitlines()
    fenced_indices = build_fenced_line_indices(lines)

    verify_indices: list[int] = []
    for index, line in enumerate(lines):
        if index in fenced_indices:
            continue
        if VERIFICATION_RE.search(line):
            verify_indices.append(index)

    with_loop = 0
    for vi in verify_indices:
        start = max(0, vi - VERIFICATION_WINDOW)
        end = min(len(lines), vi + VERIFICATION_WINDOW + 1)
        window_text = " ".join(lines[start:end])
        if any(p.search(window_text) for p in LOOP_PATTERNS):
            with_loop += 1

    ref_inputs = iter_reference_inputs(document)
    reference_verify_steps, reference_with_loop = _count_reference_verification_loops(
        ref_inputs,
    )
    with_loop += reference_with_loop

    total = len(verify_indices) + reference_verify_steps
    if total == 0:
        return CheckRecord.skip(
            CHECK_FEEDBACK_LOOP,
            "Feedback loop check skipped - no verification steps found",
            tier="I8",
        )

    if with_loop > 0:
        return CheckRecord.ok(
            CHECK_FEEDBACK_LOOP,
            (f"{with_loop} of {total} verification step(s) have loop/retry language"),
            tier="I8",
        )

    return CheckRecord.info(
        CHECK_FEEDBACK_LOOP,
        (
            f"{total} verification step(s) found but none have "
            "loop/retry language - add retry/repeat/fix-and-rerun"
        ),
        tier="I8",
    )


def check_eval_dir_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for evals directory presence."""
    evals_dir = document.skill_dir / "evals"
    if evals_dir.is_dir() and any(evals_dir.iterdir()):
        return CheckRecord.ok(
            CHECK_EVAL_DIR,
            "Evals directory found with content",
            tier="P20",
        )

    return CheckRecord.info(
        CHECK_EVAL_DIR,
        "No evals/ directory detected",
        tier="P20",
    )


def check_unversioned_tools_info(document: SkillDocument) -> CheckRecord:
    """Emit informational signal for unversioned tool install references in prose."""
    match = UNVERSIONED_TOOL_RE.search(document.prose_body)
    if match:
        return CheckRecord.info(
            CHECK_UNVERSIONED_TOOLS,
            (
                f"Unversioned tool install detected in prose: {match.group(0).strip()} "
                "- consider pinning a version"
            ),
            tier="P21",
        )

    return CheckRecord.ok(
        CHECK_UNVERSIONED_TOOLS,
        "No unversioned tool install references detected in prose",
        tier="P21",
    )


# ---------------------------------------------------------------------------
# Orchestration (below new checks)
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], CheckRecord]]] = {
    CHECK_EXAMPLE_TAGS: check_example_tags,
    CHECK_OVER_PROMPTING: check_over_prompting,
    CHECK_NEGATIVE_INSTR: check_negative_instruction_info,
    CHECK_ERROR_SECTION: check_error_section_info,
    CHECK_SCOPE_BOUNDARY: check_scope_boundary_info,
    CHECK_CONSTRAINT_REFRESH: check_constraint_refresh_info,
    CHECK_SECTION_ORDER: check_section_order_info,
    CHECK_WHY_RATIONALE: check_why_rationale_info,
    CHECK_EXAMPLE_DIVERSITY: check_example_diversity_info,
    CHECK_FEEDBACK_LOOP: check_feedback_loop_info,
    CHECK_EVAL_DIR: check_eval_dir_info,
    CHECK_UNVERSIONED_TOOLS: check_unversioned_tools_info,
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
