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

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Shared infrastructure (mirrors check-flag-coverage.py)
# ---------------------------------------------------------------------------

def find_skill_md(skill_dir: str) -> str:
    """Find SKILL.md in the given directory."""
    path = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(path):
        return path
    return ""


def read_file(path: str) -> str:
    """Read file contents, return empty string on failure."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def emit(check: str, passed: bool, detail: str) -> dict:
    """Build a check result dict."""
    return {"check": check, "pass": passed, "detail": detail}


def emit_json(obj: dict) -> None:
    """Print a JSON object as a single line."""
    print(json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------

def extract_frontmatter_lines(content: str) -> list:
    """Return raw lines between --- delimiters."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    else:
        return []
    return fm_lines


def get_field_value(fm_lines: list, field: str) -> str:
    """Get a simple scalar field from frontmatter lines."""
    for line in fm_lines:
        m = re.match(r"^" + re.escape(field) + r":\s*(.*)", line)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            return val
    return ""


# ---------------------------------------------------------------------------
# Hooks YAML parser (custom state machine for nested hooks structure)
# ---------------------------------------------------------------------------

VALID_EVENTS = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "SubagentStart", "SubagentStop", "Stop",
}

# Events that require a matcher field
MATCHER_EVENTS = VALID_EVENTS - {"Stop"}


def parse_hooks(fm_lines: list) -> dict:
    """Parse hooks: block from frontmatter into dict[event] -> list[entry].

    Each entry is a dict with optional 'matcher' and a list of 'hooks',
    where each hook has 'type' and 'command'.

    Returns empty dict if no hooks: block found.
    """
    # Find hooks: line at indent 0
    hooks_start = None
    for i, line in enumerate(fm_lines):
        if re.match(r"^hooks:\s*$", line):
            hooks_start = i
            break

    if hooks_start is None:
        return {}

    # Collect indented lines after hooks:
    hooks_lines = []
    for line in fm_lines[hooks_start + 1:]:
        # Stop at next top-level key or end
        if line and not line[0].isspace():
            break
        hooks_lines.append(line)

    # Parse with state machine
    result = {}
    current_event = None
    current_entry = None
    current_hooks_list = None
    current_hook = None

    for line in hooks_lines:
        stripped = line.rstrip()
        if not stripped.strip():
            continue

        indent = len(stripped) - len(stripped.lstrip())

        # 2-space indent: event name (e.g., "  PreToolUse:")
        if indent == 2 and stripped.strip().endswith(":"):
            event_name = stripped.strip()[:-1]
            current_event = event_name
            if current_event not in result:
                result[current_event] = []
            current_entry = None
            current_hooks_list = None
            current_hook = None
            continue

        # 4-space indent: list item (- matcher: "X" or - hooks:)
        if indent == 4 and stripped.strip().startswith("- "):
            item_content = stripped.strip()[2:]
            current_entry = {}
            current_hooks_list = None
            current_hook = None

            m = re.match(r'matcher:\s*"?([^"]*)"?', item_content)
            if m:
                current_entry["matcher"] = m.group(1).strip()
            elif item_content.strip() == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = current_entry["hooks"]

            if current_event is not None:
                result[current_event].append(current_entry)
            continue

        # 6-space indent: nested key under list item
        if indent == 6 and current_entry is not None:
            key_content = stripped.strip()
            if key_content == "hooks:":
                current_entry["hooks"] = []
                current_hooks_list = current_entry["hooks"]
                current_hook = None
            elif key_content.startswith("matcher:"):
                m = re.match(r'matcher:\s*"?([^"]*)"?', key_content)
                if m:
                    current_entry["matcher"] = m.group(1).strip()
            continue

        # 8-space indent: hook list item (- type: "command")
        if indent == 8 and stripped.strip().startswith("- "):
            if current_hooks_list is not None:
                item_content = stripped.strip()[2:]
                current_hook = {}
                m = re.match(r'type:\s*"?([^"]*)"?', item_content)
                if m:
                    current_hook["type"] = m.group(1).strip()
                current_hooks_list.append(current_hook)
            continue

        # 10-space indent: hook fields (command:, type:)
        if indent == 10 and current_hook is not None:
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
# Sub-check implementations
# ---------------------------------------------------------------------------

def check_events(hooks: dict) -> list:
    """HK-EVENTS: all event names must be valid."""
    invalid = sorted(set(hooks.keys()) - VALID_EVENTS)
    if invalid:
        return [emit("HK-EVENTS", False,
                      "Invalid event names: " + ", ".join(invalid))]
    return [emit("HK-EVENTS", True,
                  "All %d event names valid" % len(hooks))]


def check_structure(hooks: dict) -> list:
    """HK-STRUCTURE: matcher-based events have matcher; Stop has none."""
    problems = []
    for event, entries in hooks.items():
        if event in MATCHER_EVENTS:
            for i, entry in enumerate(entries):
                if "matcher" not in entry or not entry["matcher"]:
                    problems.append(
                        "%s entry %d missing matcher" % (event, i + 1))
        elif event == "Stop":
            for i, entry in enumerate(entries):
                if "matcher" in entry and entry["matcher"]:
                    problems.append(
                        "Stop entry %d has unexpected matcher" % (i + 1))
    if problems:
        return [emit("HK-STRUCTURE", False, "; ".join(problems))]
    return [emit("HK-STRUCTURE", True,
                  "All entries have correct matcher structure")]


def check_type(hooks: dict) -> list:
    """HK-TYPE: every hook entry has type: command with non-empty command."""
    problems = []
    total_hooks = 0
    for event, entries in hooks.items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                total_hooks += 1
                if hook.get("type") != "command":
                    problems.append(
                        "%s: type is '%s', expected 'command'" %
                        (event, hook.get("type", "(missing)")))
                if not hook.get("command"):
                    problems.append(
                        "%s: empty or missing command field" % event)
    if problems:
        return [emit("HK-TYPE", False, "; ".join(problems))]
    return [emit("HK-TYPE", True,
                  "All %d hook entries have type: command" % total_hooks)]


def resolve_command_path(command: str, skill_dir: str) -> str:
    """Replace ${CLAUDE_SKILL_DIR} and return resolved path."""
    resolved = command.replace("${CLAUDE_SKILL_DIR}", skill_dir)
    resolved = resolved.replace("$CLAUDE_SKILL_DIR", skill_dir)
    return resolved


def collect_hook_entries(hooks: dict) -> list:
    """Return list of (event, matcher, command) tuples."""
    entries = []
    for event, event_entries in hooks.items():
        for entry in event_entries:
            matcher = entry.get("matcher", "")
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                entries.append((event, matcher, cmd))
    return entries


def check_resolve(hooks: dict, skill_dir: str) -> list:
    """HK-RESOLVE: all command paths resolve to existing files."""
    missing = []
    checked = 0
    for event, matcher, cmd in collect_hook_entries(hooks):
        if not cmd:
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        checked += 1
        if not os.path.isfile(resolved):
            label = "%s/%s" % (event, matcher) if matcher else event
            missing.append("%s -> %s" % (label, resolved))
    if missing:
        return [emit("HK-RESOLVE", False,
                      "Missing scripts: " + "; ".join(missing))]
    return [emit("HK-RESOLVE", True,
                  "All %d command paths resolve" % checked)]


def check_exec(hooks: dict, skill_dir: str) -> list:
    """HK-EXEC: all resolved hook scripts are executable."""
    not_exec = []
    seen = set()
    for event, matcher, cmd in collect_hook_entries(hooks):
        if not cmd:
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        if resolved in seen:
            continue
        seen.add(resolved)
        if os.path.isfile(resolved) and not os.access(resolved, os.X_OK):
            not_exec.append(os.path.basename(resolved))
    if not_exec:
        return [emit("HK-EXEC", False,
                      "Not executable: " + ", ".join(not_exec))]
    return [emit("HK-EXEC", True,
                  "All %d unique scripts are executable" % len(seen))]


def check_duplicate(hooks: dict) -> list:
    """HK-DUPLICATE: no duplicate event+matcher combinations."""
    seen = {}
    dupes = []
    for event, entries in hooks.items():
        for entry in entries:
            matcher = entry.get("matcher", "")
            key = (event, matcher)
            if key in seen:
                label = "%s/%s" % (event, matcher) if matcher else event
                dupes.append(label)
            seen[key] = True
    if dupes:
        return [emit("HK-DUPLICATE", False,
                      "Duplicate event+matcher: " + ", ".join(dupes))]
    return [emit("HK-DUPLICATE", True, "No duplicate event+matcher pairs")]


def _scripts_for_events(hooks: dict, events: set,
                        skill_dir: str) -> list:
    """Return unique resolved paths for scripts referenced by given events."""
    paths = []
    seen = set()
    for event, matcher, cmd in collect_hook_entries(hooks):
        if event not in events or not cmd:
            continue
        resolved = resolve_command_path(cmd, skill_dir)
        if resolved not in seen and os.path.isfile(resolved):
            seen.add(resolved)
            paths.append(resolved)
    return paths


STDIN_PATTERNS = [
    re.compile(r'input="\$\(cat\)"'),
    re.compile(r"input='\$\(cat\)'"),
    re.compile(r"\bcat\b.*\bjq\b"),
    re.compile(r"\bjq\b.*<"),
    re.compile(r"read\b.*stdin"),
    re.compile(r"input=\$\(cat\)"),
]

# Scripts that only output static JSON (jq -nc) without reading any stdin
# fields don't need stdin parsing. This is common for SubagentStart hooks
# that just inject context.
STATIC_OUTPUT_RE = re.compile(r"\bjq\s+-nc\b")


def check_stdin(hooks: dict, skill_dir: str) -> list:
    """HK-STDIN: hook scripts parse stdin JSON."""
    all_scripts = _scripts_for_events(hooks, VALID_EVENTS, skill_dir)
    missing = []
    for path in all_scripts:
        content = read_file(path)
        if not content:
            continue
        found = False
        for pat in STDIN_PATTERNS:
            if pat.search(content):
                found = True
                break
        # Static-output scripts (jq -nc only, no stdin field references)
        # don't need stdin parsing
        if not found and STATIC_OUTPUT_RE.search(content):
            # Verify it doesn't reference stdin fields like tool_input,
            # tool_response, last_assistant_message, etc.
            if not re.search(
                r"\b(tool_input|tool_response|last_assistant_message|"
                r"hook_event_name|session_id|stop_hook_active)\b",
                content
            ):
                found = True
        if not found:
            missing.append(os.path.basename(path))
    if missing:
        return [emit("HK-STDIN", False,
                      "Scripts not parsing stdin: " + ", ".join(missing))]
    return [emit("HK-STDIN", True,
                  "All %d scripts parse stdin JSON" % len(all_scripts))]


def check_loop(hooks: dict, skill_dir: str) -> list:
    """HK-LOOP: Stop/SubagentStop scripts check stop_hook_active."""
    stop_events = {"Stop", "SubagentStop"}
    scripts = _scripts_for_events(hooks, stop_events, skill_dir)
    if not scripts:
        return [emit("HK-LOOP", True,
                      "No Stop/SubagentStop hooks to check")]
    missing = []
    for path in scripts:
        content = read_file(path)
        if "stop_hook_active" not in content:
            missing.append(os.path.basename(path))
    if missing:
        return [emit("HK-LOOP", False,
                      "Missing stop_hook_active guard: " +
                      ", ".join(missing))]
    return [emit("HK-LOOP", True,
                  "All %d Stop/SubagentStop scripts have loop guard" %
                  len(scripts))]


EXIT2_RE = re.compile(r"^\s*exit\s+2\b")
COMMENT_RE = re.compile(r"^\s*#")


def check_exit(hooks: dict, skill_dir: str) -> list:
    """HK-EXIT: PreToolUse scripts never use exit 2."""
    scripts = _scripts_for_events(hooks, {"PreToolUse"}, skill_dir)
    if not scripts:
        return [emit("HK-EXIT", True, "No PreToolUse hooks to check")]
    problems = []
    for path in scripts:
        content = read_file(path)
        for line in content.splitlines():
            if COMMENT_RE.match(line):
                continue
            if EXIT2_RE.match(line):
                problems.append(os.path.basename(path))
                break
    if problems:
        return [emit("HK-EXIT", False,
                      "PreToolUse scripts using exit 2 (loses JSON output): "
                      + ", ".join(problems))]
    return [emit("HK-EXIT", True,
                  "No PreToolUse scripts use exit 2")]


def check_perm(hooks: dict, skill_dir: str) -> list:
    """HK-PERM: PostToolUse/PostToolUseFailure don't output permissionDecision."""
    post_events = {"PostToolUse", "PostToolUseFailure"}
    scripts = _scripts_for_events(hooks, post_events, skill_dir)
    if not scripts:
        return [emit("HK-PERM", True,
                      "No PostToolUse/PostToolUseFailure hooks to check")]
    problems = []
    for path in scripts:
        content = read_file(path)
        if "permissionDecision" in content:
            for line in content.splitlines():
                if COMMENT_RE.match(line):
                    continue
                if "permissionDecision" in line:
                    problems.append(os.path.basename(path))
                    break
    if problems:
        return [emit("HK-PERM", False,
                      "Post hooks outputting permissionDecision "
                      "(not supported): " + ", ".join(problems))]
    return [emit("HK-PERM", True,
                  "No post hooks use permissionDecision")]


PREFIX_RE = re.compile(r"\[([A-Z]+)\d{3}\]")


def check_prefix(hooks: dict, skill_dir: str) -> list:
    """HK-PREFIX: error codes use consistent prefix within the skill."""
    all_scripts = _scripts_for_events(hooks, VALID_EVENTS, skill_dir)
    prefixes = set()
    for path in all_scripts:
        content = read_file(path)
        for m in PREFIX_RE.finditer(content):
            prefixes.add(m.group(1))
    if not prefixes:
        return [emit("HK-PREFIX", True, "No error codes found (OK)")]
    if len(prefixes) == 1:
        return [emit("HK-PREFIX", True,
                      "Consistent error prefix: %s" % prefixes.pop())]
    return [emit("HK-PREFIX", False,
                  "Multiple error prefixes: " +
                  ", ".join(sorted(prefixes)))]


# ---------------------------------------------------------------------------
# P10: informational suggestion
# ---------------------------------------------------------------------------

def check_p10(fm_lines: list, skill_dir: str) -> list:
    """P10: side-effect skills without hooks could benefit from guardrails."""
    dmi = get_field_value(fm_lines, "disable-model-invocation")
    scripts_dir = os.path.join(skill_dir, "scripts")
    if dmi == "true" and os.path.isdir(scripts_dir):
        return [emit("hooks-suggestion-info", True,
                      "INFO: Side-effect skill with scripts/ but no hooks. "
                      "Consider adding skill-scoped hooks for guardrails.")]
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check-hooks.py <skill-directory>", file=sys.stderr)
        sys.exit(2)

    skill_dir = sys.argv[1]
    skill_md_path = find_skill_md(skill_dir)

    if not skill_md_path:
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    content = read_file(skill_md_path)
    if not content:
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    fm_lines = extract_frontmatter_lines(content)
    hooks = parse_hooks(fm_lines)

    # No hooks block - emit P10 if applicable, then exit
    if not hooks:
        p10 = check_p10(fm_lines, skill_dir)
        for r in p10:
            emit_json(r)
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    # Run all sub-checks
    results = []
    results.extend(check_events(hooks))
    results.extend(check_structure(hooks))
    results.extend(check_type(hooks))
    results.extend(check_resolve(hooks, skill_dir))
    results.extend(check_exec(hooks, skill_dir))
    results.extend(check_duplicate(hooks))
    results.extend(check_stdin(hooks, skill_dir))
    results.extend(check_loop(hooks, skill_dir))
    results.extend(check_exit(hooks, skill_dir))
    results.extend(check_perm(hooks, skill_dir))
    results.extend(check_prefix(hooks, skill_dir))

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed

    for r in results:
        emit_json(r)

    emit_json({"summary": True, "total": total, "passed": passed,
               "failed": failed})
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
