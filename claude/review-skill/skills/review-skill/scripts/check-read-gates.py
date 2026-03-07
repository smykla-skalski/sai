#!/usr/bin/env python3
"""Validate reference file read gates in SKILL.md.

Sub-checks:
- `RG-gate-present` - every linked ref has an explicit load directive
- `RG-passive` - no passive weak mentions before gates
- `RG-orphan` - no disk files missing from SKILL.md
- `RG-dead` - no refs listed only in bundled section
- `RG-use-order` - no ref cited before its gate appears
- `RG-purpose` - read gates explain why (not bare path-only)
- `RG-flow` - multi-flow skills gate refs in each flow

Output format is NDJSON, ending with a summary line that includes
a `refs` count for compatibility with orchestration guards.

Exit codes:
- 0 when all emitted checks pass (or no refs found)
- 1 when one or more checks fail
- 2 for CLI usage/input errors
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

from _skill_check_common import (
    CheckRecord,
    ProseLine,
    SkillDocument,
    extract_prose_lines,
    find_bundled_indices,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_GATE: Final[str] = "RG-gate-present"
CHECK_PASSIVE: Final[str] = "RG-passive"
CHECK_ORPHAN: Final[str] = "RG-orphan"
CHECK_DEAD: Final[str] = "RG-dead"
CHECK_USE_ORDER: Final[str] = "RG-use-order"
CHECK_PURPOSE: Final[str] = "RG-purpose"
CHECK_FLOW: Final[str] = "RG-flow"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_GATE,
    CHECK_PASSIVE,
    CHECK_ORPHAN,
    CHECK_DEAD,
    CHECK_USE_ORDER,
    CHECK_PURPOSE,
    CHECK_FLOW,
)

# ---------------------------------------------------------------------------
# Named constants (PLR2004)
# ---------------------------------------------------------------------------

MIN_MULTI_FLOW_HEADERS: Final[int] = 2
MIN_FLOW_MENTIONS: Final[int] = 2
REF_SUBDIRECTORIES: Final[tuple[str, ...]] = ("references", "examples")
_END_SENTINEL: Final[int] = 999_999

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

MARKDOWN_LINK_REF_RE: Final[Pattern[str]] = re.compile(
    r"\((?:references|examples)/[a-zA-Z0-9._-]+\.md\)",
)

GATE_DIRECTIVE_RE: Final[Pattern[str]] = re.compile(
    r"(Read|Contents\s+of|path\s+to|Load)\s",
    re.IGNORECASE,
)

PASSIVE_MENTION_RE: Final[Pattern[str]] = re.compile(
    r"\b(See|are\s+in|is\s+in|Consult|per|available\s+in"
    r"|described\s+in|defined\s+in|documented\s+in)\b",
    re.IGNORECASE,
)

PASSIVE_FROM_RE: Final[Pattern[str]] = re.compile(
    r"\bfrom\b",
    re.IGNORECASE,
)

CONTENTS_FROM_RE: Final[Pattern[str]] = re.compile(
    r"Contents\s+from",
    re.IGNORECASE,
)

PURPOSE_TRAILING_RE: Final[Pattern[str]] = re.compile(
    r"(for |before |in full|when |,\s+then |to understand|to learn)",
    re.IGNORECASE,
)

WORKFLOW_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^##\s+.*workflow",
    re.IGNORECASE,
)

MODE_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^#{2,}\s+.*(mode|alternative|fallback)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RefInventory:
    """Store the union of linked and on-disk reference files."""

    linked_refs: frozenset[str]
    disk_refs: frozenset[str]
    all_refs: frozenset[str]
    count: int


@dataclass(frozen=True)
class RefAnalysis:
    """Store per-reference analysis results."""

    ref: str
    gate_index: int | None
    passive_before_gate: tuple[int, ...]
    use_indices: tuple[int, ...]
    in_full_content: bool


@dataclass(frozen=True)
class FlowSection:
    """Store one workflow flow section range."""

    start_index: int
    end_index: int
    header_text: str


# ---------------------------------------------------------------------------
# Inventory functions
# ---------------------------------------------------------------------------


def _collect_disk_refs(skill_dir: Path) -> frozenset[str]:
    """Scan references/ and examples/ for .md files on disk."""
    refs: set[str] = set()
    for subdir in REF_SUBDIRECTORIES:
        subdir_path = skill_dir / subdir
        if not subdir_path.is_dir():
            continue
        for path in subdir_path.iterdir():
            if path.is_file() and path.suffix == ".md":
                refs.add(f"{subdir}/{path.name}")
    return frozenset(refs)


def _extract_linked_refs(prose_body: str) -> frozenset[str]:
    """Extract reference paths from markdown links in prose body."""
    matches = MARKDOWN_LINK_REF_RE.findall(prose_body)
    return frozenset(match[1:-1] for match in matches)


def _build_inventory(document: SkillDocument) -> RefInventory:
    """Build the full reference inventory from document."""
    linked = _extract_linked_refs(document.prose_body)
    disk = _collect_disk_refs(document.skill_dir)
    all_refs = linked | disk
    return RefInventory(
        linked_refs=linked,
        disk_refs=disk,
        all_refs=all_refs,
        count=len(all_refs),
    )


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------


def _is_gate_line(text: str, ref: str) -> bool:
    """Return whether the line is a gate directive mentioning ref."""
    if ref.lower() not in text.lower():
        return False
    return GATE_DIRECTIVE_RE.search(text) is not None


def _is_passive_mention(text: str, ref: str) -> bool:
    """Return whether the line is a passive (non-gate) mention of ref."""
    if ref.lower() not in text.lower():
        return False
    if _is_gate_line(text, ref):
        return False
    if PASSIVE_MENTION_RE.search(text):
        return True
    return bool(
        PASSIVE_FROM_RE.search(text) and not CONTENTS_FROM_RE.search(text),
    )


def _find_gate_index(
    prose_lines: tuple[ProseLine, ...],
    ref: str,
) -> int | None:
    """Return the index of the first gate line for ref, or None."""
    for line in prose_lines:
        if _is_gate_line(line.text, ref):
            return line.index
    return None


def _find_passive_before_gate(
    prose_lines: tuple[ProseLine, ...],
    ref: str,
    gate_index: int | None,
    bundled_indices: frozenset[int],
) -> tuple[int, ...]:
    """Return indices of passive mentions before the gate."""
    result: list[int] = []
    for line in prose_lines:
        if line.index in bundled_indices:
            continue
        if gate_index is not None and line.index >= gate_index:
            break
        if _is_passive_mention(line.text, ref):
            result.append(line.index)
    return tuple(result)


def _find_use_indices(
    prose_lines: tuple[ProseLine, ...],
    ref: str,
    bundled_indices: frozenset[int],
) -> tuple[int, ...]:
    """Return indices of non-gate, non-bundled mentions of ref."""
    result: list[int] = []
    for line in prose_lines:
        if line.index in bundled_indices:
            continue
        if ref.lower() not in line.text.lower():
            continue
        if _is_gate_line(line.text, ref):
            continue
        result.append(line.index)
    return tuple(result)


def _analyze_ref(
    ref: str,
    prose_lines: tuple[ProseLine, ...],
    bundled_indices: frozenset[int],
    full_content: str,
) -> RefAnalysis:
    """Build per-ref analysis combining gate, passive, and use data."""
    gate_index = _find_gate_index(prose_lines, ref)
    return RefAnalysis(
        ref=ref,
        gate_index=gate_index,
        passive_before_gate=_find_passive_before_gate(
            prose_lines,
            ref,
            gate_index,
            bundled_indices,
        ),
        use_indices=_find_use_indices(prose_lines, ref, bundled_indices),
        in_full_content=ref.lower() in full_content.lower(),
    )


# ---------------------------------------------------------------------------
# Flow detection
# ---------------------------------------------------------------------------


def _is_multi_flow(prose_lines: tuple[ProseLine, ...]) -> bool:
    """Return whether the skill has multiple workflow flows."""
    workflow_count = sum(
        1 for line in prose_lines if WORKFLOW_HEADING_RE.match(line.text)
    )
    if workflow_count >= MIN_MULTI_FLOW_HEADERS:
        return True
    return any(MODE_HEADING_RE.match(line.text) for line in prose_lines)


def _detect_flow_sections(
    prose_lines: tuple[ProseLine, ...],
) -> tuple[FlowSection, ...]:
    """Build FlowSection entries for multi-flow skills."""
    headers = [
        (line.index, line.text)
        for line in prose_lines
        if WORKFLOW_HEADING_RE.match(line.text)
    ]

    if len(headers) < MIN_MULTI_FLOW_HEADERS:
        return ()

    sections: list[FlowSection] = []
    for i, (start_idx, header_text) in enumerate(headers):
        end_idx = headers[i + 1][0] if i + 1 < len(headers) else _END_SENTINEL
        sections.append(
            FlowSection(
                start_index=start_idx,
                end_index=end_idx,
                header_text=header_text,
            ),
        )

    return tuple(sections)


# ---------------------------------------------------------------------------
# Purpose helper
# ---------------------------------------------------------------------------


def _gate_has_purpose(gate_text: str, ref: str) -> bool:
    """Return whether the gate line explains why to read the ref."""
    ref_escaped = re.escape(ref)
    after_match = re.search(
        rf"{ref_escaped}\)\.?\s*(.*)",
        gate_text,
    )
    if after_match:
        trailing = after_match.group(1).strip()
        if trailing and trailing != ".":
            return True

    return PURPOSE_TRAILING_RE.search(gate_text) is not None


# ---------------------------------------------------------------------------
# Flow coverage helper
# ---------------------------------------------------------------------------


def _count_flow_coverage(
    ref: str,
    prose_lines: tuple[ProseLine, ...],
    section: FlowSection,
    bundled_indices: frozenset[int],
) -> tuple[bool, bool]:
    """Return (is_mentioned, is_gated) for one ref in one flow section."""
    is_mentioned = False
    is_gated = False
    ref_lower = ref.lower()

    for line in prose_lines:
        if line.index < section.start_index:
            continue
        if line.index >= section.end_index:
            break
        if line.index in bundled_indices:
            continue
        if ref_lower not in line.text.lower():
            continue
        is_mentioned = True
        if _is_gate_line(line.text, ref):
            is_gated = True

    return is_mentioned, is_gated


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def _check_gate(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
) -> CheckRecord:
    """RG-GATE: every linked ref has an explicit load directive."""
    fails = [
        a.ref
        for a in analyses.values()
        if a.ref in inventory.linked_refs and a.gate_index is None
    ]
    if not fails:
        return CheckRecord(
            check=CHECK_GATE,
            passed=True,
            detail="All linked references have explicit load directives",
            tier="I19",
        )
    refs_str = " ".join(fails)
    return CheckRecord(
        check=CHECK_GATE,
        passed=False,
        detail=(
            f"{len(fails)} reference(s) linked without explicit load directive"
            f" (Read, Contents of, path to, Load): {refs_str}"
        ),
        tier="I19",
    )


def _check_passive(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
    document: SkillDocument,
) -> CheckRecord:
    """RG-PASSIVE: no passive weak mentions before gates."""
    detail_parts: list[str] = []
    seen_refs: set[str] = set()

    for analysis in analyses.values():
        if analysis.ref not in inventory.linked_refs:
            continue
        if analysis.passive_before_gate:
            seen_refs.add(analysis.ref)
            first_line = document.line_number(analysis.passive_before_gate[0])
            detail_parts.append(f"{analysis.ref}:L{first_line}")

    if not detail_parts:
        return CheckRecord(
            check=CHECK_PASSIVE,
            passed=True,
            detail="No passive weak mentions found before gates",
            tier="I19",
        )
    details_str = " ".join(detail_parts)
    return CheckRecord(
        check=CHECK_PASSIVE,
        passed=False,
        detail=(
            f"{len(seen_refs)} reference(s) have passive mentions"
            f" before their gate: {details_str}"
        ),
        tier="I19",
    )


def _check_orphan(orphan_refs: frozenset[str]) -> CheckRecord:
    """RG-ORPHAN: no disk files missing from SKILL.md entirely."""
    if not orphan_refs:
        return CheckRecord(
            check=CHECK_ORPHAN,
            passed=True,
            detail="All disk files are mentioned in SKILL.md",
            tier="I19",
        )
    refs_str = " ".join(sorted(orphan_refs))
    return CheckRecord(
        check=CHECK_ORPHAN,
        passed=False,
        detail=(
            f"{len(orphan_refs)} file(s) on disk not mentioned"
            f" in SKILL.md: {refs_str}"
        ),
        tier="I19",
    )


def _check_dead(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
    orphan_refs: frozenset[str],
    bundled_indices: frozenset[int],
    prose_lines: tuple[ProseLine, ...],
) -> CheckRecord:
    """RG-DEAD: no refs listed only in bundled resources section."""
    if not bundled_indices:
        return CheckRecord(
            check=CHECK_DEAD,
            passed=True,
            detail="No dead bundled-only listings found",
            tier="I19",
        )

    fails: list[str] = []
    for analysis in analyses.values():
        ref = analysis.ref
        if ref not in inventory.linked_refs:
            continue
        if ref in orphan_refs:
            continue
        has_outside = _ref_has_mention_outside_bundled(
            ref,
            prose_lines,
            bundled_indices,
        )
        if not has_outside:
            fails.append(ref)

    if not fails:
        return CheckRecord(
            check=CHECK_DEAD,
            passed=True,
            detail="No dead bundled-only listings found",
            tier="I19",
        )
    refs_str = " ".join(fails)
    return CheckRecord(
        check=CHECK_DEAD,
        passed=False,
        detail=(
            f"{len(fails)} reference(s) only appear in bundled resources"
            f" section, never used in workflow: {refs_str}"
        ),
        tier="I19",
    )


def _ref_has_mention_outside_bundled(
    ref: str,
    prose_lines: tuple[ProseLine, ...],
    bundled_indices: frozenset[int],
) -> bool:
    """Return whether ref appears in any prose line outside bundled."""
    ref_lower = ref.lower()
    return any(
        ref_lower in line.text.lower()
        for line in prose_lines
        if line.index not in bundled_indices
    )


def _check_use_order(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
    document: SkillDocument,
) -> CheckRecord:
    """RG-ORDER: no ref cited before its gate appears."""
    detail_parts: list[str] = []

    for analysis in analyses.values():
        if analysis.ref not in inventory.linked_refs:
            continue
        if analysis.gate_index is None:
            continue
        if not analysis.use_indices:
            continue
        first_use = analysis.use_indices[0]
        if first_use < analysis.gate_index:
            use_line = document.line_number(first_use)
            gate_line = document.line_number(analysis.gate_index)
            detail_parts.append(
                f"{analysis.ref}:used-L{use_line}<gate-L{gate_line}",
            )

    if not detail_parts:
        return CheckRecord(
            check=CHECK_USE_ORDER,
            passed=True,
            detail="All references are gated before first use",
            tier="I19",
        )
    details_str = " ".join(detail_parts)
    return CheckRecord(
        check=CHECK_USE_ORDER,
        passed=False,
        detail=(
            f"{len(detail_parts)} reference(s) cited before their gate: {details_str}"
        ),
        tier="I19",
    )


def _check_purpose(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
    prose_lines: tuple[ProseLine, ...],
) -> CheckRecord:
    """RG-PURPOSE: read gates explain why (not bare path-only gates)."""
    prose_by_index = {line.index: line.text for line in prose_lines}
    fails: list[str] = []

    for analysis in analyses.values():
        if analysis.ref not in inventory.linked_refs:
            continue
        if analysis.gate_index is None:
            continue
        gate_text = prose_by_index.get(analysis.gate_index)
        if gate_text is None:
            continue
        if not _gate_has_purpose(gate_text, analysis.ref):
            fails.append(analysis.ref)

    if not fails:
        return CheckRecord(
            check=CHECK_PURPOSE,
            passed=True,
            detail="All read gates explain their purpose",
            tier="I19",
        )
    refs_str = " ".join(fails)
    return CheckRecord(
        check=CHECK_PURPOSE,
        passed=False,
        detail=(f"{len(fails)} gate(s) lack purpose text (why to read): {refs_str}"),
        tier="I19",
    )


def _check_flow(
    inventory: RefInventory,
    analyses: dict[str, RefAnalysis],
    prose_lines: tuple[ProseLine, ...],
    bundled_indices: frozenset[int],
) -> CheckRecord:
    """RG-FLOW: multi-flow skills gate refs in each flow."""
    if not _is_multi_flow(prose_lines):
        return CheckRecord(
            check=CHECK_FLOW,
            passed=True,
            detail="Single-flow skill, flow coverage check not applicable",
            tier="I19",
        )

    flow_sections = _detect_flow_sections(prose_lines)
    if not flow_sections:
        return CheckRecord(
            check=CHECK_FLOW,
            passed=True,
            detail="Single-flow skill, flow coverage check not applicable",
            tier="I19",
        )

    detail_parts: list[str] = []

    for analysis in analyses.values():
        if analysis.ref not in inventory.linked_refs:
            continue

        mention_count = 0
        gate_count = 0

        for section in flow_sections:
            mentioned, gated = _count_flow_coverage(
                analysis.ref,
                prose_lines,
                section,
                bundled_indices,
            )
            if mentioned:
                mention_count += 1
            if gated:
                gate_count += 1

        if mention_count >= MIN_FLOW_MENTIONS and gate_count < mention_count:
            detail_parts.append(
                f"{analysis.ref}:gated-in-{gate_count}-of-{mention_count}-flows",
            )

    if not detail_parts:
        return CheckRecord(
            check=CHECK_FLOW,
            passed=True,
            detail="All references gated in each workflow flow",
            tier="I19",
        )
    details_str = " ".join(detail_parts)
    return CheckRecord(
        check=CHECK_FLOW,
        passed=False,
        detail=(
            f"{len(detail_parts)} reference(s) not gated in all"
            f" workflow flows: {details_str}"
        ),
        tier="I19",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> tuple[list[CheckRecord], dict[str, object]]:
    """Build inventory, run checks, return results and extra summary."""
    inventory = _build_inventory(document)

    if inventory.count == 0:
        return [], {"refs": 0}

    prose_lines = extract_prose_lines(document.body)
    bundled_indices = find_bundled_indices(prose_lines)

    analyses: dict[str, RefAnalysis] = {}
    for ref in sorted(inventory.all_refs):
        analyses[ref] = _analyze_ref(
            ref,
            prose_lines,
            bundled_indices,
            document.content,
        )

    orphan_refs = frozenset(
        a.ref
        for a in analyses.values()
        if a.ref in inventory.disk_refs and not a.in_full_content
    )

    selected = frozenset(selected_checks)

    check_results: dict[str, CheckRecord] = {
        CHECK_GATE: _check_gate(inventory, analyses),
        CHECK_PASSIVE: _check_passive(inventory, analyses, document),
        CHECK_ORPHAN: _check_orphan(orphan_refs),
        CHECK_DEAD: _check_dead(
            inventory,
            analyses,
            orphan_refs,
            bundled_indices,
            prose_lines,
        ),
        CHECK_USE_ORDER: _check_use_order(inventory, analyses, document),
        CHECK_PURPOSE: _check_purpose(inventory, analyses, prose_lines),
        CHECK_FLOW: _check_flow(
            inventory,
            analyses,
            prose_lines,
            bundled_indices,
        ),
    }

    results = [
        check_results[check_id]
        for check_id in CHECK_ORDER
        if not selected or check_id in selected
    ]

    return results, {"refs": inventory.count}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and return process exit code."""
    return run_check_cli(
        "Validate reference file read gates in a skill SKILL.md",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
