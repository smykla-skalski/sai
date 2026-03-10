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
import shlex
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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
    split_frontmatter,
    strip_wrapping_quotes,
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
CHECK_UNREFERENCED: Final[str] = "SD-unreferenced"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_SCRIPT_INVOCATION_PREFIX,
    CHECK_NO_BASH_PREFIX,
    CHECK_SCRIPT_EXECUTABLE,
    CHECK_LEGACY_BASH_INFO,
    CHECK_HELP_OUTPUT_INFO,
    CHECK_EXIT_CODES_INFO,
    CHECK_UNDECLARED_DEPS_INFO,
    CHECK_UNREFERENCED,
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

# Hook script detection patterns
_HOOKS_BLOCK_START_RE: Final[Pattern[str]] = re.compile(r"^hooks:\s*$")
_HOOK_COMMAND_RE: Final[Pattern[str]] = re.compile(r"^\s+command:\s*(.+?)\s*$")
_HOOK_INTERPRETER_NAMES: Final[frozenset[str]] = frozenset(
    {"bash", "node", "perl", "python", "python3", "ruby", "sh", "zsh"},
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


def _skip_env_assignments(tokens: list[str], start: int) -> int:
    """Return index past any leading KEY=val env assignments."""
    idx = start
    while idx < len(tokens) and "=" in tokens[idx] and not tokens[idx].startswith("/"):
        idx += 1
    return idx


def _resolve_env_wrapper(tokens: list[str], idx: int) -> int:
    """Advance past /usr/bin/env wrapper and its flags/assignments."""
    if idx >= len(tokens) or Path(tokens[idx]).name != "env":
        return idx
    idx += 1
    while idx < len(tokens):
        if tokens[idx].startswith("-") or (
            "=" in tokens[idx] and not tokens[idx].startswith("/")
        ):
            idx += 1
        else:
            break
    return idx


def _skip_interpreter(tokens: list[str], idx: int) -> int:
    """Advance past interpreter binary and its flags."""
    if idx >= len(tokens) or Path(tokens[idx]).name not in _HOOK_INTERPRETER_NAMES:
        return idx
    idx += 1
    while idx < len(tokens) and tokens[idx].startswith("-"):
        idx += 1
    return idx


def _extract_hook_script_target(tokens: list[str]) -> str | None:
    """Extract the script path token from a hook command's tokenized form."""
    if not tokens:
        return None

    idx = _skip_env_assignments(tokens, 0)
    if idx >= len(tokens):
        return None

    idx = _resolve_env_wrapper(tokens, idx)
    if idx >= len(tokens):
        return None

    idx = _skip_interpreter(tokens, idx)
    if idx >= len(tokens):
        return None

    return tokens[idx]


def _extract_hook_commands(fm_lines: list[str]) -> list[str]:
    """Extract command: values from the hooks: frontmatter block."""
    in_hooks = False
    commands: list[str] = []
    for line in fm_lines:
        if _HOOKS_BLOCK_START_RE.match(line):
            in_hooks = True
            continue
        if in_hooks:
            if line and not line[0].isspace():
                break
            m = _HOOK_COMMAND_RE.match(line)
            if m:
                commands.append(strip_wrapping_quotes(m.group(1).strip()))
    return commands


def _resolve_hook_command(cmd: str, skill_dir: Path) -> Path | None:
    """Resolve a single hook command string to a filesystem path."""
    if "$CLAUDE_PROJECT_DIR" in cmd:
        return None

    dir_str = str(skill_dir)
    resolved = cmd.replace("${CLAUDE_SKILL_DIR}", dir_str).replace(
        "$CLAUDE_SKILL_DIR",
        dir_str,
    )

    try:
        tokens = shlex.split(resolved, posix=True)
    except ValueError:
        tokens = resolved.split()

    target = _extract_hook_script_target(tokens)
    if target is None:
        return None

    path = Path(target)
    try:
        if path.is_file():
            return path.resolve()
    except OSError:
        pass
    return None


def _collect_hook_script_paths(document: SkillDocument) -> frozenset[Path]:
    """Collect resolved paths of scripts referenced in hooks: frontmatter.

    Hook scripts have a fixed JSON-in/JSON-out contract invoked by the
    Claude Code runtime, not by the agent. They don't need --help.
    """
    fm_lines, _, _ = split_frontmatter(document.content)
    commands = _extract_hook_commands(fm_lines)
    if not commands:
        return frozenset()

    paths: set[Path] = set()
    for cmd in commands:
        resolved = _resolve_hook_command(cmd, document.skill_dir)
        if resolved is not None:
            paths.add(resolved)
    return frozenset(paths)


def _is_hook_only_script(
    path: Path,
    hook_paths: frozenset[Path],
) -> bool:
    """Return whether script is wired as a hook command target.

    Only scripts explicitly referenced in the hooks: frontmatter block
    are considered hook scripts. Directory naming (scripts/hooks/) alone
    is not sufficient - the script must be wired.
    """
    try:
        return path.resolve() in hook_paths
    except OSError:
        return False


def _partition_hook_scripts(
    runnable_scripts: tuple[Path, ...],
    hook_paths: frozenset[Path],
) -> tuple[list[Path], int]:
    """Split runnable scripts into workflow scripts and hook count."""
    workflow: list[Path] = []
    hook_count = 0
    for path in runnable_scripts:
        if _is_hook_only_script(path, hook_paths):
            hook_count += 1
        else:
            workflow.append(path)
    return workflow, hook_count


def _find_missing_help(
    scripts: list[Path],
    scripts_dir: Path,
) -> list[str]:
    """Return relative paths of scripts lacking --help support."""
    missing: list[str] = []
    for path in scripts:
        rel = path.relative_to(scripts_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing.append(rel)
            continue

        has_help = False
        if path.suffix.lower() == ".py":
            has_help = _HELP_IMPORT_RE.search(content) is not None
        elif path.suffix.lower() == ".sh":
            has_help = _SHELL_HELP_CASE_RE.search(content) is not None

        if not has_help:
            missing.append(rel)
    return missing


def check_help_output_info(document: SkillDocument) -> list[CheckRecord]:
    """Check whether runnable scripts advertise --help support.

    Hook scripts are excluded - they have a fixed JSON-in/JSON-out
    contract invoked by the Claude Code runtime, not by the agent,
    so --help is not applicable per agentskills.io guidance.
    """
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

    hook_paths = _collect_hook_script_paths(document)
    workflow_scripts, hook_count = _partition_hook_scripts(
        runnable_scripts, hook_paths,
    )
    hook_note = f" ({hook_count} hook script(s) excluded)" if hook_count else ""

    if not workflow_scripts:
        return [
            CheckRecord(
                check=CHECK_HELP_OUTPUT_INFO,
                passed=True,
                detail=(
                    f"All {len(runnable_scripts)} runnable script(s) are "
                    "hook scripts (--help not applicable)"
                ),
                tier="I30",
            ),
        ]

    missing_help = _find_missing_help(workflow_scripts, scripts_dir)

    if missing_help:
        return [
            CheckRecord.info(
                CHECK_HELP_OUTPUT_INFO,
                (
                    f"{len(missing_help)} of {len(workflow_scripts)} workflow "
                    f"script(s) lack --help support{hook_note}: "
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
                f"All {len(workflow_scripts)} workflow script(s) have "
                f"--help support{hook_note}"
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


def _collect_body_referenced_scripts(document: SkillDocument) -> frozenset[str]:
    """Return relative paths (from scripts/) mentioned in body or refs.

    Collects script paths from both fenced code blocks and prose lines
    in SKILL.md and all referenced text files.
    """
    referenced: set[str] = set()
    for line in _iter_invocation_lines(document):
        for match in SCRIPT_PATH_RE.finditer(line.line.text):
            full_match = match.group(0)
            if full_match.startswith("scripts/"):
                referenced.add(full_match[len("scripts/"):])
    return frozenset(referenced)


def _read_script_contents(scripts: list[Path]) -> dict[Path, str]:
    """Read all script files and return {path: content} dict."""
    contents: dict[Path, str] = {}
    for path in scripts:
        text = _read_file_text(path)
        if text is not None:
            contents[path] = text
    return contents


def _read_file_text(path: Path) -> str | None:
    """Read file as UTF-8 with replacement. Return None on error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _collect_script_internal_refs(scripts_dir: Path) -> frozenset[str]:
    """Return relative paths of scripts referenced by other scripts.

    Detects filename mentions (subprocess calls, string literals,
    orchestrator mappings) within other scripts in the same directory.
    Self-references are excluded - only cross-script references count.
    """
    all_scripts = list(_iter_script_files(scripts_dir))

    # Read all scripts once and cache contents
    contents = _read_script_contents(all_scripts)

    referenced: set[str] = set()
    for target in all_scripts:
        target_name = target.name
        for source, content in contents.items():
            if source == target:
                continue
            if target_name in content:
                referenced.add(target.relative_to(scripts_dir).as_posix())
                break

    return frozenset(referenced)


def _collect_all_referenced_scripts(
    document: SkillDocument,
    hook_paths: frozenset[Path],
    scripts_dir: Path,
) -> frozenset[str]:
    """Return relative paths of all referenced scripts.

    A script is referenced if any of:
    1. Its resolved path is a hook command target in frontmatter
    2. Its scripts/-relative path appears in SKILL.md body or refs
    3. Its name or stem appears in other scripts (internal tooling)
    """
    # Hook-referenced scripts (filter to those under scripts_dir).
    # Resolve scripts_dir to match hook_paths (which are resolved).
    hook_rels = set[str]()
    resolved_scripts_dir = scripts_dir.resolve()
    for path in hook_paths:
        if path.is_relative_to(resolved_scripts_dir):
            hook_rels.add(path.relative_to(resolved_scripts_dir).as_posix())

    # Body/reference-referenced scripts
    body_rels = _collect_body_referenced_scripts(document)

    # Inter-script references (orchestrator -> checkers pattern)
    internal_rels = _collect_script_internal_refs(scripts_dir)

    return frozenset(hook_rels | body_rels | internal_rels)


def check_unreferenced_scripts(document: SkillDocument) -> list[CheckRecord]:
    """Check for runnable scripts not referenced anywhere in the skill.

    A script is unreferenced if it is not:
    - Wired as a hook command in frontmatter
    - Invoked in SKILL.md body or reference files
    - A library file (underscore prefix convention)
    """
    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []

    runnable_scripts, _ = _collect_runnable_scripts(scripts_dir)
    if not runnable_scripts:
        return []

    # Filter out library files (underscore prefix = imported, not invoked)
    entrypoints = [p for p in runnable_scripts if not p.name.startswith("_")]
    if not entrypoints:
        return []

    hook_paths = _collect_hook_script_paths(document)
    all_refs = _collect_all_referenced_scripts(document, hook_paths, scripts_dir)

    unreferenced: list[str] = []
    for path in entrypoints:
        rel = path.relative_to(scripts_dir).as_posix()
        if rel not in all_refs:
            unreferenced.append(rel)

    if unreferenced:
        return [
            CheckRecord(
                check=CHECK_UNREFERENCED,
                passed=False,
                detail=(
                    f"{len(unreferenced)} script(s) not referenced in "
                    "SKILL.md body, references, or hooks: "
                    f"{_format_examples(unreferenced)}"
                ),
                tier="I32",
            ),
        ]

    return [
        CheckRecord(
            check=CHECK_UNREFERENCED,
            passed=True,
            detail=(
                f"All {len(entrypoints)} entrypoint script(s) are referenced"
            ),
            tier="I32",
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
    CHECK_UNREFERENCED: check_unreferenced_scripts,
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
