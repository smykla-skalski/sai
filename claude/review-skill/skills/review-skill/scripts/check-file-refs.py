#!/usr/bin/env python3
"""Validate SKILL.md file reference and path-format checks.

Sub-checks:
- `file-ref-resolves`
- `no-backslash-paths`
- `no-disallowed-files`
- `refs-one-level`
- `skill-md-mentions-file`
- `ref-link-format`

Output is NDJSON with a summary line.
Exit codes: 0 (all pass), 1 (any fail), 2 (usage/input error).
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Callable
from pathlib import Path
from re import Pattern
from typing import Final

from skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckResult,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    load_skill_document,
    strip_fenced_code_blocks,
)

CHECK_FILE_REF_RESOLVES: Final[str] = "file-ref-resolves"
CHECK_NO_BACKSLASH_PATHS: Final[str] = "no-backslash-paths"
CHECK_NO_DISALLOWED_FILES: Final[str] = "no-disallowed-files"
CHECK_REFS_ONE_LEVEL: Final[str] = "refs-one-level"
CHECK_SKILL_MENTIONS_FILE: Final[str] = "skill-md-mentions-file"
CHECK_REF_LINK_FORMAT: Final[str] = "ref-link-format"

RESOURCE_DIRS: Final[tuple[str, ...]] = (
    "references",
    "scripts",
    "assets",
    "examples",
)
DISALLOWED_FILES: Final[tuple[str, ...]] = (
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
)

RESOURCE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"(?:references|scripts|assets|examples)/[a-zA-Z0-9._-]+",
)
IGNORE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"/(?:\.\.\.|\.\.|[a-z]\.md|foo\.|bar\.|baz\.|example\.)",
)
BACKSLASH_PATH_RE: Final[Pattern[str]] = re.compile(
    r"(?:references|scripts|assets|examples)\\[a-zA-Z0-9._-]+",
)
INLINE_CODE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"`(?:references|examples)/[a-zA-Z0-9._-]+`",
)

BARE_REFERENCE_PARENS_RE: Final[Pattern[str]] = re.compile(
    r"\(references/[a-zA-Z0-9._-]+\)",
)
MARKDOWN_LINK_RE: Final[Pattern[str]] = re.compile(r"\]\(references/")
DOUBLE_QUOTED_RE: Final[Pattern[str]] = re.compile(r'"[^"]*"')
INLINE_CODE_RE: Final[Pattern[str]] = re.compile(r"`[^`]*`")

FIRST_HIT_WIDTH: Final[int] = 80


def _read_text(path: Path) -> str:
    """Read text from a file using UTF-8 with replacement."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_plugin_root(skill_dir: Path, *, max_depth: int = 4) -> Path | None:
    """Find plugin root by walking up for `.claude-plugin/plugin.json`."""
    search_dir = skill_dir.resolve()

    for _ in range(max_depth):
        search_dir = search_dir.parent
        plugin_manifest = search_dir / ".claude-plugin" / "plugin.json"
        if plugin_manifest.is_file():
            return search_dir

    return None


def _extract_referenced_paths(prose_body: str) -> tuple[str, ...]:
    """Extract normalized resource references from prose body."""
    references = {
        match
        for match in RESOURCE_REFERENCE_RE.findall(prose_body)
        if not IGNORE_REFERENCE_RE.search(match)
    }
    return tuple(sorted(references))


def check_file_ref_resolves(document: SkillDocument) -> list[CheckResult]:
    """Validate that resource references resolve from skill directory."""
    references = _extract_referenced_paths(document.prose_body)
    if not references:
        return [
            CheckResult(
                check=CHECK_FILE_REF_RESOLVES,
                passed=True,
                detail="No file references found in SKILL.md",
            ),
        ]

    plugin_root = _find_plugin_root(document.skill_dir)
    results: list[CheckResult] = []

    for reference in references:
        expected_path = document.skill_dir / reference
        if expected_path.exists():
            results.append(
                CheckResult(
                    check=CHECK_FILE_REF_RESOLVES,
                    passed=True,
                    detail=f"Reference '{reference}' resolves in skill directory",
                ),
            )
            continue

        plugin_root_path = plugin_root / reference if plugin_root is not None else None
        if plugin_root_path is not None and plugin_root_path.exists():
            results.append(
                CheckResult(
                    check=CHECK_FILE_REF_RESOLVES,
                    passed=False,
                    detail=(
                        f"Reference '{reference}' found at plugin root but not in "
                        f"skill directory - move to {expected_path}"
                    ),
                ),
            )
            continue

        results.append(
            CheckResult(
                check=CHECK_FILE_REF_RESOLVES,
                passed=False,
                detail=(
                    f"Reference '{reference}' not found - expected at {expected_path}"
                ),
            ),
        )

    return results


def check_no_backslash_paths(document: SkillDocument) -> list[CheckResult]:
    """Validate that resource paths use forward slashes."""
    first_hit = BACKSLASH_PATH_RE.search(document.prose_body)
    if first_hit is None:
        return [
            CheckResult(
                check=CHECK_NO_BACKSLASH_PATHS,
                passed=True,
                detail="No Windows-style backslash paths found",
            ),
        ]

    return [
        CheckResult(
            check=CHECK_NO_BACKSLASH_PATHS,
            passed=False,
            detail=(
                "Windows-style backslash path found: "
                f"{first_hit.group(0)} - use forward slashes"
            ),
        ),
    ]


def check_no_disallowed_files(document: SkillDocument) -> list[CheckResult]:
    """Validate that known disallowed files are absent in skill directory."""
    results: list[CheckResult] = []

    for filename in DISALLOWED_FILES:
        file_path = document.skill_dir / filename
        if file_path.is_file():
            results.append(
                CheckResult(
                    check=CHECK_NO_DISALLOWED_FILES,
                    passed=False,
                    detail=f"Disallowed file '{filename}' found in skill directory",
                ),
            )
            continue

        results.append(
            CheckResult(
                check=CHECK_NO_DISALLOWED_FILES,
                passed=True,
                detail=f"'{filename}' not present (correct)",
            ),
        )

    return results


def _remove_non_signal_segments(text: str) -> str:
    """Remove quoted and inline-code segments from reference text."""
    without_quotes = DOUBLE_QUOTED_RE.sub("", text)
    return INLINE_CODE_RE.sub("", without_quotes)


def _contains_cross_reference(content: str) -> bool:
    """Return whether prose contains bare `(references/...)` paths."""
    stripped = strip_fenced_code_blocks(content)
    normalized = _remove_non_signal_segments(stripped)

    for line in normalized.splitlines():
        if not BARE_REFERENCE_PARENS_RE.search(line):
            continue
        if MARKDOWN_LINK_RE.search(line):
            continue
        return True

    return False


def check_refs_one_level(document: SkillDocument) -> list[CheckResult]:
    """Validate references files do not cross-reference each other directly."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    results: list[CheckResult] = []
    for path in sorted(references_dir.iterdir()):
        if not path.is_file():
            continue

        has_cross_reference = _contains_cross_reference(_read_text(path))
        if has_cross_reference:
            results.append(
                CheckResult(
                    check=CHECK_REFS_ONE_LEVEL,
                    passed=False,
                    detail=(
                        f"Reference '{path.name}' cross-references other "
                        "reference files"
                    ),
                ),
            )
            continue

        results.append(
            CheckResult(
                check=CHECK_REFS_ONE_LEVEL,
                passed=True,
                detail=(
                    f"Reference '{path.name}' does not cross-reference other files"
                ),
            ),
        )

    return results


def check_skill_md_mentions_file(document: SkillDocument) -> list[CheckResult]:
    """Validate that SKILL.md mentions all bundled top-level resource files."""
    results: list[CheckResult] = []

    for subdir in RESOURCE_DIRS:
        subdir_path = document.skill_dir / subdir
        if not subdir_path.is_dir():
            continue

        for path in sorted(subdir_path.iterdir()):
            if not path.is_file():
                continue

            relative_path = f"{subdir}/{path.name}"
            if relative_path in document.content:
                results.append(
                    CheckResult(
                        check=CHECK_SKILL_MENTIONS_FILE,
                        passed=True,
                        detail=f"SKILL.md mentions '{relative_path}'",
                    ),
                )
                continue

            results.append(
                CheckResult(
                    check=CHECK_SKILL_MENTIONS_FILE,
                    passed=False,
                    detail=(
                        f"SKILL.md does not mention '{relative_path}' - all "
                        "bundled files should be referenced"
                    ),
                ),
            )

    return results


def check_ref_link_format(document: SkillDocument) -> list[CheckResult]:
    """Validate reference paths use markdown links, not inline-code paths."""
    hits = INLINE_CODE_REFERENCE_RE.findall(document.prose_body)
    if not hits:
        return [
            CheckResult(
                check=CHECK_REF_LINK_FORMAT,
                passed=True,
                detail="Reference file paths use markdown link format",
            ),
        ]

    first_hit = hits[0][:FIRST_HIT_WIDTH]
    return [
        CheckResult(
            check=CHECK_REF_LINK_FORMAT,
            passed=False,
            detail=(
                f"Found {len(hits)} inline code reference(s) - use markdown "
                f"links [file](path) for progressive disclosure - first: {first_hit}"
            ),
        ),
    ]


CheckRunner = Callable[[SkillDocument], list[CheckResult]]

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_FILE_REF_RESOLVES,
    CHECK_NO_BACKSLASH_PATHS,
    CHECK_NO_DISALLOWED_FILES,
    CHECK_REFS_ONE_LEVEL,
    CHECK_SKILL_MENTIONS_FILE,
    CHECK_REF_LINK_FORMAT,
)

CHECK_RUNNERS: Final[dict[str, CheckRunner]] = {
    CHECK_FILE_REF_RESOLVES: check_file_ref_resolves,
    CHECK_NO_BACKSLASH_PATHS: check_no_backslash_paths,
    CHECK_NO_DISALLOWED_FILES: check_no_disallowed_files,
    CHECK_REFS_ONE_LEVEL: check_refs_one_level,
    CHECK_SKILL_MENTIONS_FILE: check_skill_md_mentions_file,
    CHECK_REF_LINK_FORMAT: check_ref_link_format,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...],
) -> list[CheckResult]:
    """Run selected checks in stable output order."""
    selected = frozenset(selected_checks)
    checks_to_run = [
        check_name
        for check_name in CHECK_ORDER
        if not selected or check_name in selected
    ]

    results: list[CheckResult] = []
    for check_name in checks_to_run:
        results.extend(CHECK_RUNNERS[check_name](document))
    return results


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate skill file-reference and path-format checks.",
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
    """Run checks and return the process exit code."""
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
