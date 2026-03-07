#!/usr/bin/env python3
"""Validate script invocation and runnable script permissions for a skill.

Sub-checks:
- `script-invocation-prefix`
- `no-bash-prefix`
- `script-executable`

Output is NDJSON with one final summary line.
Exit codes:
- 0 when all checks pass
- 1 when any check fails
- 2 for usage/input errors
"""

from __future__ import annotations

import argparse
import re
import stat
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckResult,
    ProseLine,
    SkillDocument,
    SkillLoadError,
    emit_error,
    emit_results,
    extract_prose_lines,
    format_hit,
    load_skill_document,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_SCRIPT_INVOCATION_PREFIX: Final[str] = "script-invocation-prefix"
CHECK_NO_BASH_PREFIX: Final[str] = "no-bash-prefix"
CHECK_SCRIPT_EXECUTABLE: Final[str] = "script-executable"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_SCRIPT_INVOCATION_PREFIX,
    CHECK_NO_BASH_PREFIX,
    CHECK_SCRIPT_EXECUTABLE,
)

# ---------------------------------------------------------------------------
# Patterns and constants
# ---------------------------------------------------------------------------

SCRIPT_PATH_RE: Final[Pattern[str]] = re.compile(
    r"scripts/(?:[a-zA-Z0-9._-]+/)*[a-zA-Z0-9._-]+\.(?:sh|py)\b",
)
HEADING_LINE_RE: Final[Pattern[str]] = re.compile(r"^\s*#{1,6}\s")
BASH_INVOCATION_PREFIX_RE: Final[Pattern[str]] = re.compile(
    r"^\s*(?:command\s+)?(?:(?:/usr/bin/|/bin/)?env\s+)?bash\b",
)

FENCE_START_RE: Final[Pattern[str]] = re.compile(
    r"^\s*```\s*(?P<language>[a-zA-Z0-9_-]+)?.*$",
)

LIST_PREFIX_RE: Final[Pattern[str]] = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)")
RUN_VERB_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:run|execute|invoke)\b",
    re.IGNORECASE,
)

COMMAND_FENCE_LANGUAGES: Final[frozenset[str]] = frozenset(
    {"", "bash", "sh", "shell", "zsh", "console", "terminal"},
)

SCRIPT_EXTENSIONS: Final[frozenset[str]] = frozenset({".sh", ".py"})
CLAUDE_PREFIX_ENDINGS: Final[tuple[str, ...]] = (
    "${CLAUDE_SKILL_DIR}/",
    '"${CLAUDE_SKILL_DIR}/',
    "'${CLAUDE_SKILL_DIR}/",
    '"${CLAUDE_SKILL_DIR}"/',
    "'${CLAUDE_SKILL_DIR}'/",
)
SHEBANG_PREFIX: Final[str] = "#!"
EXECUTABLE_MODE_MASK: Final[int] = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
MAX_LISTED_EXAMPLES: Final[int] = 5
CONTINUATION_DIVISOR: Final[int] = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_trailing_continuation(text: str) -> bool:
    """Return whether text ends with a line continuation backslash."""
    trailing = len(text) - len(text.rstrip("\\"))
    return trailing % CONTINUATION_DIVISOR == 1


def _has_required_prefix(line_text: str, script_start: int) -> bool:
    """Return whether script path has required variable prefix immediately before it."""
    prefix_region = line_text[:script_start]
    return prefix_region.endswith(CLAUDE_PREFIX_ENDINGS)


def _has_scripts_dir(document: SkillDocument) -> bool:
    """Return whether skill has a scripts/ directory."""
    return (document.skill_dir / "scripts").is_dir()


def _strip_list_prefix(text: str) -> str:
    """Remove leading markdown bullet or ordered-list prefix."""
    return LIST_PREFIX_RE.sub("", text, count=1).lstrip()


def _line_hit(document: SkillDocument, line: ProseLine) -> str:
    """Format a matching line as `L<line>: <snippet>`."""
    return format_hit(
        line.index,
        line.text,
        body_start_line=document.body_start_line,
    )


def _iter_command_fence_lines(body: str) -> Iterator[ProseLine]:
    """Yield lines inside command-like fenced code blocks."""
    in_fence = False
    in_command_fence = False

    for index, line in enumerate(body.splitlines()):
        fence_match = FENCE_START_RE.match(line)
        if fence_match is not None:
            if not in_fence:
                in_fence = True
                language = (fence_match.group("language") or "").lower()
                in_command_fence = language in COMMAND_FENCE_LANGUAGES
            else:
                in_fence = False
                in_command_fence = False
            continue

        if in_fence and in_command_fence:
            yield ProseLine(index=index, text=line)


def _iter_command_fence_commands(body: str) -> Iterator[ProseLine]:
    """Yield logical command lines merged across trailing backslashes."""
    pending_text = ""
    pending_index: int | None = None

    for line in _iter_command_fence_lines(body):
        stripped = line.text.strip()

        if not stripped or stripped.startswith("#"):
            if pending_text and pending_index is not None:
                yield ProseLine(index=pending_index, text=pending_text)
                pending_text = ""
                pending_index = None
            continue

        if pending_index is None:
            pending_text = stripped
            pending_index = line.index
        else:
            pending_text = f"{pending_text} {stripped}"

        if _has_trailing_continuation(pending_text):
            pending_text = pending_text[:-1].rstrip()
            continue

        yield ProseLine(index=pending_index, text=pending_text)
        pending_text = ""
        pending_index = None

    if pending_text and pending_index is not None:
        yield ProseLine(index=pending_index, text=pending_text)


def _is_command_like_prose_line(text: str) -> bool:
    """Return whether prose line likely describes a script invocation."""
    stripped = text.strip()
    if not stripped or HEADING_LINE_RE.match(stripped):
        return False

    line = _strip_list_prefix(stripped)
    script_match = SCRIPT_PATH_RE.search(line)
    if script_match is None:
        return False

    if BASH_INVOCATION_PREFIX_RE.match(line):
        return True
    if _has_required_prefix(line, script_match.start()):
        return True

    return RUN_VERB_RE.search(line[: script_match.start()]) is not None


def _iter_invocation_lines(document: SkillDocument) -> Iterator[ProseLine]:
    """Yield lines where script-invocation checks should run."""
    yield from _iter_command_fence_commands(document.body)

    for line in extract_prose_lines(document.body):
        if _is_command_like_prose_line(line.text):
            yield line


def _read_first_line(path: Path) -> str | None:
    """Read first line using UTF-8 replacement. Return None on read error."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            return handle.readline()
    except OSError:
        return None


def _iter_script_files(scripts_dir: Path) -> Iterator[Path]:
    """Yield files under scripts/ recursively in stable sorted order."""
    file_paths: list[Path] = []

    for path in scripts_dir.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(scripts_dir).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        file_paths.append(path)

    for path in sorted(
        file_paths,
        key=lambda item: item.relative_to(scripts_dir).as_posix(),
    ):
        yield path


def _collect_runnable_scripts(
    scripts_dir: Path,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    """Return runnable entrypoints and read-error paths."""
    runnable: list[Path] = []
    read_errors: list[str] = []

    for path in _iter_script_files(scripts_dir):
        if path.suffix.lower() not in SCRIPT_EXTENSIONS:
            continue

        rel = path.relative_to(scripts_dir).as_posix()
        first_line = _read_first_line(path)
        if first_line is None:
            read_errors.append(rel)
            continue
        if first_line.startswith(SHEBANG_PREFIX):
            runnable.append(path)

    return tuple(runnable), tuple(read_errors)


def _has_executable_bit(path: Path) -> bool | None:
    """Return executable-bit state, or None if stat fails."""
    try:
        mode = path.stat().st_mode
    except OSError:
        return None
    return (mode & EXECUTABLE_MODE_MASK) != 0


def _format_examples(items: list[str]) -> str:
    """Format first MAX_LISTED_EXAMPLES values and overflow suffix."""
    shown = ", ".join(items[:MAX_LISTED_EXAMPLES])
    overflow = max(0, len(items) - MAX_LISTED_EXAMPLES)
    if overflow <= 0:
        return shown
    return f"{shown} (+{overflow} more)"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_script_invocation_prefix(document: SkillDocument) -> list[CheckResult]:
    """Validate `${CLAUDE_SKILL_DIR}` prefix usage for script invocations."""
    if not _has_scripts_dir(document):
        return []

    violations: list[str] = []
    seen_lines: set[int] = set()
    for line in _iter_invocation_lines(document):
        for match in SCRIPT_PATH_RE.finditer(line.text):
            if _has_required_prefix(line.text, match.start()):
                continue
            if line.index in seen_lines:
                break
            seen_lines.add(line.index)
            violations.append(_line_hit(document, line))
            break

    if violations:
        return [
            CheckResult(
                check=CHECK_SCRIPT_INVOCATION_PREFIX,
                passed=False,
                detail=(
                    f"Found {len(violations)} script invocation line(s) without "
                    "${CLAUDE_SKILL_DIR} prefix - use "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." - '
                    f"first: {violations[0]}"
                ),
            ),
        ]

    return [
        CheckResult(
            check=CHECK_SCRIPT_INVOCATION_PREFIX,
            passed=True,
            detail="All detected script invocations use ${CLAUDE_SKILL_DIR} prefix",
        ),
    ]


def check_no_bash_prefix(document: SkillDocument) -> list[CheckResult]:
    """Validate that script invocations do not start with `bash` prefix."""
    if not _has_scripts_dir(document):
        return []

    violations: list[str] = []
    seen_lines: set[int] = set()
    for line in _iter_invocation_lines(document):
        command_text = _strip_list_prefix(line.text.strip())
        if not command_text:
            continue
        if BASH_INVOCATION_PREFIX_RE.match(command_text) is None:
            continue
        if SCRIPT_PATH_RE.search(command_text) is None:
            continue
        if line.index in seen_lines:
            continue
        seen_lines.add(line.index)
        violations.append(_line_hit(document, line))

    if violations:
        return [
            CheckResult(
                check=CHECK_NO_BASH_PREFIX,
                passed=False,
                detail=(
                    f"Found {len(violations)} script invocation(s) using bash "
                    "prefix - invoke directly via "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." and set executable bit '
                    f"- first: {violations[0]}"
                ),
            ),
        ]

    return [
        CheckResult(
            check=CHECK_NO_BASH_PREFIX,
            passed=True,
            detail="No bash-prefixed script invocations found",
        ),
    ]


def check_script_executable(document: SkillDocument) -> list[CheckResult]:
    """Validate executable bits for runnable script entrypoints only."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    runnable_scripts, read_errors = _collect_runnable_scripts(scripts_dir)

    missing_exec: list[str] = []
    stat_errors: list[str] = []
    for path in runnable_scripts:
        rel = path.relative_to(scripts_dir).as_posix()
        has_exec = _has_executable_bit(path)
        if has_exec is None:
            stat_errors.append(rel)
            continue
        if not has_exec:
            missing_exec.append(rel)

    issues: list[str] = []
    if read_errors:
        issues.append(
            "unable to read "
            f"{len(read_errors)} script file(s) for shebang detection: "
            f"{_format_examples(list(read_errors))}",
        )
    if stat_errors:
        issues.append(
            "unable to stat "
            f"{len(stat_errors)} runnable script(s): "
            f"{_format_examples(stat_errors)}",
        )
    if missing_exec:
        issues.append(
            f"{len(missing_exec)} runnable script(s) missing executable bit: "
            f"{_format_examples(missing_exec)}",
        )

    if issues:
        return [
            CheckResult(
                check=CHECK_SCRIPT_EXECUTABLE,
                passed=False,
                detail="; ".join(issues),
            ),
        ]

    if not runnable_scripts:
        return [
            CheckResult(
                check=CHECK_SCRIPT_EXECUTABLE,
                passed=True,
                detail="No runnable script entrypoints found in scripts/",
            ),
        ]

    return [
        CheckResult(
            check=CHECK_SCRIPT_EXECUTABLE,
            passed=True,
            detail=(
                f"All {len(runnable_scripts)} runnable script entrypoint(s) "
                "in scripts/ have executable bit set"
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], list[CheckResult]]]] = {
    CHECK_SCRIPT_INVOCATION_PREFIX: check_script_invocation_prefix,
    CHECK_NO_BASH_PREFIX: check_no_bash_prefix,
    CHECK_SCRIPT_EXECUTABLE: check_script_executable,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckResult]:
    """Run all script-dir checks and return results in stable order."""
    selected = frozenset(selected_checks)
    results: list[CheckResult] = []

    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        results.extend(CHECK_FUNCTIONS[check_name](document))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build and return command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate scripts directory invocation and executability checks.",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=CHECK_ORDER,
        dest="checks",
        help=(
            "Run only specified check (repeatable): "
            "script-invocation-prefix, no-bash-prefix, script-executable"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI entry point and return process exit code."""
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
