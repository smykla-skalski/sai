#!/usr/bin/env python3
"""Structure checks for Codex skill bundles."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _skill_check_common import (
    CheckRecord,
    ResultCollector,
    body_line_count,
    file_relative_to,
    load_skill_document,
    read_text,
    relative_links,
    resolve_link_target,
)

LONG_REFERENCE_LINES = 100
PROGRESSIVE_DISCLOSURE_LINES = 220
AGENT_METADATA_PATH = "agents/openai.yaml"


def _check_links_resolve(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    missing: list[str] = []
    invalid_absolute: list[str] = []
    for target, line in _slash_prefixed_links(doc.body):
        absolute_line = doc.body_start_line + line - 1
        invalid_absolute.append(f"{target} (line {absolute_line})")
    for link in relative_links(doc.body):
        target_path = resolve_link_target(doc.skill_dir, link.target)
        if not target_path.exists():
            absolute_line = doc.body_start_line + link.line - 1
            missing.append(f"{link.target} (line {absolute_line})")

    detail = (
        "All relative markdown links resolve from SKILL.md."
        if not invalid_absolute and not missing
        else (
            "Slash-prefixed links must use bundle-relative paths: "
            + ", ".join(invalid_absolute[:5])
        )
        if invalid_absolute
        else "Broken linked files: " + ", ".join(missing[:5])
    )
    return CheckRecord(
        check="ST-links-resolve",
        passed=not invalid_absolute and not missing,
        level="critical",
        detail=detail,
    )


def _check_read_directives(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    lines = doc.body.splitlines()
    ungated: list[str] = []
    for link in relative_links(doc.body):
        if not link.target.endswith(".md"):
            continue
        line_index = link.line - 1
        window = [lines[line_index].lower()]
        if line_index > 0:
            window.insert(0, lines[line_index - 1].lower())
        if not any("read " in entry or "open " in entry for entry in window):
            absolute_line = doc.body_start_line + link.line - 1
            ungated.append(f"{link.target} (line {absolute_line})")

    detail = (
        "Linked references have explicit read directives."
        if not ungated
        else "Linked references need explicit read directives: "
        + ", ".join(ungated[:5])
    )
    return CheckRecord(
        check="ST-read-directives",
        passed=not ungated,
        level="important",
        detail=detail,
    )


def _check_bundled_docs_mentioned(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    missing_docs: list[str] = []
    linked_targets = {
        link.target.split("#", 1)[0]
        for link in relative_links(doc.body)
    }

    for path in doc.resource_files:
        relative_path = file_relative_to(path, doc.skill_dir)
        if not _is_surface_doc(relative_path):
            continue
        if relative_path not in linked_targets and relative_path not in doc.body:
            missing_docs.append(relative_path)

    detail = (
        "Bundled docs and metadata are surfaced from SKILL.md."
        if not missing_docs
        else "Bundled docs are not surfaced from SKILL.md: "
        + ", ".join(missing_docs[:5])
    )
    return CheckRecord(
        check="ST-bundled-docs-mentioned",
        passed=not missing_docs,
        level="important",
        detail=detail,
    )


def _check_progressive_disclosure(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    body_lines = body_line_count(doc.body)
    has_reference_links = any(
        link.target.startswith("references/") for link in relative_links(doc.body)
    )
    passed = body_lines <= PROGRESSIVE_DISCLOSURE_LINES or has_reference_links
    detail = (
        f"Body has {body_lines} lines and uses linked references."
        if passed
        else (
            f"Body has {body_lines} lines without linked references. "
            "Move detail into references/."
        )
    )
    return CheckRecord(
        check="ST-progressive-disclosure",
        passed=passed,
        level="important",
        detail=detail,
    )


def _check_long_ref_toc(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    missing_toc: list[str] = []
    for path in doc.resource_files:
        relative_path = file_relative_to(path, doc.skill_dir)
        if not relative_path.startswith("references/") or path.suffix != ".md":
            continue
        lines = read_text(path).splitlines()
        if len(lines) <= LONG_REFERENCE_LINES:
            continue
        preview = "\n".join(lines[:40]).lower()
        if "table of contents" not in preview:
            missing_toc.append(relative_path)

    detail = (
        "All long reference files include a table of contents."
        if not missing_toc
        else "Long references without a table of contents: "
        + ", ".join(missing_toc[:5])
    )
    return CheckRecord(
        check="ST-long-ref-toc",
        passed=not missing_toc,
        level="info",
        detail=detail,
    )


def _is_surface_doc(relative_path: str) -> bool:
    return (
        relative_path.startswith("references/")
        or relative_path == AGENT_METADATA_PATH
    )


def _slash_prefixed_links(markdown: str) -> list[tuple[str, int]]:
    matches: list[tuple[str, int]] = []
    pattern = re.compile(r"\[([^\]]+)\]\((/[^)]+)\)")
    for match in pattern.finditer(markdown):
        line = markdown.count("\n", 0, match.start()) + 1
        matches.append((match.group(2).strip(), line))
    return matches


CHECKS = {
    "ST-links-resolve": _check_links_resolve,
    "ST-read-directives": _check_read_directives,
    "ST-bundled-docs-mentioned": _check_bundled_docs_mentioned,
    "ST-progressive-disclosure": _check_progressive_disclosure,
    "ST-long-ref-toc": _check_long_ref_toc,
}


def run_checks(
    skill_dir: Path,
    collector: ResultCollector,
    *,
    selected: set[str] | None = None,
) -> None:
    """Run structure checks for a skill directory."""
    names = selected or set(CHECKS)
    for check_id, check_fn in CHECKS.items():
        if check_id in names:
            collector.emit(check_fn(skill_dir))


def main(argv: list[str] | None = None) -> int:
    """Run structure checks as a CLI."""
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
