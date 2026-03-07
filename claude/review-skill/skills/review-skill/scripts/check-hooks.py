#!/usr/bin/env python3
"""check-hooks.py - Validate skill-scoped hooks configuration in SKILL.md.

Checks hooks frontmatter structure and referenced hook scripts for
correctness against the Skill Authoring Guide conventions.

Sub-checks:
  HK-EVENTS:    All event names are valid
  HK-STRUCTURE: Matcher-based events have matcher field; Stop has none
  HK-TYPE:      Every hook entry has type: "command" with non-empty command
  HK-RESOLVE:   All command paths resolve to existing files
  HK-EXEC:      All resolved hook scripts are executable
  HK-DUPLICATE: No duplicate event+matcher combinations
  HK-STDIN:     Hook scripts parse stdin JSON
  HK-LOOP:      Stop/SubagentStop scripts check stop_hook_active
  HK-EXIT:      PreToolUse scripts never use exit 2
  HK-PERM:      PostToolUse/PostToolUseFailure scripts don't output permissionDecision
  HK-PREFIX:    Error codes use consistent prefix within the skill

P10 (informational):
  Side-effect skills with scripts/ but no hooks could benefit from guardrails.

Usage:
    ./check-hooks.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes: 0 = all pass, 1 = any fail, 2 = usage error.
"""

from __future__ import annotations

import argparse
import re
from os import X_OK, access
from pathlib import Path
from re import Pattern
from typing import Final

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckResult,
    emit_error,
    emit_record,
    emit_results,
    parse_frontmatter_lines,
    split_frontmatter,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVENTS: Final[frozenset[str]] = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "Stop",
})

MATCHER_EVENTS: Final[frozenset[str]] = VALID_EVENTS - frozenset({"Stop"})


# ---------------------------------------------------------------------------
# Hooks YAML parser (custom state machine for nested hooks structure)
# ---------------------------------------------------------------------------


def parse_hooks(  # noqa: C901, PLR0912, PLR0915
    fm_lines: list[str],
) -> dict[str, list[dict[str, object]]]:
    """Parse hooks: block from frontmatter into dict[event] -> list[entry].

    Each entry is a dict with optional 'matcher' and a list of 'hooks',
    where each hook has 'type' and 'command'.

    Returns empty dict if no hooks: block found.
    """
    hooks_start: int | None = None
    for i, line in enumerate(fm_lines):
        if re.match(r"^hooks:\s*$", line):
            hooks_start = i
            break

    if hooks_start is None:
        return {}

    hooks_lines: list[str] = []
    for line in fm_lines[hooks_start + 1:]:
        if line and not line[0].isspace():
            break
        hooks_lines.append(line)

    result: dict[str, list[dict[str, object]]] = {}
    current_event: str | None = None
    current_entry: dict[str, object] | None = None
    current_hooks_list: list[dict[str, str]] | None = None
    current_hook: dict[str, str] | None = None

    for line in hooks_lines:
        stripped = line.rstrip()
        if not stripped.strip():
            continue

        indent = len(stripped) - len(stripped.lstrip())

        if indent == 2 and stripped.strip().endswith(":"):  # noqa: PLR2004
            event_name = stripped.strip()[:-1]
            current_event = event_name
            if current_event not in result:
                result[current_event] = []
            current_entry = None
            current_hooks_list = None
            current_hook = None
            continue

        if indent == 4 and stripped.strip().startswith("- "):  # noqa: PLR2004
            item_content = stripped.strip()[2:]
            current_entry = {}
            current_hooks_list = None
            current_hook = None

            m = re.match(r'matcher:\s*"?([^"]*)"?', item_content)
            if m:
                current_entry["matcher"] = m.group(1).strip()
            elif item_content.strip() == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = current_entry["hooks"]  # type: ignore[assignment]

            if current_event is not None:
                result[current_event].append(current_entry)
            continue

        if indent == 6 and current_entry is not None:  # noqa: PLR2004
            key_content = stripped.strip()
            if key_content == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = current_entry["hooks"]  # type: ignore[assignment]
                current_hook = None
            elif key_content.startswith("matcher:"):
                m = re.match(r'matcher:\s*"?([^"]*)"?', key_content)
                if m:
                    current_entry["matcher"] = m.group(1).strip()
            continue

        if indent == 8 and stripped.strip().startswith("- "):  # noqa: PLR2004
            if current_hooks_list is not None:
                item_content = stripped.strip()[2:]
                current_hook = {}
                m = re.match(r'type:\s*"?([^"]*)"?', item_content)
                if m:
                    current_hook["type"] = m.group(1).strip()
                current_hooks_list.append(current_hook)
            continue

        if indent == 10 and current_hook is not None:  # noqa: PLR2004
            key_content = stripped.strip()
            m = re.match(r'command:\s*"?([^"]*)"?', key_content)
            if m:
                current_hook["command"] = m.group(1).strip()
            else:
                m = re.match(r'type:\s*"?([^"]*)"?', key_content)
                if m:
                    current_hook["type"] = m.group(1).strip()
            continue

    return result


# ---------------------------------------------------------------------------
# Hook resolution helpers
# ---------------------------------------------------------------------------


def uses_project_dir(command: str) -> bool:
    """Check if a hook command uses $CLAUDE_PROJECT_DIR."""
    return "$CLAUDE_PROJECT_DIR" in command


def resolve_command_path(command: str, skill_dir: Path) -> Path:
    """Replace ${CLAUDE_SKILL_DIR} and return resolved path.

    Only handles ${CLAUDE_SKILL_DIR} (body substitution that also works
    when skill_dir matches the actual skill location).

    $CLAUDE_PROJECT_DIR paths are NOT resolved here - they are runtime
    env vars that can only resolve in the target project where the skill
    is installed (see #17688 workaround). Use uses_project_dir() to
    detect and skip these paths in checks that need file existence.
    """
    dir_str = str(skill_dir)
    resolved = command.replace("${CLAUDE_SKILL_DIR}", dir_str)
    resolved = resolved.replace("$CLAUDE_SKILL_DIR", dir_str)
    return Path(resolved)


def collect_hook_entries(
    hooks: dict[str, list[dict[str, object]]],
) -> list[tuple[str, str, str]]:
    """Return list of (event, matcher, command) tuples."""
    entries: list[tuple[str, str, str]] = []
    for event, event_entries in hooks.items():
        for entry in event_entries:
            matcher = entry.get("matcher", "") or ""  # type: ignore[assignment]
            for hook in entry.get("hooks", []):  # type: ignore[union-attr]
                cmd = hook.get("command", "") or ""  # type: ignore[union-attr]
                entries.append((event, str(matcher), str(cmd)))
    return entries


def _scripts_for_events(
    hooks: dict[str, list[dict[str, object]]],
    events: frozenset[str],
    skill_dir: Path,
) -> list[Path]:
    """Return unique resolved paths for scripts referenced by given events."""
    paths: list[Path] = []
    seen: set[Path] = set()
    for event, _matcher, cmd in collect_hook_entries(hooks):
        if event not in events or not cmd or uses_project_dir(cmd):
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        if resolved not in seen and resolved.is_file():
            seen.add(resolved)
            paths.append(resolved)
    return paths


def _read_text(path: Path) -> str:
    """Read file contents, return empty string on failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

STDIN_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    re.compile(r'input="\$\(cat\)"'),
    re.compile(r"input='\$\(cat\)'"),
    re.compile(r"\bcat\b.*\bjq\b"),
    re.compile(r"\bjq\b.*<"),
    re.compile(r"read\b.*stdin"),
    re.compile(r"input=\$\(cat\)"),
)

STATIC_OUTPUT_RE: Final[Pattern[str]] = re.compile(r"\bjq\s+-nc\b")

STDIN_FIELD_RE: Final[Pattern[str]] = re.compile(
    r"\b(tool_input|tool_response|last_assistant_message"
    r"|hook_event_name|session_id|stop_hook_active)\b",
)

EXIT2_RE: Final[Pattern[str]] = re.compile(r"^\s*exit\s+2\b")
COMMENT_RE: Final[Pattern[str]] = re.compile(r"^\s*#")
PREFIX_RE: Final[Pattern[str]] = re.compile(r"\[([A-Z]+)\d{3}\]")


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def _check_events(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckResult]:
    """HK-EVENTS: all event names must be valid."""
    invalid = sorted(set(hooks.keys()) - VALID_EVENTS)
    if invalid:
        return [CheckResult(
            check="HK-EVENTS",
            passed=False,
            detail=f"Invalid event names: {', '.join(invalid)}",
        )]
    return [CheckResult(
        check="HK-EVENTS",
        passed=True,
        detail=f"All {len(hooks)} event names valid",
    )]


def _check_structure(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckResult]:
    """HK-STRUCTURE: matcher-based events have matcher; Stop has none."""
    problems: list[str] = []
    for event, entries in hooks.items():
        if event in MATCHER_EVENTS:
            for i, entry in enumerate(entries):
                if "matcher" not in entry or not entry["matcher"]:
                    problems.append(f"{event} entry {i + 1} missing matcher")
        elif event == "Stop":
            for i, entry in enumerate(entries):
                if entry.get("matcher"):
                    problems.append(
                        f"Stop entry {i + 1} has unexpected matcher",
                    )
    if problems:
        return [CheckResult(
            check="HK-STRUCTURE",
            passed=False,
            detail="; ".join(problems),
        )]
    return [CheckResult(
        check="HK-STRUCTURE",
        passed=True,
        detail="All entries have correct matcher structure",
    )]


def _check_type(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckResult]:
    """HK-TYPE: every hook entry has type: command with non-empty command."""
    problems: list[str] = []
    total_hooks = 0
    for event, entries in hooks.items():
        for entry in entries:
            for hook in entry.get("hooks", []):  # type: ignore[union-attr]
                total_hooks += 1
                hook_type = hook.get("type", "(missing)")  # type: ignore[union-attr]
                if hook_type != "command":
                    problems.append(
                        f"{event}: type is '{hook_type}', expected 'command'",
                    )
                if not hook.get("command"):  # type: ignore[union-attr]
                    problems.append(f"{event}: empty or missing command field")
    if problems:
        return [CheckResult(
            check="HK-TYPE",
            passed=False,
            detail="; ".join(problems),
        )]
    return [CheckResult(
        check="HK-TYPE",
        passed=True,
        detail=f"All {total_hooks} hook entries have type: command",
    )]


def _check_resolve(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-RESOLVE: all command paths resolve to existing files."""
    missing: list[str] = []
    checked = 0
    skipped = 0
    for event, matcher, cmd in collect_hook_entries(hooks):
        if not cmd:
            continue
        if uses_project_dir(cmd):
            skipped += 1
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        checked += 1
        if not resolved.is_file():
            label = f"{event}/{matcher}" if matcher else event
            missing.append(f"{label} -> {resolved}")
    if missing:
        return [CheckResult(
            check="HK-RESOLVE",
            passed=False,
            detail=f"Missing scripts: {'; '.join(missing)}",
        )]
    detail = f"All {checked} command paths resolve"
    if skipped:
        detail += (
            f" ({skipped} $CLAUDE_PROJECT_DIR paths skipped - runtime only)"
        )
    return [CheckResult(check="HK-RESOLVE", passed=True, detail=detail)]


def _check_exec(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-EXEC: all resolved hook scripts are executable."""
    not_exec: list[str] = []
    seen: set[Path] = set()
    for _event, _matcher, cmd in collect_hook_entries(hooks):
        if not cmd:
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file() and not access(resolved, X_OK):
            not_exec.append(resolved.name)
    if not_exec:
        return [CheckResult(
            check="HK-EXEC",
            passed=False,
            detail=f"Not executable: {', '.join(not_exec)}",
        )]
    return [CheckResult(
        check="HK-EXEC",
        passed=True,
        detail=f"All {len(seen)} unique scripts are executable",
    )]


def _check_duplicate(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckResult]:
    """HK-DUPLICATE: no duplicate event+matcher combinations."""
    seen: set[tuple[str, str]] = set()
    dupes: list[str] = []
    for event, entries in hooks.items():
        for entry in entries:
            matcher = str(entry.get("matcher", ""))
            key = (event, matcher)
            if key in seen:
                label = f"{event}/{matcher}" if matcher else event
                dupes.append(label)
            seen.add(key)
    if dupes:
        return [CheckResult(
            check="HK-DUPLICATE",
            passed=False,
            detail=f"Duplicate event+matcher: {', '.join(dupes)}",
        )]
    return [CheckResult(
        check="HK-DUPLICATE",
        passed=True,
        detail="No duplicate event+matcher pairs",
    )]


def _check_stdin(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-STDIN: hook scripts parse stdin JSON."""
    all_scripts = _scripts_for_events(hooks, VALID_EVENTS, skill_dir)
    missing: list[str] = []
    for path in all_scripts:
        content = _read_text(path)
        if not content:
            continue
        found = any(pat.search(content) for pat in STDIN_PATTERNS)
        # Static-output scripts (jq -nc only, no stdin field references)
        # don't need stdin parsing
        if (
            not found
            and STATIC_OUTPUT_RE.search(content)
            and not STDIN_FIELD_RE.search(content)
        ):
            found = True
        if not found:
            missing.append(path.name)
    if missing:
        return [CheckResult(
            check="HK-STDIN",
            passed=False,
            detail=f"Scripts not parsing stdin: {', '.join(missing)}",
        )]
    return [CheckResult(
        check="HK-STDIN",
        passed=True,
        detail=f"All {len(all_scripts)} scripts parse stdin JSON",
    )]


def _check_loop(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-LOOP: Stop/SubagentStop scripts check stop_hook_active."""
    stop_events = frozenset({"Stop", "SubagentStop"})
    scripts = _scripts_for_events(hooks, stop_events, skill_dir)
    if not scripts:
        return [CheckResult(
            check="HK-LOOP",
            passed=True,
            detail="No Stop/SubagentStop hooks to check",
        )]
    missing: list[str] = []
    for path in scripts:
        content = _read_text(path)
        if "stop_hook_active" not in content:
            missing.append(path.name)
    if missing:
        return [CheckResult(
            check="HK-LOOP",
            passed=False,
            detail=f"Missing stop_hook_active guard: {', '.join(missing)}",
        )]
    return [CheckResult(
        check="HK-LOOP",
        passed=True,
        detail=f"All {len(scripts)} Stop/SubagentStop scripts have loop guard",
    )]


def _check_exit(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-EXIT: PreToolUse scripts never use exit 2."""
    scripts = _scripts_for_events(
        hooks,
        frozenset({"PreToolUse"}),
        skill_dir,
    )
    if not scripts:
        return [CheckResult(
            check="HK-EXIT",
            passed=True,
            detail="No PreToolUse hooks to check",
        )]
    problems: list[str] = []
    for path in scripts:
        content = _read_text(path)
        for line in content.splitlines():
            if COMMENT_RE.match(line):
                continue
            if EXIT2_RE.match(line):
                problems.append(path.name)
                break
    if problems:
        return [CheckResult(
            check="HK-EXIT",
            passed=False,
            detail="PreToolUse scripts using exit 2 (loses JSON output): "
            + ", ".join(problems),
        )]
    return [CheckResult(
        check="HK-EXIT",
        passed=True,
        detail="No PreToolUse scripts use exit 2",
    )]


def _check_perm(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-PERM: PostToolUse/PostToolUseFailure don't output permissionDecision."""
    post_events = frozenset({"PostToolUse", "PostToolUseFailure"})
    scripts = _scripts_for_events(hooks, post_events, skill_dir)
    if not scripts:
        return [CheckResult(
            check="HK-PERM",
            passed=True,
            detail="No PostToolUse/PostToolUseFailure hooks to check",
        )]
    problems: list[str] = []
    for path in scripts:
        content = _read_text(path)
        if "permissionDecision" in content:
            for line in content.splitlines():
                if COMMENT_RE.match(line):
                    continue
                if "permissionDecision" in line:
                    problems.append(path.name)
                    break
    if problems:
        return [CheckResult(
            check="HK-PERM",
            passed=False,
            detail="Post hooks outputting permissionDecision "
            "(not supported): " + ", ".join(problems),
        )]
    return [CheckResult(
        check="HK-PERM",
        passed=True,
        detail="No post hooks use permissionDecision",
    )]


def _check_prefix(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """HK-PREFIX: error codes use consistent prefix within the skill."""
    all_scripts = _scripts_for_events(hooks, VALID_EVENTS, skill_dir)
    prefixes: set[str] = set()
    for path in all_scripts:
        content = _read_text(path)
        for m in PREFIX_RE.finditer(content):
            prefixes.add(m.group(1))
    if not prefixes:
        return [CheckResult(
            check="HK-PREFIX",
            passed=True,
            detail="No error codes found (OK)",
        )]
    if len(prefixes) == 1:
        return [CheckResult(
            check="HK-PREFIX",
            passed=True,
            detail=f"Consistent error prefix: {prefixes.pop()}",
        )]
    return [CheckResult(
        check="HK-PREFIX",
        passed=False,
        detail=f"Multiple error prefixes: {', '.join(sorted(prefixes))}",
    )]


# ---------------------------------------------------------------------------
# P10: informational suggestion
# ---------------------------------------------------------------------------


def _check_p10(
    frontmatter: dict[str, str],
    skill_dir: Path,
) -> list[CheckResult]:
    """P10: side-effect skills without hooks could benefit from guardrails."""
    dmi = frontmatter.get("disable-model-invocation", "")
    scripts_dir = skill_dir / "scripts"
    if dmi == "true" and scripts_dir.is_dir():
        return [CheckResult(
            check="hooks-suggestion-info",
            passed=True,
            detail="INFO: Side-effect skill with scripts/ but no hooks. "
            "Consider adding skill-scoped hooks for guardrails.",
        )]
    return []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckResult]:
    """Run all hook validation checks and return results."""
    results: list[CheckResult] = []
    results.extend(_check_events(hooks))
    results.extend(_check_structure(hooks))
    results.extend(_check_type(hooks))
    results.extend(_check_resolve(hooks, skill_dir))
    results.extend(_check_exec(hooks, skill_dir))
    results.extend(_check_duplicate(hooks))
    results.extend(_check_stdin(hooks, skill_dir))
    results.extend(_check_loop(hooks, skill_dir))
    results.extend(_check_exit(hooks, skill_dir))
    results.extend(_check_perm(hooks, skill_dir))
    results.extend(_check_prefix(hooks, skill_dir))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate skill-scoped hooks configuration in SKILL.md",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    skill_dir: Path = args.skill_directory
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.is_file():
        return emit_results([])

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        emit_error(f"Error reading {skill_md_path}: {err}")
        return EXIT_USAGE_ERROR

    if not content:
        return emit_results([])

    fm_lines, _body_lines, _body_start = split_frontmatter(content)
    frontmatter = parse_frontmatter_lines(fm_lines)
    hooks = parse_hooks(fm_lines)

    # No hooks block - emit P10 if applicable, then empty summary
    if not hooks:
        p10_results = _check_p10(frontmatter, skill_dir)
        for result in p10_results:
            emit_record(result.payload())
        return emit_results([])

    return emit_results(run_checks(hooks, skill_dir))


if __name__ == "__main__":
    raise SystemExit(main())
