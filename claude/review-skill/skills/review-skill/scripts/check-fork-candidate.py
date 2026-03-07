#!/usr/bin/env python3
"""Analyze whether a skill should use context: fork + agent field.

Usage:
    ./check-fork-candidate.py <skill-directory>

Output: One JSON object per line (NDJSON).
    Signal line:
        {"signal": "<id>", "type": "blocker|positive|counter",
         "detected": true|false, "detail": "msg"}
    Summary line:
        {"recommendation": "strong|soft|none", "positive_count": N,
         "effective_count": N, "positive_ids": "P1 P2",
         "blocker_count": N, "blocker_ids": "B1",
         "counter_count": N, "counter_ids": "N1",
         "agent_type": "general-purpose|Explore",
         "detail": "Human-readable recommendation."}

Exit code: 0 if applies, 1 if no suggestion, 2 if usage error.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final, Literal

from _skill_check_common import (
    EXIT_FAILURE,
    EXIT_OK,
    EXIT_USAGE_ERROR,
    SignalRecord,
    SkillDocument,
    SkillLoadError,
    SummaryRecord,
    emit_error,
    emit_record,
    load_skill_document,
    parse_allowed_tools,
)

# ---------------------------------------------------------------------------
# Constants & patterns
# ---------------------------------------------------------------------------

RECOMMENDATION_STRONG: Final[str] = "strong"
RECOMMENDATION_SOFT: Final[str] = "soft"
RECOMMENDATION_NONE: Final[str] = "none"

TINY_SKILL_LINES_THRESHOLD: Final[int] = 40
HIGH_PHASE_COUNT_THRESHOLD: Final[int] = 5
STRONG_CANDIDATE_THRESHOLD: Final[int] = 3
SOFT_CANDIDATE_THRESHOLD: Final[int] = 2
P5_MIN_REF_FILES: Final[int] = 3
P5_MIN_READ_DIRECTIVES: Final[int] = 2

# B2 conversation-dependent phrases
B2_CONV_HITS_RE: Final[Pattern[str]] = re.compile(
    r"conversation\s+(context|history)|"
    r"previous(?:ly)?\s+(message|discussed)|"
    r"selected\s+(code|text|block|content)|"
    r"what\s+(you|the\s+user)\s+(said|asked|want|mentioned)|"
    r"from\s+(the|our)\s+(conversation|discussion|chat)",
    re.IGNORECASE,
)

# P1 phase/step header pattern
P1_PHASE_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,4}\s+(Phase|Step)\s+\d+\b",
    re.IGNORECASE,
)

# P2 structured output headers
P2_OUTPUT_HEADERS_RE: Final[Pattern[str]] = re.compile(
    r"^#{1,4}\s+.*\b(Output|Report|Template|Artifact|Digest|Verdict)\b",
    re.IGNORECASE,
)
P2_INTERNAL_FORMAT_RE: Final[Pattern[str]] = re.compile(
    r"(Script|JSON|NDJSON|Wire|Data|API|Log|Raw|Parse)\s+(output|format)",
    re.IGNORECASE,
)

# P3 web tool references
P3_WEB_RE: Final[Pattern[str]] = re.compile(r"\b(WebSearch|WebFetch)\b")

# P4 manual subagent spawning
P4_SPAWN1_RE: Final[Pattern[str]] = re.compile(
    r"\bspawn\b.*\bagent\b|\bagent\b.*\bspawn\b|"
    r"\bTaskCreate\b|\bTask tool\b|\bsubagent\b",
    re.IGNORECASE,
)
P4_SPAWN2_RE: Final[Pattern[str]] = re.compile(
    r"\b(spawn|create|launch)\b.*(agent|task)\b",
    re.IGNORECASE,
)

# P5 reference read directives
P5_READ_RE: Final[Pattern[str]] = re.compile(
    r"\bread\b.*references/",
    re.IGNORECASE,
)

# P6 implicit session input
P6_IMPLICIT_INPUT_RE: Final[Pattern[str]] = re.compile(
    r"\b(current|active)\s+(file|buffer|selection|PR|pull\s+request|branch)\b|"
    r"\bthis\s+(file|code|PR|function|branch)\b",
    re.IGNORECASE,
)

# N1 destructive command patterns
N1_DESTRUCTIVE_RE: Final[Pattern[str]] = re.compile(
    r"k3d\s+(cluster|create|delete)|"
    r"kind\s+(create|delete)\s+cluster|"
    r"git\s+reset|"
    r"git\s+branch\s+-[dD]|"
    r"git\s+apply\s+--cached|"
    r"git\s+clean\s+-|"
    r"git\s+push\s+--force|"
    r"kubectl\s+(delete|drain|cordon)|"
    r"helm\s+(uninstall|delete)|"
    r"rm\s+-rf",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WebSignals:
    """Store web-related signal detection state."""

    has_websearch_tool: bool
    has_webfetch_tool: bool
    body_web: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _signal(
    signal_id: str,
    signal_type: Literal["positive", "blocker", "counter"],
    *,
    detected: bool,
    detail: str,
) -> SignalRecord:
    """Emit a signal as NDJSON and return the result."""
    result = SignalRecord(
        signal=signal_id,
        type=signal_type,
        detected=detected,
        detail=detail,
    )
    emit_record(result.payload())
    return result


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_blockers(doc: SkillDocument) -> list[SignalRecord]:
    """Run all blocker signal checks and return detected results."""
    results: list[SignalRecord] = []

    # B1 - already forked
    if doc.field("context").lower() == "fork":
        results.append(
            _signal("FK-B1", "blocker", detected=True, detail="Already uses fork"),
        )
    else:
        _signal("FK-B1", "blocker", detected=False, detail="No fork frontmatter")

    # B2 - conversation-dependent
    if B2_CONV_HITS_RE.search(doc.prose_body):
        first_hit = ""
        for line in doc.prose_body.splitlines():
            if B2_CONV_HITS_RE.search(line):
                first_hit = line.strip()[:80]
                break
        results.append(
            _signal(
                "FK-B2",
                "blocker",
                detected=True,
                detail=f"Conversation-dependent: {first_hit}",
            ),
        )
    else:
        _signal(
            "FK-B2",
            "blocker",
            detected=False,
            detail="No conversation-dependent phrases found",
        )

    # B3 - tiny skill
    body_lines = len(doc.body.splitlines())
    if body_lines < TINY_SKILL_LINES_THRESHOLD:
        results.append(
            _signal(
                "FK-B3",
                "blocker",
                detected=True,
                detail=f"Body {body_lines} lines — overhead not justified",
            ),
        )
    else:
        _signal(
            "FK-B3",
            "blocker",
            detected=False,
            detail=f"Body is {body_lines} lines",
        )

    # B4 - background knowledge
    if doc.field("user-invocable").lower() == "false":
        results.append(
            _signal(
                "FK-B4",
                "blocker",
                detected=True,
                detail="user-invocable: false — context enrichment, not task",
            ),
        )
    else:
        _signal("FK-B4", "blocker", detected=False, detail="User-invocable")

    return results


def _check_positives_p1_p2(
    prose_lines: list[str],
    results: list[SignalRecord],
) -> None:
    """Check P1 (phase count) and P2 (structured output)."""
    # P1 - high phase count
    phase_count = sum(1 for line in prose_lines if P1_PHASE_RE.search(line))
    if phase_count >= HIGH_PHASE_COUNT_THRESHOLD:
        results.append(
            _signal(
                "FK-P1",
                "positive",
                detected=True,
                detail=f"{phase_count} phases — workflow generates context",
            ),
        )
    else:
        _signal(
            "FK-P1",
            "positive",
            detected=False,
            detail=f"{phase_count} numbered phases (threshold: 5)",
        )

    # P2 - structured output artifact
    output_filtered = [
        line.strip()
        for line in prose_lines
        if P2_OUTPUT_HEADERS_RE.search(line) and not P2_INTERNAL_FORMAT_RE.search(line)
    ]
    if output_filtered:
        first_header = output_filtered[0][:60]
        results.append(
            _signal(
                "FK-P2",
                "positive",
                detected=True,
                detail=f"Has structured output section: {first_header}",
            ),
        )
    else:
        _signal(
            "FK-P2",
            "positive",
            detected=False,
            detail="No structured output/report section found",
        )


def _check_positives_p3_p4(
    doc: SkillDocument,
    allowed_tools: frozenset[str],
    results: list[SignalRecord],
) -> WebSignals:
    """Check P3 (data gathering) and P4 (manual subagent). Return web state."""
    # P3 - data gathering via web tools
    has_websearch_tool = "WebSearch" in allowed_tools
    has_webfetch_tool = "WebFetch" in allowed_tools
    body_web = bool(P3_WEB_RE.search(doc.prose_body))

    if has_websearch_tool or has_webfetch_tool or body_web:
        results.append(
            _signal(
                "FK-P3",
                "positive",
                detected=True,
                detail="Uses WebSearch/Fetch — results pollute context",
            ),
        )
    else:
        _signal(
            "FK-P3",
            "positive",
            detected=False,
            detail="No WebSearch/WebFetch usage detected",
        )

    # P4 - manual subagent usage
    has_task_tool = "Task" in allowed_tools
    body_spawn = bool(
        P4_SPAWN1_RE.search(doc.prose_body) or P4_SPAWN2_RE.search(doc.prose_body),
    )

    if has_task_tool and body_spawn:
        results.append(
            _signal(
                "FK-P4",
                "positive",
                detected=True,
                detail="Task in allowed-tools + body spawns agents",
            ),
        )
    else:
        _signal(
            "FK-P4",
            "positive",
            detected=False,
            detail="No explicit agent spawning detected",
        )

    return WebSignals(
        has_websearch_tool=has_websearch_tool,
        has_webfetch_tool=has_webfetch_tool,
        body_web=body_web,
    )


def _check_positives_p5_p6(
    doc: SkillDocument,
    prose_lines: list[str],
    results: list[SignalRecord],
) -> None:
    """Check P5 (heavy reference loading) and P6 (self-contained inputs)."""
    # P5 - heavy reference loading
    ref_dir = doc.skill_dir / "references"
    ref_count = 0
    if ref_dir.is_dir():
        ref_count = sum(
            1 for f in ref_dir.iterdir() if f.is_file() and f.suffix == ".md"
        )

    read_directives = sum(1 for line in prose_lines if P5_READ_RE.search(line))

    if ref_count >= P5_MIN_REF_FILES and read_directives >= P5_MIN_READ_DIRECTIVES:
        results.append(
            _signal(
                "FK-P5",
                "positive",
                detected=True,
                detail=f"{ref_count} refs + {read_directives} reads — heavy loading",
            ),
        )
    else:
        _signal(
            "FK-P5",
            "positive",
            detected=False,
            detail=f"{ref_count} reference files, {read_directives} read dirs",
        )

    # P6 - self-contained inputs
    has_arguments = "$ARGUMENTS" in doc.body
    implicit_input = bool(P6_IMPLICIT_INPUT_RE.search(doc.prose_body))

    if has_arguments and not implicit_input:
        results.append(
            _signal(
                "FK-P6",
                "positive",
                detected=True,
                detail="All input via $ARGUMENTS, no implicit dependency",
            ),
        )
    else:
        _signal(
            "FK-P6",
            "positive",
            detected=False,
            detail="Body relies on session context or lacks $ARGUMENTS",
        )


def check_positives(doc: SkillDocument) -> tuple[list[SignalRecord], WebSignals]:
    """Run all positive signal checks and return results + web state."""
    results: list[SignalRecord] = []
    prose_lines = doc.prose_body.splitlines()
    allowed_tools = parse_allowed_tools(doc.frontmatter)

    _check_positives_p1_p2(prose_lines, results)
    web = _check_positives_p3_p4(doc, allowed_tools, results)
    _check_positives_p5_p6(doc, prose_lines, results)

    return results, web


def check_counters(doc: SkillDocument) -> list[SignalRecord]:
    """Run all counter signal checks and return detected results."""
    results: list[SignalRecord] = []

    # N1 - side-effect skill
    dmi = doc.field("disable-model-invocation").lower() == "true"
    side_effect_hits = sum(
        1 for line in doc.body.splitlines() if N1_DESTRUCTIVE_RE.search(line)
    )

    if dmi or side_effect_hits > 0:
        results.append(
            _signal(
                "FK-N1",
                "counter",
                detected=True,
                detail=f"Side-effect ({side_effect_hits} hits) — reduces visibility",
            ),
        )
    else:
        _signal("FK-N1", "counter", detected=False, detail="No side-effects")

    # N2 - AskUserQuestion actively used (forked agents can't interact)
    auq_in_tools = "AskUserQuestion" in doc.field("allowed-tools")
    auq_in_body = "AskUserQuestion" in doc.body
    if auq_in_tools and auq_in_body:
        results.append(
            _signal(
                "FK-N2",
                "counter",
                detected=True,
                detail="AskUserQuestion actively used — forked agents cannot interact",
            ),
        )
    else:
        _signal("FK-N2", "counter", detected=False, detail="No AskUserQuestion usage")

    # N3 - Write/Edit actively used (fork results are summarized, not written)
    write_tools = {"Edit", "Write"}
    has_write_tools = any(
        t.strip() in write_tools for t in doc.field("allowed-tools").split(",")
    )
    write_in_body = "Edit" in doc.body or "Write" in doc.body
    if has_write_tools and write_in_body:
        results.append(
            _signal(
                "FK-N3",
                "counter",
                detected=True,
                detail=(
                    "Write/Edit actively used - fork output is summarized, not direct"
                ),
            ),
        )
    else:
        _signal("FK-N3", "counter", detected=False, detail="No Write/Edit usage")

    return results


def determine_agent(web: WebSignals) -> tuple[str, str]:
    """Determine the recommended agent type based on web signals."""
    if web.has_websearch_tool or web.has_webfetch_tool or web.body_web:
        return "Explore", "research-heavy skill benefits from Explore agent"
    return "general-purpose", "default for task execution"


def build_summary(  # noqa: PLR0913
    blockers: list[SignalRecord],
    positives: list[SignalRecord],
    counters: list[SignalRecord],
    agent_type: str,
    agent_reason: str,
    *,
    total_signals: int,
) -> tuple[SummaryRecord, int]:
    """Build the summary record and determine exit code."""
    blocker_count = len(blockers)
    positive_count = len(positives)
    counter_count = len(counters)
    effective_count = max(0, positive_count - counter_count)

    blocker_ids = " ".join(s.signal for s in blockers)
    positive_ids = " ".join(s.signal for s in positives)
    counter_ids = " ".join(s.signal for s in counters)

    if blocker_count > 0:
        recommendation = RECOMMENDATION_NONE
        detail = f"Blocked by {blocker_ids} - not a fork candidate"
    elif effective_count >= STRONG_CANDIDATE_THRESHOLD:
        recommendation = RECOMMENDATION_STRONG
        counter_note = (
            f", minus counters = {effective_count} effective"
            if counter_count > 0
            else ""
        )
        detail = (
            f"Strong candidate for context: fork ({positive_count} signals: "
            f"{positive_ids}{counter_note}). Add to frontmatter: context: fork, "
            f"agent: {agent_type}. {agent_reason.capitalize()}"
        )
    elif effective_count >= SOFT_CANDIDATE_THRESHOLD:
        recommendation = RECOMMENDATION_SOFT
        counter_note = (
            f", minus counters = {effective_count} effective"
            if counter_count > 0
            else ""
        )
        detail = (
            f"Consider context: fork ({positive_count} signals: "
            f"{positive_ids}{counter_note}). Fork would isolate intermediate "
            f"work from the main context. Suggested agent: {agent_type}"
        )
    else:
        recommendation = RECOMMENDATION_NONE
        counter_note = (
            f" ({positive_count} positive minus {counter_count} counter(s))"
            if counter_count > 0
            else ""
        )
        detail = (
            f"Only {effective_count} effective signal(s)"
            f"{counter_note} - fork overhead likely not justified"
        )

    summary = SummaryRecord(
        total=total_signals,
        passed=0,
        failed=0,
        info=total_signals,
        extras={
            "recommendation": recommendation,
            "positive_count": positive_count,
            "effective_count": effective_count,
            "positive_ids": positive_ids,
            "blocker_count": blocker_count,
            "blocker_ids": blocker_ids,
            "counter_count": counter_count,
            "counter_ids": counter_ids,
            "agent_type": agent_type,
            "detail": detail,
        },
    )

    exit_code = EXIT_OK if recommendation != RECOMMENDATION_NONE else EXIT_FAILURE
    return summary, exit_code


def run_analysis(doc: SkillDocument) -> int:
    """Run full fork-candidate analysis and emit NDJSON results."""
    blockers = check_blockers(doc)
    positives, web = check_positives(doc)
    counters = check_counters(doc)
    agent_type, agent_reason = determine_agent(web)
    # All signals are always emitted (4 blockers + 6 positives + 3 counters)
    total_signals = 4 + 6 + 3
    summary, exit_code = build_summary(
        blockers,
        positives,
        counters,
        agent_type,
        agent_reason,
        total_signals=total_signals,
    )
    emit_record(summary.payload())
    return exit_code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyze whether a skill should use context: fork + agent field.",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to skill directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the check-fork-candidate process and output NDJSON."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        doc = load_skill_document(args.skill_directory)
    except SkillLoadError as e:
        emit_error(f"Error: {e}")
        return EXIT_USAGE_ERROR

    return run_analysis(doc)


if __name__ == "__main__":
    raise SystemExit(main())
