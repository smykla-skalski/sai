#!/usr/bin/env python3
"""Prompt-quality checks for Codex skill bundles."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _skill_check_common import (
    CheckRecord,
    ResultCollector,
    load_skill_document,
    read_text,
)

FILLER_FAILURE_THRESHOLD = 2
EXAMPLE_MINIMUM = 2
FILLER_PHRASES = (
    "write clean code",
    "follow best practices",
    "handle edge cases",
    "handle errors gracefully",
    "be concise and clear",
)
STARTUP_COST_PATTERNS = (
    "list every installed skill",
    "enumerate every skill",
    "on startup",
    "at startup",
    "every session",
    "before every request",
)
FORBIDDEN_FRONTMATTER_FIELDS = {
    "allowed-tools",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
    "hooks",
}


def _check_claude_only_surface(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    found = sorted(FORBIDDEN_FRONTMATTER_FIELDS.intersection(doc.frontmatter))
    found.extend(_body_claude_only_terms(doc.body))
    detail = (
        "No Claude-only runtime surface detected."
        if not found
        else "Claude-only runtime surface detected: " + ", ".join(sorted(set(found)))
    )
    return CheckRecord(
        check="PR-claude-only-surface",
        passed=not found,
        level="critical",
        detail=detail,
    )


def _check_no_filler(skill_dir: Path) -> CheckRecord:
    lower_body = load_skill_document(skill_dir).body.lower()
    hits = [phrase for phrase in FILLER_PHRASES if phrase in lower_body]
    detail = (
        "The skill avoids generic filler."
        if len(hits) < FILLER_FAILURE_THRESHOLD
        else "Generic filler phrases found: " + ", ".join(hits)
    )
    return CheckRecord(
        check="PR-no-filler",
        passed=len(hits) < FILLER_FAILURE_THRESHOLD,
        level="critical",
        detail=detail,
    )


def _check_routing_boundaries(skill_dir: Path) -> CheckRecord:
    lower_body = load_skill_document(skill_dir).body.lower()
    has_positive = "use this skill" in lower_body or "use when" in lower_body
    has_negative = "do not use" in lower_body or "not designed for" in lower_body
    detail = (
        "The skill defines both use and do-not-use boundaries."
        if has_positive and has_negative
        else "Add explicit use-this-skill and do-not-use-this-skill boundaries."
    )
    return CheckRecord(
        check="PR-routing-boundaries",
        passed=has_positive and has_negative,
        level="important",
        detail=detail,
    )


def _check_examples(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    example_count = doc.content.count("<example>")
    examples_path = doc.skill_dir / "references" / "examples.md"
    if examples_path.exists():
        example_count += read_text(examples_path).count("<example>")
    detail = (
        f"Found {example_count} example blocks."
        if example_count >= EXAMPLE_MINIMUM
        else "Add at least two concrete example blocks."
    )
    return CheckRecord(
        check="PR-examples",
        passed=example_count >= EXAMPLE_MINIMUM,
        level="important",
        detail=detail,
    )


def _check_startup_cost(skill_dir: Path) -> CheckRecord:
    lower_body = load_skill_document(skill_dir).body.lower()
    hits = [phrase for phrase in STARTUP_COST_PATTERNS if phrase in lower_body]
    detail = (
        "No startup-cost smell detected."
        if not hits
        else "Startup-cost language detected: " + ", ".join(hits)
    )
    return CheckRecord(
        check="PR-startup-cost",
        passed=not hits,
        level="important",
        detail=detail,
    )


def _check_verification_loop(skill_dir: Path) -> CheckRecord:
    lower_body = load_skill_document(skill_dir).body.lower()
    has_verify = "verify" in lower_body or "verification" in lower_body
    has_rerun = "rerun" in lower_body or "re-run" in lower_body
    has_fix = "fix" in lower_body
    detail = (
        "The skill defines a fix and verification loop."
        if has_verify and has_rerun and has_fix
        else "Add an explicit rerun-and-verify loop after fixes."
    )
    return CheckRecord(
        check="PR-verification-loop",
        passed=has_verify and has_rerun and has_fix,
        level="important",
        detail=detail,
    )


def _body_claude_only_terms(body: str) -> list[str]:
    found: list[str] = []
    for raw_line in body.splitlines():
        lowered = raw_line.lower()
        if _is_negative_context_line(raw_line):
            continue
        if "$arguments" in lowered:
            found.append("$ARGUMENTS")
        if "$claude_skill_dir" in lowered:
            found.append("$CLAUDE_SKILL_DIR")
        if "askuserquestion" in lowered:
            found.append("AskUserQuestion")
        if re.search(r"context:\s*fork", raw_line, re.IGNORECASE):
            found.append("context: fork")
    return found


def _is_negative_context_line(raw_line: str) -> bool:
    return re.match(
        r"^\s*(?:[-*+]|\d+\.)?\s*(?:do not apply|do not use|claude-only)\b",
        raw_line,
        re.IGNORECASE,
    ) is not None


CHECKS = {
    "PR-claude-only-surface": _check_claude_only_surface,
    "PR-no-filler": _check_no_filler,
    "PR-routing-boundaries": _check_routing_boundaries,
    "PR-examples": _check_examples,
    "PR-startup-cost": _check_startup_cost,
    "PR-verification-loop": _check_verification_loop,
}


def run_checks(
    skill_dir: Path,
    collector: ResultCollector,
    *,
    selected: set[str] | None = None,
) -> None:
    """Run prompt-quality checks for a skill directory."""
    names = selected or set(CHECKS)
    for check_id, check_fn in CHECKS.items():
        if check_id in names:
            collector.emit(check_fn(skill_dir))


def main(argv: list[str] | None = None) -> int:
    """Run prompt-quality checks as a CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--check", action="append", dest="checks")
    args = parser.parse_args(argv)

    collector = ResultCollector()
    selected = set(args.checks) if args.checks else None
    run_checks(args.skill_dir, collector, selected=selected)
    collector.emit_summary()
    return 1 if collector.blocking_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
