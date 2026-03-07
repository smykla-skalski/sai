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

import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    RESOURCE_SUBDIRECTORIES,
    SNIPPET_WIDTH,
    CheckResult,
    SkillDocument,
    find_plugin_root,
    read_text,
    run_check_cli,
    strip_fenced_code_blocks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHECK_FILE_REF_RESOLVES: Final[str] = "file-ref-resolves"
CHECK_NO_BACKSLASH_PATHS: Final[str] = "no-backslash-paths"
CHECK_NO_DISALLOWED_FILES: Final[str] = "no-disallowed-files"
CHECK_REFS_ONE_LEVEL: Final[str] = "refs-one-level"
CHECK_SKILL_MENTIONS_FILE: Final[str] = "skill-md-mentions-file"
CHECK_REF_LINK_FORMAT: Final[str] = "ref-link-format"

DISALLOWED_FILES: Final[tuple[str, ...]] = (
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

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

CROSS_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"references/[a-zA-Z0-9._-]+",
)
DOUBLE_QUOTED_RE: Final[Pattern[str]] = re.compile(r'"[^"]*"')
INLINE_CODE_RE: Final[Pattern[str]] = re.compile(r"`[^`]*`")

PATH_CHAR_RE: Final[str] = r"[a-zA-Z0-9._-]"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_referenced_paths(prose_body: str) -> tuple[str, ...]:
    """Extract normalized resource references from prose body."""
    references = {
        match
        for match in RESOURCE_REFERENCE_RE.findall(prose_body)
        if not IGNORE_REFERENCE_RE.search(match)
    }
    return tuple(sorted(references))


def _remove_non_signal_segments(text: str) -> str:
    """Remove quoted and inline-code segments from reference text."""
    without_quotes = DOUBLE_QUOTED_RE.sub("", text)
    return INLINE_CODE_RE.sub("", without_quotes)


def _has_cross_reference(content: str) -> bool:
    """Return whether prose contains any references/ path cross-reference."""
    stripped = strip_fenced_code_blocks(content)
    normalized = _remove_non_signal_segments(stripped)
    return bool(CROSS_REFERENCE_RE.search(normalized))


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


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

    plugin_root = find_plugin_root(document.skill_dir)
    results: list[CheckResult] = []

    for reference in references:
        expected_path = document.skill_dir / reference
        if expected_path.is_file():
            results.append(
                CheckResult(
                    check=CHECK_FILE_REF_RESOLVES,
                    passed=True,
                    detail=f"Reference '{reference}' resolves in skill directory",
                ),
            )
            continue

        plugin_root_path = plugin_root / reference if plugin_root is not None else None
        if plugin_root_path is not None and plugin_root_path.is_file():
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
    hits = BACKSLASH_PATH_RE.findall(document.prose_body)
    if not hits:
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
            detail=f"Windows-style backslash path found: {hit} - use forward slashes",
        )
        for hit in hits
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


def check_refs_one_level(document: SkillDocument) -> list[CheckResult]:
    """Validate references files do not cross-reference each other directly."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    results: list[CheckResult] = []
    for path in sorted(references_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue

        has_xref = _has_cross_reference(read_text(path))
        if has_xref:
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

    for subdir in RESOURCE_SUBDIRECTORIES:
        subdir_path = document.skill_dir / subdir
        if not subdir_path.is_dir():
            continue

        for path in sorted(subdir_path.iterdir()):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue

            relative_path = f"{subdir}/{path.name}"
            boundary_re = re.compile(
                rf"(?<!{PATH_CHAR_RE}){re.escape(relative_path)}(?!{PATH_CHAR_RE})",
            )
            if boundary_re.search(document.content):
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

    return [
        CheckResult(
            check=CHECK_REF_LINK_FORMAT,
            passed=False,
            detail=(
                "Inline code reference path - use markdown link "
                f"[file](path) for progressive disclosure: {hit[:SNIPPET_WIDTH]}"
            ),
        )
        for hit in hits
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run checks and return the process exit code."""
    return run_check_cli(
        "Validate skill file-reference and path-format checks.",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
