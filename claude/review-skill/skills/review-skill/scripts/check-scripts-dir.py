#!/usr/bin/env python3
"""Validate script invocation and runnable script permissions for a skill.

Sub-checks:
- `SD-invocation-prefix`
- `SD-no-bash`
- `SD-executable`
- `SD-legacy-bash-info`
- `SD-help-output-info`
- `SD-exit-codes-info`
- `SD-undeclared-deps-info`

Output is NDJSON with one final summary line.
Exit codes:
- 0 when all checks pass
- 1 when any check fails
- 2 for usage/input errors
"""

from __future__ import annotations

import re
import stat
import sys
from dataclasses import dataclass
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

from _skill_check_common import (
    CheckRecord,
    ProseLine,
    SkillDocument,
    SkipConfig,
    extract_prose_lines,
    format_hit,
    iter_fence_lines,
    iter_reference_inputs,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_SCRIPT_INVOCATION_PREFIX: Final[str] = "SD-invocation-prefix"
CHECK_NO_BASH_PREFIX: Final[str] = "SD-no-bash"
CHECK_SCRIPT_EXECUTABLE: Final[str] = "SD-executable"
CHECK_LEGACY_BASH_INFO: Final[str] = "SD-legacy-bash-info"
CHECK_HELP_OUTPUT_INFO: Final[str] = "SD-help-output-info"
CHECK_EXIT_CODES_INFO: Final[str] = "SD-exit-codes-info"
CHECK_UNDECLARED_DEPS_INFO: Final[str] = "SD-undeclared-deps-info"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_SCRIPT_INVOCATION_PREFIX,
    CHECK_NO_BASH_PREFIX,
    CHECK_SCRIPT_EXECUTABLE,
    CHECK_LEGACY_BASH_INFO,
    CHECK_HELP_OUTPUT_INFO,
    CHECK_EXIT_CODES_INFO,
    CHECK_UNDECLARED_DEPS_INFO,
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
MIN_DISTINCT_EXIT_CODES: Final[int] = 2

_POST_SHORT_FLAG_RE: Final[Pattern[str]] = re.compile(r"^\s+-[a-zA-Z]")
_POST_LONG_FLAG_RE: Final[Pattern[str]] = re.compile(r"^\s+--[a-zA-Z]")

_HELP_IMPORT_RE: Final[Pattern[str]] = re.compile(
    r"^(?:import\s+(?:argparse|click|typer)|from\s+(?:argparse|click|typer)\b)",
    re.MULTILINE,
)
_SHELL_HELP_CASE_RE: Final[Pattern[str]] = re.compile(r"--help\)")

_PY_EXIT_CODE_RE: Final[Pattern[str]] = re.compile(
    r"(?:sys\.exit|raise\s+SystemExit)\(\s*(\d+)\s*\)",
)
_SH_EXIT_CODE_RE: Final[Pattern[str]] = re.compile(
    r"\bexit\s+(\d+)\b",
)

_PY_IMPORT_RE: Final[Pattern[str]] = re.compile(
    r"^(?:import\s+(\w+)|from\s+(\w+))",
    re.MULTILINE,
)

_STDLIB_MODULES: Final[frozenset[str]] = (
    frozenset(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else frozenset(
        {
            "abc",
            "argparse",
            "ast",
            "collections",
            "contextlib",
            "dataclasses",
            "datetime",
            "enum",
            "functools",
            "hashlib",
            "importlib",
            "io",
            "itertools",
            "json",
            "logging",
            "math",
            "operator",
            "os",
            "pathlib",
            "platform",
            "pprint",
            "re",
            "shlex",
            "shutil",
            "signal",
            "socket",
            "stat",
            "string",
            "subprocess",
            "sys",
            "tempfile",
            "textwrap",
            "threading",
            "time",
            "traceback",
            "typing",
            "unittest",
            "urllib",
            "uuid",
            "warnings",
        },
    )
)


@dataclass(frozen=True)
class InvocationLine:
    """Store one script-invocation candidate with source metadata."""

    source: str
    body_start_line: int
    line: ProseLine


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


def _line_hit(line: InvocationLine) -> str:
    """Format a matching line as `L<line>: <snippet>`."""
    hit = format_hit(
        line.line.index,
        line.line.text,
        body_start_line=line.body_start_line,
    )
    if line.source == "SKILL.md":
        return hit
    return f"{line.source} {hit}"


def _iter_command_fence_commands(
    body: str,
    *,
    skip_indices: frozenset[int] = frozenset(),
) -> Iterator[ProseLine]:
    """Yield logical command lines merged across trailing backslashes."""
    pending_text = ""
    pending_index: int | None = None

    for line in iter_fence_lines(body, COMMAND_FENCE_LANGUAGES):
        if line.index in skip_indices:
            continue
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

    if (
        BASH_INVOCATION_PREFIX_RE.match(line)
        or _has_required_prefix(line, script_match.start())
        or RUN_VERB_RE.search(line[: script_match.start()]) is not None
    ):
        return True

    # Bare script invocation: starts line, quoted at position 0, or has flags
    start = script_match.start()
    if start == 0 or (start == 1 and line[0] in ("`", '"', "'")):
        return True
    post_match = line[script_match.end() :]
    return bool(
        _POST_SHORT_FLAG_RE.search(post_match) or _POST_LONG_FLAG_RE.search(post_match),
    )


def _iter_invocation_lines_from_text(
    text: str,
    *,
    skip_indices: frozenset[int] = frozenset(),
) -> Iterator[ProseLine]:
    """Yield script-invocation candidates from one markdown text source."""
    yield from _iter_command_fence_commands(text, skip_indices=skip_indices)

    for line in extract_prose_lines(text):
        if line.index in skip_indices:
            continue
        if _is_command_like_prose_line(line.text):
            yield line


def _iter_invocation_lines(document: SkillDocument) -> Iterator[InvocationLine]:
    """Yield script invocation candidates from SKILL.md and referenced text files."""
    for line in _iter_invocation_lines_from_text(document.body):
        yield InvocationLine(
            source="SKILL.md",
            body_start_line=document.body_start_line,
            line=line,
        )

    for ref in iter_reference_inputs(
        document,
        skip=SkipConfig(fenced=False),
    ):
        for line in _iter_invocation_lines_from_text(
            "\n".join(ref.lines),
            skip_indices=ref.skip_indices,
        ):
            yield InvocationLine(
                source=ref.rel_path,
                body_start_line=1,
                line=line,
            )


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


def check_script_invocation_prefix(document: SkillDocument) -> list[CheckRecord]:
    """Validate `${CLAUDE_SKILL_DIR}` prefix usage for script invocations."""
    if not _has_scripts_dir(document):
        return []

    violations: list[str] = []
    seen_lines: set[tuple[str, int]] = set()
    for line in _iter_invocation_lines(document):
        for match in SCRIPT_PATH_RE.finditer(line.line.text):
            if _has_required_prefix(line.line.text, match.start()):
                continue
            line_key = (line.source, line.line.index)
            if line_key in seen_lines:
                break
            seen_lines.add(line_key)
            violations.append(_line_hit(line))
            break

    if violations:
        return [
            CheckRecord(
                check=CHECK_SCRIPT_INVOCATION_PREFIX,
                passed=False,
                detail=(
                    f"Found {len(violations)} script invocation line(s) without "
                    "${CLAUDE_SKILL_DIR} prefix - use "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." - '
                    f"first: {violations[0]}"
                ),
                tier="I6",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_SCRIPT_INVOCATION_PREFIX,
            passed=True,
            detail="All detected script invocations use ${CLAUDE_SKILL_DIR} prefix",
            tier="I6",
        ),
    ]


def check_no_bash_prefix(document: SkillDocument) -> list[CheckRecord]:
    """Validate that script invocations do not start with `bash` prefix."""
    if not _has_scripts_dir(document):
        return []

    violations: list[str] = []
    seen_lines: set[tuple[str, int]] = set()
    for line in _iter_invocation_lines(document):
        command_text = _strip_list_prefix(line.line.text.strip())
        if not command_text:
            continue
        if BASH_INVOCATION_PREFIX_RE.match(command_text) is None:
            continue
        if SCRIPT_PATH_RE.search(command_text) is None:
            continue
        line_key = (line.source, line.line.index)
        if line_key in seen_lines:
            continue
        seen_lines.add(line_key)
        violations.append(_line_hit(line))

    if violations:
        return [
            CheckRecord(
                check=CHECK_NO_BASH_PREFIX,
                passed=False,
                detail=(
                    f"Found {len(violations)} script invocation(s) using bash "
                    "prefix - invoke directly via "
                    '"${CLAUDE_SKILL_DIR}/scripts/..." and set executable bit '
                    f"- first: {violations[0]}"
                ),
                tier="I6",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_NO_BASH_PREFIX,
            passed=True,
            detail="No bash-prefixed script invocations found",
            tier="I6",
        ),
    ]


def check_script_executable(document: SkillDocument) -> list[CheckRecord]:
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
            "Unable to read "
            f"{len(read_errors)} script file(s) for shebang detection: "
            f"{_format_examples(list(read_errors))}",
        )
    if stat_errors:
        issues.append(
            "Unable to stat "
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
            CheckRecord(
                check=CHECK_SCRIPT_EXECUTABLE,
                passed=False,
                detail="; ".join(issues),
                tier="I12",
            ),
        ]

    if not runnable_scripts:
        return [
            CheckRecord(
                check=CHECK_SCRIPT_EXECUTABLE,
                passed=True,
                detail="No runnable script entrypoints found in scripts/",
                tier="I12",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_SCRIPT_EXECUTABLE,
            passed=True,
            detail=(
                f"All {len(runnable_scripts)} runnable script entrypoint(s) "
                "in scripts/ have executable bit set"
            ),
            tier="I12",
        ),
    ]


def check_legacy_bash_info(document: SkillDocument) -> list[CheckRecord]:
    """Emit informational signal when legacy .sh scripts exist anywhere."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    legacy_scripts = sorted(
        path.relative_to(scripts_dir).as_posix()
        for path in scripts_dir.rglob("*.sh")
        if path.is_file()
    )
    if not legacy_scripts:
        return [
            CheckRecord(
                check=CHECK_LEGACY_BASH_INFO,
                passed=True,
                detail="No legacy .sh scripts found in scripts/",
                tier="P16",
            ),
        ]

    return [
        CheckRecord.info(
            CHECK_LEGACY_BASH_INFO,
            (
                f"Found {len(legacy_scripts)} legacy .sh "
                "script(s) in scripts/: "
                f"{_format_examples(legacy_scripts)}"
            ),
            tier="P16",
        ),
    ]


def check_help_output_info(document: SkillDocument) -> list[CheckRecord]:
    """Check whether runnable scripts advertise --help support."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    runnable_scripts, _ = _collect_runnable_scripts(scripts_dir)

    if not runnable_scripts:
        return [
            CheckRecord(
                check=CHECK_HELP_OUTPUT_INFO,
                passed=True,
                detail="No runnable scripts found",
                tier="I30",
            ),
        ]

    missing_help: list[str] = []
    for path in runnable_scripts:
        rel = path.relative_to(scripts_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing_help.append(rel)
            continue

        has_help = False
        if path.suffix.lower() == ".py":
            has_help = _HELP_IMPORT_RE.search(content) is not None
        elif path.suffix.lower() == ".sh":
            has_help = _SHELL_HELP_CASE_RE.search(content) is not None

        if not has_help:
            missing_help.append(rel)

    if missing_help:
        return [
            CheckRecord.info(
                CHECK_HELP_OUTPUT_INFO,
                (
                    f"{len(missing_help)} of {len(runnable_scripts)} runnable "
                    "script(s) lack --help support: "
                    f"{_format_examples(missing_help)}"
                ),
                tier="I30",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_HELP_OUTPUT_INFO,
            passed=True,
            detail=(
                f"All {len(runnable_scripts)} runnable script(s) have --help support"
            ),
            tier="I30",
        ),
    ]


def _collect_exit_codes(scripts_dir: Path) -> tuple[int, set[str]]:
    """Scan eligible scripts and return (eligible_count, distinct_exit_codes)."""
    distinct_codes: set[str] = set()
    eligible_count = 0

    for path in _iter_script_files(scripts_dir):
        if path.name.startswith("_"):
            continue
        first_line = _read_first_line(path)
        if first_line is None or not first_line.startswith(SHEBANG_PREFIX):
            continue

        eligible_count += 1
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        pattern = _PY_EXIT_CODE_RE if path.suffix.lower() == ".py" else _SH_EXIT_CODE_RE
        for m in pattern.finditer(content):
            distinct_codes.add(m.group(1))

    return eligible_count, distinct_codes


def check_exit_codes_info(document: SkillDocument) -> list[CheckRecord]:
    """Check whether scripts use distinct exit codes."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    eligible_count, distinct_codes = _collect_exit_codes(scripts_dir)

    if eligible_count == 0:
        return [
            CheckRecord(
                check=CHECK_EXIT_CODES_INFO,
                passed=True,
                detail="No eligible scripts found",
                tier="P18",
            ),
        ]

    if len(distinct_codes) >= MIN_DISTINCT_EXIT_CODES:
        return [
            CheckRecord(
                check=CHECK_EXIT_CODES_INFO,
                passed=True,
                detail=(
                    f"Found {len(distinct_codes)} distinct exit code(s) "
                    f"across {eligible_count} script(s)"
                ),
                tier="P18",
            ),
        ]

    return [
        CheckRecord.info(
            CHECK_EXIT_CODES_INFO,
            (
                f"Only {len(distinct_codes)} distinct exit code(s) found "
                f"across {eligible_count} script(s) - consider using "
                "distinct codes for pass/fail/usage errors"
            ),
            tier="P18",
        ),
    ]


def _find_third_party_imports(
    content: str,
    local_modules: frozenset[str],
) -> list[str]:
    """Return list of third-party module names imported in content."""
    third_party: list[str] = []
    known = _STDLIB_MODULES | local_modules
    for m in _PY_IMPORT_RE.finditer(content):
        module = m.group(1) or m.group(2)
        if module not in known and module not in third_party:
            third_party.append(module)
    return third_party


def check_undeclared_deps_info(document: SkillDocument) -> list[CheckRecord]:
    """Check whether Python scripts import undeclared third-party dependencies."""
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    py_files = sorted(
        p for p in _iter_script_files(scripts_dir) if p.suffix.lower() == ".py"
    )

    if not py_files:
        return [
            CheckRecord(
                check=CHECK_UNDECLARED_DEPS_INFO,
                passed=True,
                detail="No .py files found in scripts/",
                tier="I31",
            ),
        ]

    local_modules: frozenset[str] = frozenset(p.stem for p in py_files)

    undeclared: list[str] = []
    for path in py_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if "# /// script" in content:
            continue

        file_third_party = _find_third_party_imports(content, local_modules)
        if file_third_party:
            rel = path.relative_to(scripts_dir).as_posix()
            undeclared.append(f"{rel} ({', '.join(file_third_party)})")

    if undeclared:
        return [
            CheckRecord.info(
                CHECK_UNDECLARED_DEPS_INFO,
                (
                    f"{len(undeclared)} script(s) import undeclared "
                    f"third-party module(s): {_format_examples(undeclared)}"
                ),
                tier="I31",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_UNDECLARED_DEPS_INFO,
            passed=True,
            detail="All Python script imports are stdlib or local",
            tier="I31",
        ),
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], list[CheckRecord]]]] = {
    CHECK_SCRIPT_INVOCATION_PREFIX: check_script_invocation_prefix,
    CHECK_NO_BASH_PREFIX: check_no_bash_prefix,
    CHECK_SCRIPT_EXECUTABLE: check_script_executable,
    CHECK_LEGACY_BASH_INFO: check_legacy_bash_info,
    CHECK_HELP_OUTPUT_INFO: check_help_output_info,
    CHECK_EXIT_CODES_INFO: check_exit_codes_info,
    CHECK_UNDECLARED_DEPS_INFO: check_undeclared_deps_info,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    """Run all script-dir checks and return results in stable order."""
    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []

    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        results.extend(CHECK_FUNCTIONS[check_name](document))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run CLI entry point and return process exit code."""
    return run_check_cli(
        "Validate scripts directory invocation and executability checks.",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
