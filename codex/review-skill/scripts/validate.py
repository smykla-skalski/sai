#!/usr/bin/env python3
"""Top-level validator implementation for Codex skill bundles."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import check_agents_metadata
import check_prompts
import check_shell_safety
import check_structure
from _skill_check_common import (
    CheckRecord,
    ResultCollector,
    SkillLoadError,
    body_line_count,
    load_skill_document,
)

EXIT_USAGE_ERROR = 2
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_BODY_LINES = 500
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIGGER_RE = re.compile(r"\buse (?:when|for|this skill)\b", re.IGNORECASE)


def run_frontmatter(skill_dir: Path, collector: ResultCollector) -> None:
    """Emit frontmatter checks for a skill directory."""
    doc = load_skill_document(skill_dir)
    name = doc.frontmatter.get("name", "")
    description = doc.frontmatter.get("description", "")
    body_lines = body_line_count(doc.body)

    collector.emit(
        CheckRecord(
            check="FM-name-present",
            passed=bool(name),
            level="critical",
            detail="name is present." if name else "Missing frontmatter name.",
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-name-format",
            passed=bool(name)
            and len(name) <= MAX_NAME_LENGTH
            and NAME_RE.match(name) is not None,
            level="critical",
            detail=(
                f"name '{name}' is valid kebab-case."
                if bool(name)
                and len(name) <= MAX_NAME_LENGTH
                and NAME_RE.match(name) is not None
                else "name must be kebab-case and at most 64 characters."
            ),
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-name-matches-dir",
            passed=bool(name) and name == doc.skill_dir.name,
            level="critical",
            detail=(
                f"name matches directory '{doc.skill_dir.name}'."
                if bool(name) and name == doc.skill_dir.name
                else f"name must match directory '{doc.skill_dir.name}'."
            ),
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-description-present",
            passed=bool(description),
            level="critical",
            detail=(
                "description is present."
                if description
                else "Missing frontmatter description."
            ),
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-description-trigger",
            passed=bool(description) and TRIGGER_RE.search(description) is not None,
            level="critical",
            detail=(
                "description explains when to use the skill."
                if bool(description) and TRIGGER_RE.search(description) is not None
                else "description should include a clear use-when trigger."
            ),
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-description-length",
            passed=len(description) <= MAX_DESCRIPTION_LENGTH,
            level="important",
            detail=(
                f"description length is {len(description)} characters."
                if len(description) <= MAX_DESCRIPTION_LENGTH
                else f"description is too long at {len(description)} characters."
            ),
        ),
    )
    collector.emit(
        CheckRecord(
            check="FM-body-lines",
            passed=body_lines < MAX_BODY_LINES,
            level="critical",
            detail=(
                f"Body has {body_lines} lines."
                if body_lines < MAX_BODY_LINES
                else f"Body has {body_lines} lines; keep it under 500."
            ),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """Run frontmatter and delegated checks as a CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("all", "frontmatter", "structure", "shell", "metadata", "prompts"),
        default="all",
    )
    args = parser.parse_args(argv)

    collector = ResultCollector()
    try:
        if args.mode in {"all", "frontmatter"}:
            run_frontmatter(args.skill_dir, collector)
        if args.mode in {"all", "structure"}:
            check_structure.run_checks(args.skill_dir, collector)
        if args.mode in {"all", "shell"}:
            check_shell_safety.run_checks(args.skill_dir, collector)
        if args.mode in {"all", "metadata"}:
            check_agents_metadata.run_checks(args.skill_dir, collector)
        if args.mode in {"all", "prompts"}:
            check_prompts.run_checks(args.skill_dir, collector)
    except SkillLoadError as error:
        collector.emit(
            CheckRecord(
                check="FM-skill-md-exists",
                passed=False,
                level="critical",
                detail=str(error),
            ),
        )
        collector.emit_summary()
        return EXIT_USAGE_ERROR

    collector.emit_summary()
    return 1 if collector.blocking_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
