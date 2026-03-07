#!/usr/bin/env python3
"""check-hooks.py - Validate skill-scoped hooks configuration in SKILL.md.

Checks hooks frontmatter structure and referenced hook scripts for
correctness against the Skill Authoring Guide conventions.

Sub-checks:
  HK-events:    All event names are valid
  HK-structure: Matcher-based events have matcher field; Stop has none
  HK-type:      Every hook entry has type: "command" with non-empty command
  HK-resolve:   All command paths resolve to existing files
  HK-exec:      All resolved hook scripts are executable
  HK-duplicate: No duplicate event+matcher combinations
  HK-stdin:     Hook scripts parse stdin JSON
  HK-loop:      Stop/SubagentStop scripts check stop_hook_active
  HK-exit:      PreToolUse scripts never use exit 2
  HK-perm:      PostToolUse/PostToolUseFailure scripts don't output permissionDecision
  HK-prefix:    Error codes use consistent prefix within the skill

P10 (informational):
  HK-suggestion-info: Side-effect skills with scripts/ but no hooks.

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
import sys
from os import X_OK, access
from pathlib import Path
from re import Pattern
from typing import Final, cast

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckRecord,
    emit_error,
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

# YAML indentation levels in the hooks: block
INDENT_EVENT: Final[int] = 2
INDENT_ENTRY_LIST: Final[int] = 4
INDENT_ENTRY_KEY: Final[int] = 6
INDENT_HOOK_LIST: Final[int] = 8
INDENT_HOOK_KEY: Final[int] = 10


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

    Supported YAML subset (limitations):
    - Block mapping only (no flow syntax like {key: value})
    - Fixed indentation levels: 2 (event), 4 (entry list), 6 (entry
      keys), 8 (hook list), 10 (hook keys)
    - No anchors (&), aliases (*), or merge keys (<<)
    - No multi-line strings (| or >)
    - Values may be bare or double-quoted; single quotes not stripped
    - Only 'matcher', 'hooks', 'type', 'command' keys are recognized
    - Unexpected indentation levels are silently skipped
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

        if indent == INDENT_EVENT and stripped.strip().endswith(":"):
            event_name = stripped.strip()[:-1]
            current_event = event_name
            if current_event not in result:
                result[current_event] = []
            current_entry = None
            current_hooks_list = None
            current_hook = None
            continue

        if indent == INDENT_ENTRY_LIST and stripped.strip().startswith("- "):
            item_content = stripped.strip()[2:]
            current_entry = {}
            current_hooks_list = None
            current_hook = None

            m = re.match(r'matcher:\s*"?([^"]*)"?', item_content)
            if m:
                current_entry["matcher"] = m.group(1).strip()
            elif item_content.strip() == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = cast(
                    "list[dict[str, str]]", current_entry["hooks"],
                )

            if current_event is not None:
                result[current_event].append(current_entry)
            continue

        if indent == INDENT_ENTRY_KEY and current_entry is not None:
            key_content = stripped.strip()
            if key_content == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = cast(
                    "list[dict[str, str]]", current_entry["hooks"],
                )
                current_hook = None
            elif key_content.startswith("matcher:"):
                m = re.match(r'matcher:\s*"?([^"]*)"?', key_content)
                if m:
                    current_entry["matcher"] = m.group(1).strip()
            continue

        if indent == INDENT_HOOK_LIST and stripped.strip().startswith("- "):
            if current_hooks_list is not None:
                item_content = stripped.strip()[2:]
                current_hook = {}
                m = re.match(r'type:\s*"?([^"]*)"?', item_content)
                if m:
                    current_hook["type"] = m.group(1).strip()
                current_hooks_list.append(current_hook)
            continue

        if indent == INDENT_HOOK_KEY and current_hook is not None:
            key_content = stripped.strip()
            m = re.match(r'command:\s*"?([^"]*)"?', key_content)
            if m:
                current_hook["command"] = m.group(1).strip()
            else:
                m = re.match(r'type:\s*"?([^"]*)"?', key_content)
                if m:
                    current_hook["type"] = m.group(1).strip()
            continue

        # Unexpected indentation - warn on stderr
        expected = {
            INDENT_EVENT, INDENT_ENTRY_LIST, INDENT_ENTRY_KEY,
            INDENT_HOOK_LIST, INDENT_HOOK_KEY,
        }
        if indent not in expected:
            print(
                f"check-hooks: unexpected indent {indent} in hooks block: "
                f"{stripped.strip()!r}",
                file=sys.stderr,
            )

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
            matcher = cast("str", entry.get("matcher", "")) or ""
            for hook in cast("list[dict[str, object]]", entry.get("hooks", [])):
                cmd = cast("str", hook.get("command", "")) or ""
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
) -> list[CheckRecord]:
    """HK-EVENTS: all event names must be valid."""
    invalid = sorted(set(hooks.keys()) - VALID_EVENTS)
    if invalid:
        return [CheckRecord(
            check="HK-events",
            passed=False,
            detail=f"Invalid event names: {', '.join(invalid)}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-events",
        passed=True,
        detail=f"All {len(hooks)} event names valid",
        tier="I23",
    )]


def _check_structure(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckRecord]:
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
        return [CheckRecord(
            check="HK-structure",
            passed=False,
            detail="; ".join(problems),
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-structure",
        passed=True,
        detail="All entries have correct matcher structure",
        tier="I23",
    )]


def _check_type(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckRecord]:
    """HK-TYPE: every hook entry has type: command with non-empty command."""
    problems: list[str] = []
    total_hooks = 0
    for event, entries in hooks.items():
        for entry in entries:
            for hook in cast("list[dict[str, object]]", entry.get("hooks", [])):
                total_hooks += 1
                hook_type = cast("str", hook.get("type", "(missing)"))
                if hook_type != "command":
                    problems.append(
                        f"{event}: type is '{hook_type}', expected 'command'",
                    )
                if not hook.get("command"):
                    problems.append(f"{event}: empty or missing command field")
    if problems:
        return [CheckRecord(
            check="HK-type",
            passed=False,
            detail="; ".join(problems),
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-type",
        passed=True,
        detail=f"All {total_hooks} hook entries have type: command",
        tier="I23",
    )]


def _check_resolve(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
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
        return [CheckRecord(
            check="HK-resolve",
            passed=False,
            detail=f"Missing scripts: {'; '.join(missing)}",
            tier="I23",
        )]
    detail = f"All {checked} command paths resolve"
    if skipped:
        detail += (
            f" ({skipped} $CLAUDE_PROJECT_DIR paths skipped - runtime only)"
        )
    return [CheckRecord(check="HK-resolve", passed=True, detail=detail, tier="I23")]


def _check_exec(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
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
        return [CheckRecord(
            check="HK-exec",
            passed=False,
            detail=f"Not executable: {', '.join(not_exec)}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-exec",
        passed=True,
        detail=f"All {len(seen)} unique scripts are executable",
        tier="I23",
    )]


def _check_duplicate(
    hooks: dict[str, list[dict[str, object]]],
) -> list[CheckRecord]:
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
        return [CheckRecord(
            check="HK-duplicate",
            passed=False,
            detail=f"Duplicate event+matcher: {', '.join(dupes)}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-duplicate",
        passed=True,
        detail="No duplicate event+matcher pairs",
        tier="I23",
    )]


def _check_stdin(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
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
        return [CheckRecord(
            check="HK-stdin",
            passed=False,
            detail=f"Scripts not parsing stdin: {', '.join(missing)}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-stdin",
        passed=True,
        detail=f"All {len(all_scripts)} scripts parse stdin JSON",
        tier="I23",
    )]


def _check_loop(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
    """HK-LOOP: Stop/SubagentStop scripts check stop_hook_active."""
    stop_events = frozenset({"Stop", "SubagentStop"})
    scripts = _scripts_for_events(hooks, stop_events, skill_dir)
    if not scripts:
        return [CheckRecord(
            check="HK-loop",
            passed=True,
            detail="No Stop/SubagentStop hooks to check",
            tier="I23",
        )]
    missing: list[str] = []
    for path in scripts:
        content = _read_text(path)
        if "stop_hook_active" not in content:
            missing.append(path.name)
    if missing:
        return [CheckRecord(
            check="HK-loop",
            passed=False,
            detail=f"Missing stop_hook_active guard: {', '.join(missing)}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-loop",
        passed=True,
        detail=f"All {len(scripts)} Stop/SubagentStop scripts have loop guard",
        tier="I23",
    )]


def _check_exit(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
    """HK-EXIT: PreToolUse scripts never use exit 2."""
    scripts = _scripts_for_events(
        hooks,
        frozenset({"PreToolUse"}),
        skill_dir,
    )
    if not scripts:
        return [CheckRecord(
            check="HK-exit",
            passed=True,
            detail="No PreToolUse hooks to check",
            tier="I23",
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
        return [CheckRecord(
            check="HK-exit",
            passed=False,
            detail="PreToolUse scripts using exit 2 (loses JSON output): "
            + ", ".join(problems),
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-exit",
        passed=True,
        detail="No PreToolUse scripts use exit 2",
        tier="I23",
    )]


def _check_perm(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
    """HK-PERM: PostToolUse/PostToolUseFailure don't output permissionDecision."""
    post_events = frozenset({"PostToolUse", "PostToolUseFailure"})
    scripts = _scripts_for_events(hooks, post_events, skill_dir)
    if not scripts:
        return [CheckRecord(
            check="HK-perm",
            passed=True,
            detail="No PostToolUse/PostToolUseFailure hooks to check",
            tier="I23",
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
        return [CheckRecord(
            check="HK-perm",
            passed=False,
            detail="Post hooks outputting permissionDecision "
            "(not supported): " + ", ".join(problems),
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-perm",
        passed=True,
        detail="No post hooks use permissionDecision",
        tier="I23",
    )]


def _check_prefix(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
    """HK-PREFIX: error codes use consistent prefix within the skill."""
    all_scripts = _scripts_for_events(hooks, VALID_EVENTS, skill_dir)
    prefixes: set[str] = set()
    for path in all_scripts:
        content = _read_text(path)
        for m in PREFIX_RE.finditer(content):
            prefixes.add(m.group(1))
    if not prefixes:
        return [CheckRecord(
            check="HK-prefix",
            passed=True,
            detail="No error codes found (OK)",
            tier="I23",
        )]
    if len(prefixes) == 1:
        return [CheckRecord(
            check="HK-prefix",
            passed=True,
            detail=f"Consistent error prefix: {prefixes.pop()}",
            tier="I23",
        )]
    return [CheckRecord(
        check="HK-prefix",
        passed=False,
        detail=f"Multiple error prefixes: {', '.join(sorted(prefixes))}",
        tier="I23",
    )]


# ---------------------------------------------------------------------------
# P10: informational suggestion
# ---------------------------------------------------------------------------


def _check_p10(
    frontmatter: dict[str, str],
    skill_dir: Path,
) -> list[CheckRecord]:
    """P10: side-effect skills without hooks could benefit from guardrails."""
    dmi = frontmatter.get("disable-model-invocation", "")
    scripts_dir = skill_dir / "scripts"
    if dmi == "true" and scripts_dir.is_dir():
        return [CheckRecord(
            check="HK-suggestion-info",
            passed=True,
            detail="INFO: Side-effect skill with scripts/ but no hooks - "
            "consider adding skill-scoped hooks for guardrails",
            tier="P10",
        )]
    return []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    hooks: dict[str, list[dict[str, object]]],
    skill_dir: Path,
) -> list[CheckRecord]:
    """Run all hook validation checks and return results."""
    results: list[CheckRecord] = []
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

    # No hooks block - emit P10 if applicable, then summary
    if not hooks:
        return emit_results(_check_p10(frontmatter, skill_dir))

    return emit_results(run_checks(hooks, skill_dir))


if __name__ == "__main__":
    raise SystemExit(main())
