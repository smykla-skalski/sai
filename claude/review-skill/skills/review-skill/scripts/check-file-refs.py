#!/usr/bin/env python3
"""Validate SKILL.md file reference and path-format checks.

Sub-checks:
- `FR-resolves`
- `FR-no-backslash`
- `FR-no-disallowed`
- `FR-one-level`
- `FR-mentions-file`
- `FR-link-format`
- `FR-ref-link-format`

Output is NDJSON with a summary line.
Exit codes: 0 (all pass), 1 (any fail), 2 (usage/input error).
"""

from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

from _skill_check_common import (
    DEFAULT_TEXT_REFERENCE_SUFFIXES,
    RESOURCE_SUBDIRECTORIES,
    SNIPPET_WIDTH,
    CheckRecord,
    SkillDocument,
    find_plugin_root,
    read_text,
    run_check_cli,
    strip_fenced_code_blocks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHECK_FILE_REF_RESOLVES: Final[str] = "FR-resolves"
CHECK_NO_BACKSLASH_PATHS: Final[str] = "FR-no-backslash"
CHECK_NO_DISALLOWED_FILES: Final[str] = "FR-no-disallowed"
CHECK_REFS_ONE_LEVEL: Final[str] = "FR-one-level"
CHECK_SKILL_MENTIONS_FILE: Final[str] = "FR-mentions-file"
CHECK_REF_LINK_FORMAT: Final[str] = "FR-link-format"
CHECK_REF_LINK_FORMAT_FILES: Final[str] = "FR-ref-link-format"

LINK_FORMAT_SUBDIRS: Final[tuple[str, ...]] = ("references", "examples")

DISALLOWED_FILES: Final[tuple[str, ...]] = (
    "README.md",
    "CHANGELOG.md",
    "INSTALLATION_GUIDE.md",
)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

RESOURCE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"(?:references|scripts|assets|examples)/[a-zA-Z0-9._-]+(?:/[a-zA-Z0-9._-]+)*",
)
IGNORE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"/(?:\.\.\.|\.\.|foo\.|bar\.|baz\.|example\.)",
)
BACKSLASH_PATH_RE: Final[Pattern[str]] = re.compile(
    r"(?:references|scripts|assets|examples)\\[a-zA-Z0-9._-]+",
)
INLINE_CODE_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"`(?:references|examples)/[a-zA-Z0-9._-]+(?:/[a-zA-Z0-9._-]+)*`",
)

CROSS_REFERENCE_RE: Final[Pattern[str]] = re.compile(
    r"references/[a-zA-Z0-9._-]+",
)
DOUBLE_QUOTED_RE: Final[Pattern[str]] = re.compile(r'"[^"]*"')
INLINE_CODE_RE: Final[Pattern[str]] = re.compile(r"`[^`]*`")

PATH_CHAR_RE: Final[str] = r"[a-zA-Z0-9._-]"

MARKDOWN_LINK_RE: Final[Pattern[str]] = re.compile(r"\[[^\]]*\]\([^)]*\)")
EXAMPLE_OPEN_TAG_RE: Final[Pattern[str]] = re.compile(
    r"<example(?:\s[^>]*)?>",
    re.IGNORECASE,
)
EXAMPLE_CLOSE_TAG_RE: Final[Pattern[str]] = re.compile(
    r"</example>",
    re.IGNORECASE,
)
BLOCKQUOTE_LINE_RE: Final[Pattern[str]] = re.compile(r"^\s*>")

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


def _has_cross_reference(
    content: str,
    *,
    sibling_names: frozenset[str] = frozenset(),
) -> bool:
    """Return whether prose contains cross-references to other reference files.

    Checks two patterns:
    1. Explicit ``references/filename`` paths (strips inline code)
    2. Bare sibling filenames like ``sources.md`` (does NOT strip inline code -
       backtick-wrapped sibling names are still cross-references)
    """
    stripped = strip_fenced_code_blocks(content)
    normalized = _remove_non_signal_segments(stripped)
    if CROSS_REFERENCE_RE.search(normalized):
        return True

    if sibling_names:
        for name in sibling_names:
            sibling_re = re.compile(rf"\b{re.escape(name)}\b")
            if sibling_re.search(stripped):
                return True

    return False


def _strip_example_blocks(text: str) -> str:
    """Remove content between <example> and </example> tags."""
    lines: list[str] = []
    in_example = False
    for line in text.splitlines():
        if not in_example and EXAMPLE_OPEN_TAG_RE.search(line):
            in_example = True
            continue
        if in_example and EXAMPLE_CLOSE_TAG_RE.search(line):
            in_example = False
            continue
        if not in_example:
            lines.append(line)
    return "\n".join(lines)


def _prepare_prose_for_link_check(content: str) -> str:
    """Strip non-prose regions from file content for backtick link checking.

    Removes fenced code blocks, <example> tag content, markdown link
    constructs (so backtick-formatted link text doesn't false-positive),
    and blockquote lines.
    """
    text = strip_fenced_code_blocks(content)
    text = _strip_example_blocks(text)
    text = MARKDOWN_LINK_RE.sub("", text)
    lines = [line for line in text.splitlines() if not BLOCKQUOTE_LINE_RE.match(line)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_file_ref_resolves(document: SkillDocument) -> list[CheckRecord]:
    """Validate that resource references resolve from skill directory."""
    references = _extract_referenced_paths(document.prose_body)
    if not references:
        return [
            CheckRecord(
                check=CHECK_FILE_REF_RESOLVES,
                passed=True,
                detail="No file references found in SKILL.md",
                tier="C3",
            ),
        ]

    plugin_root = find_plugin_root(document.skill_dir)
    results: list[CheckRecord] = []

    for reference in references:
        expected_path = document.skill_dir / reference
        if expected_path.is_file() or expected_path.is_dir():
            results.append(
                CheckRecord(
                    check=CHECK_FILE_REF_RESOLVES,
                    passed=True,
                    detail=f"Reference '{reference}' resolves in skill directory",
                    tier="C3",
                ),
            )
            continue

        plugin_root_path = plugin_root / reference if plugin_root is not None else None
        if plugin_root_path is not None and (
            plugin_root_path.is_file() or plugin_root_path.is_dir()
        ):
            results.append(
                CheckRecord(
                    check=CHECK_FILE_REF_RESOLVES,
                    passed=False,
                    detail=(
                        f"Reference '{reference}' found at plugin root but not in "
                        f"skill directory - move to {expected_path}"
                    ),
                    tier="C3",
                ),
            )
            continue

        results.append(
            CheckRecord(
                check=CHECK_FILE_REF_RESOLVES,
                passed=False,
                detail=(
                    f"Reference '{reference}' not found - expected at {expected_path}"
                ),
                tier="C3",
            ),
        )

    return results


def check_no_backslash_paths(document: SkillDocument) -> list[CheckRecord]:
    """Validate that resource paths use forward slashes."""
    hits = BACKSLASH_PATH_RE.findall(document.prose_body)
    if not hits:
        return [
            CheckRecord(
                check=CHECK_NO_BACKSLASH_PATHS,
                passed=True,
                detail="No Windows-style backslash paths found",
                tier="P6",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_NO_BACKSLASH_PATHS,
            passed=False,
            detail=f"Windows-style backslash path found: {hit} - use forward slashes",
            tier="P6",
        )
        for hit in hits
    ]


def check_no_disallowed_files(document: SkillDocument) -> list[CheckRecord]:
    """Validate that known disallowed files are absent in skill directory."""
    results: list[CheckRecord] = []

    for filename in DISALLOWED_FILES:
        file_path = document.skill_dir / filename
        if file_path.is_file():
            results.append(
                CheckRecord(
                    check=CHECK_NO_DISALLOWED_FILES,
                    passed=False,
                    detail=f"Disallowed file '{filename}' found in skill directory",
                ),
            )
            continue

        results.append(
            CheckRecord(
                check=CHECK_NO_DISALLOWED_FILES,
                passed=True,
                detail=f"'{filename}' not present (correct)",
            ),
        )

    return results


def check_refs_one_level(document: SkillDocument) -> list[CheckRecord]:
    """Validate references files do not cross-reference each other directly."""
    references_dir = document.skill_dir / "references"
    if not references_dir.is_dir():
        return []

    # Collect all reference filenames for sibling detection
    ref_files: list[tuple[str, str]] = []
    for path in sorted(references_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        ref_files.append((path.name, read_text(path)))

    all_names = frozenset(name for name, _ in ref_files)

    results: list[CheckRecord] = []
    for name, content in ref_files:
        siblings = all_names - {name}
        has_xref = _has_cross_reference(content, sibling_names=siblings)
        if has_xref:
            results.append(
                CheckRecord.info(
                    check=CHECK_REFS_ONE_LEVEL,
                    detail=(
                        f"Reference '{name}' cross-references other reference files"
                    ),
                ),
            )
            continue

        results.append(
            CheckRecord(
                check=CHECK_REFS_ONE_LEVEL,
                passed=True,
                detail=f"Reference '{name}' does not cross-reference other files",
            ),
        )

    return results


def check_skill_md_mentions_file(document: SkillDocument) -> list[CheckRecord]:
    """Validate that SKILL.md mentions all bundled top-level resource files."""
    results: list[CheckRecord] = []

    for subdir in RESOURCE_SUBDIRECTORIES:
        subdir_path = document.skill_dir / subdir
        if not subdir_path.is_dir():
            continue

        for path in sorted(subdir_path.iterdir()):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.name.startswith("_"):
                continue
            if path.suffix in {".toml", ".cfg", ".ini"}:
                continue

            relative_path = f"{subdir}/{path.name}"
            full_re = re.compile(
                rf"(?<!{PATH_CHAR_RE}){re.escape(relative_path)}(?!{PATH_CHAR_RE})",
            )
            bare_re = re.compile(
                rf"(?<!{PATH_CHAR_RE}){re.escape(path.name)}(?!{PATH_CHAR_RE})",
            )
            if full_re.search(document.content) or bare_re.search(document.content):
                results.append(
                    CheckRecord(
                        check=CHECK_SKILL_MENTIONS_FILE,
                        passed=True,
                        detail=f"SKILL.md mentions '{relative_path}'",
                        tier="P3",
                    ),
                )
                continue

            results.append(
                CheckRecord(
                    check=CHECK_SKILL_MENTIONS_FILE,
                    passed=False,
                    detail=(
                        f"SKILL.md does not mention '{relative_path}' - all "
                        "bundled files should be referenced"
                    ),
                    tier="P3",
                ),
            )

    return results


def check_ref_link_format(document: SkillDocument) -> list[CheckRecord]:
    """Validate reference paths use markdown links, not inline-code paths."""
    hits = INLINE_CODE_REFERENCE_RE.findall(document.prose_body)
    if not hits:
        return [
            CheckRecord(
                check=CHECK_REF_LINK_FORMAT,
                passed=True,
                detail="Reference file paths use markdown link format",
                tier="I15",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_REF_LINK_FORMAT,
            passed=False,
            detail=(
                "Inline code reference path - use markdown link "
                f"[file](path) for progressive disclosure: {hit[:SNIPPET_WIDTH]}"
            ),
            tier="I15",
        )
        for hit in hits
    ]


def _scan_file_for_backtick_refs(
    document: SkillDocument,
    path: Path,
) -> list[CheckRecord]:
    """Scan one text file for backtick-wrapped resource paths.

    Only flags paths that resolve to an existing file in the skill
    directory (hypothetical example paths are not flagged).
    """
    content = read_text(path)
    prepared = _prepare_prose_for_link_check(content)
    hits = INLINE_CODE_REFERENCE_RE.findall(prepared)
    rel_path = path.relative_to(document.skill_dir).as_posix()

    results: list[CheckRecord] = []
    for hit in hits:
        bare_path = hit.strip("`")
        if not (document.skill_dir / bare_path).is_file():
            continue
        results.append(
            CheckRecord(
                check=CHECK_REF_LINK_FORMAT_FILES,
                passed=False,
                detail=(
                    f"Backtick path in '{rel_path}' - use markdown link "
                    f"[file](path) for progressive disclosure: "
                    f"{hit[:SNIPPET_WIDTH]}"
                ),
                tier="I15",
            ),
        )
    return results


def check_ref_link_format_in_files(document: SkillDocument) -> list[CheckRecord]:
    """Validate referenced files use markdown links for resource paths.

    Scans text files under references/ and examples/ for backtick-wrapped
    resource paths that should be markdown links for progressive disclosure.
    Excludes content inside fenced code blocks, <example> tags, markdown
    link constructs, and blockquote lines.  Only flags paths that resolve
    to an existing file in the skill directory (hypothetical example paths
    like ``references/api.md`` are not flagged when the file does not exist).
    """
    results: list[CheckRecord] = []
    scanned = 0

    for subdir in LINK_FORMAT_SUBDIRS:
        subdir_path = document.skill_dir / subdir
        if not subdir_path.is_dir():
            continue

        for path in sorted(subdir_path.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.name.startswith("_"):
                continue
            if path.suffix.lower() not in DEFAULT_TEXT_REFERENCE_SUFFIXES:
                continue

            scanned += 1
            results.extend(_scan_file_for_backtick_refs(document, path))

    if not results:
        if scanned == 0:
            return [
                CheckRecord.skip(
                    CHECK_REF_LINK_FORMAT_FILES,
                    "No text files in references/ or examples/ to check",
                    tier="I15",
                ),
            ]
        return [
            CheckRecord(
                check=CHECK_REF_LINK_FORMAT_FILES,
                passed=True,
                detail=(
                    f"All {scanned} text file(s) in references/examples "
                    "use markdown link format"
                ),
                tier="I15",
            ),
        ]

    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    CheckRunner = Callable[[SkillDocument], list[CheckRecord]]

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_FILE_REF_RESOLVES,
    CHECK_NO_BACKSLASH_PATHS,
    CHECK_NO_DISALLOWED_FILES,
    CHECK_REFS_ONE_LEVEL,
    CHECK_SKILL_MENTIONS_FILE,
    CHECK_REF_LINK_FORMAT,
    CHECK_REF_LINK_FORMAT_FILES,
)

CHECK_RUNNERS: Final[dict[str, CheckRunner]] = {
    CHECK_FILE_REF_RESOLVES: check_file_ref_resolves,
    CHECK_NO_BACKSLASH_PATHS: check_no_backslash_paths,
    CHECK_NO_DISALLOWED_FILES: check_no_disallowed_files,
    CHECK_REFS_ONE_LEVEL: check_refs_one_level,
    CHECK_SKILL_MENTIONS_FILE: check_skill_md_mentions_file,
    CHECK_REF_LINK_FORMAT: check_ref_link_format,
    CHECK_REF_LINK_FORMAT_FILES: check_ref_link_format_in_files,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...],
) -> list[CheckRecord]:
    """Run selected checks in stable output order."""
    selected = frozenset(selected_checks)
    checks_to_run = [
        check_name
        for check_name in CHECK_ORDER
        if not selected or check_name in selected
    ]

    results: list[CheckRecord] = []
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
