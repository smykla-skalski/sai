#!/usr/bin/env python3
"""lint-scripts.py - Static analysis for shell scripts.

Detects 32 bug classes discovered during the SAI script audit (2026-03-06).
Covers JSON safety, array/splitting, grep/regex, exit codes, temp files,
injection, defensive coding, and cross-file consistency.

Usage:
    ./lint-scripts.py <file-or-directory> [--json] [--severity critical|medium|low|all]

Exit codes: 0 = no findings, 1 = findings exist, 2 = usage error.
"""

import sys
import os
import re
import json as jsonmod
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    severity: str
    check: str
    message: str
    evidence: str = ""


SEVERITY_RANK = {"critical": 3, "medium": 2, "low": 1}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def has_set_u(content: str) -> bool:
    """Check if file uses set -u or set -o nounset."""
    return bool(re.search(r"set\s+.*-[a-zA-Z]*u|set\s+-o\s+nounset", content))


def has_pipefail(content: str) -> bool:
    return "pipefail" in content


def extract_function_body(lines: List[str], func_line: int, max_lines: int = 30) -> str:
    """Extract function body starting from func_line (0-indexed)."""
    depth = 0
    body_lines = []
    for i in range(func_line, min(func_line + max_lines, len(lines))):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        body_lines.append(line)
        if depth <= 0 and i > func_line:
            break
    return "\n".join(body_lines)


def find_while_read_loops(lines: List[str]) -> List[Tuple[int, int]]:
    """Find (start, end) line indices of while-read loops."""
    loops = []
    i = 0
    while i < len(lines):
        if re.search(r"\bwhile\b.*\bread\b", lines[i]):
            depth = 0
            start = i
            for j in range(i, len(lines)):
                stripped = lines[j].lstrip()
                # Count loop keywords for nesting
                if re.search(r"\b(while|for|until)\b", stripped) and not is_comment(stripped):
                    depth += 1
                if re.match(r"\s*done\b", lines[j]) and depth > 0:
                    depth -= 1
                    if depth == 0:
                        loops.append((start, j))
                        i = j
                        break
            else:
                # Unterminated loop, take next 50 lines as body
                loops.append((start, min(start + 50, len(lines) - 1)))
        i += 1
    return loops


# ---------------------------------------------------------------------------
# S01: Pipe delimiter — IFS='|' with read
# Bug class: #1
# ---------------------------------------------------------------------------
def check_pipe_delimiter(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if ("IFS='|'" in line or 'IFS="|"' in line) and "read" in line:
            findings.append(Finding(
                path, i + 1, "critical", "S01",
                "Using | as field delimiter with read - data containing pipes corrupts parsing",
                "Use ASCII unit separator: IFS=$'\\x1f'"
            ))
    return findings


# ---------------------------------------------------------------------------
# S02: Command exit code suppressed then piped to grep -c
# Bug class: #2
# ---------------------------------------------------------------------------
def check_suppressed_exit_code(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if re.search(r"2>/dev/null.*\|\s*grep\s+-c", line):
            findings.append(Finding(
                path, i + 1, "critical", "S02",
                "Exit code suppressed (2>/dev/null) then piped to grep -c - "
                "command failure produces count 0 (wrong default)",
                "Check command exit code separately before counting"
            ))
    return findings


# ---------------------------------------------------------------------------
# S03: sed with potentially empty variable in range expression
# Bug class: #5
# ---------------------------------------------------------------------------
def check_sed_empty_var(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # sed -n with a variable in range expression (before comma or $)
        m = re.search(r'sed\s+(-n\s+)?["\']?\$\{?(\w+)\}?.*,', line)
        if not m:
            continue
        var = m.group(2)
        # Check if guarded in preceding 5 lines (skip comments)
        start = max(0, i - 5)
        context = "\n".join(l for l in lines[start:i + 1] if not is_comment(l))
        if re.search(rf'\[\[.*-n.*\${{?{var}}}?|if\s+\[\[.*-n.*{var}', context):
            continue
        findings.append(Finding(
            path, i + 1, "critical", "S03",
            f"sed with ${{{var}}} in range - crashes if variable is empty",
            f'Guard with: if [[ -n "${var}" ]]'
        ))
    return findings


# ---------------------------------------------------------------------------
# S04: Template placeholder mismatch (**X** vs __X__)
# Bug class: #4
# ---------------------------------------------------------------------------
def check_template_mismatch(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    # Find __PLACEHOLDER__ patterns in the script
    placeholders = set(re.findall(r"__([A-Z_]+)__", content))
    if not placeholders:
        return findings
    # Look for template files in sibling directories
    script_dir = Path(path).parent
    parent_dir = script_dir.parent
    templates = list(parent_dir.rglob("*.template.*")) + list(parent_dir.rglob("*.tmpl"))
    for tmpl in templates:
        try:
            tmpl_content = tmpl.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        tmpl_lines = tmpl_content.splitlines()
        for p in placeholders:
            bold = f"**{p}**"
            for ti, tline in enumerate(tmpl_lines):
                if bold in tline:
                    findings.append(Finding(
                        str(tmpl), ti + 1, "critical", "S04",
                        f"Template uses {bold} but script substitutes __{p}__",
                        f"Change {bold} to __{p}__ in the template"
                    ))
    return findings


# ---------------------------------------------------------------------------
# S05: Script outputs JSON but has no escaping function
# Bug classes: #6, #34
# ---------------------------------------------------------------------------
def check_json_no_escape(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    # Find echo lines that output JSON (have { and escaped quotes)
    json_output_lines = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # echo with JSON object containing escaped quotes
        if re.search(r'echo\s+"?\{.*\\"', line):
            json_output_lines.append(i)
    if not json_output_lines:
        return findings
    # Check if file has json_escape function or emit() that does escaping
    has_escape = bool(re.search(r"json_escape\s*\(\)", content))
    # Check if emit() function has proper escaping (both \\ and \n)
    emit_match = re.search(r"^emit\(\)", content, re.MULTILINE)
    if emit_match:
        emit_body = extract_function_body(lines, content[:emit_match.start()].count("\n"))
        if "\\\\n" in emit_body or "$'\\n'" in emit_body:
            has_escape = True
    if not has_escape:
        # Report on the first JSON output line
        ln = json_output_lines[0]
        findings.append(Finding(
            path, ln + 1, "medium", "S05",
            "Script outputs JSON but has no json_escape/emit helper - "
            "user content with backslashes/quotes/newlines breaks JSON",
            "Add escaping for \\, \", \\n, \\t, \\r"
        ))
    return findings


# ---------------------------------------------------------------------------
# S06: JSON escaping function misses control characters
# Bug class: #9
# ---------------------------------------------------------------------------
def check_json_escape_incomplete(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    # Find function definitions
    for i, line in enumerate(lines):
        m = re.match(r"^(\w+)\(\)\s*\{", line)
        if not m:
            continue
        fname = m.group(1)
        body = extract_function_body(lines, i)
        # Must have backslash and quote escaping
        has_backslash = bool(re.search(r'//\\\\/', body) or re.search(r"//\\\\/", body))
        has_quote = bool(re.search(r'//\\"/|//\\"/', body))
        if has_backslash and has_quote:
            # But missing newline/tab/cr escaping
            has_newline = bool(re.search(r"\\\\n|\$'\\n'", body))
            if not has_newline:
                findings.append(Finding(
                    path, i + 1, "medium", "S06",
                    f"JSON escaping in {fname}() handles \\\\ and \\\" but not "
                    "newlines/tabs/CRs - multi-line input breaks JSON",
                    "Add: ${var//$'\\n'/\\\\n} and same for \\t, \\r"
                ))
    return findings


# ---------------------------------------------------------------------------
# S07: Space-delimited file list accumulation
# Bug class: #7
# ---------------------------------------------------------------------------
def check_space_delimited_list(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Pattern: VAR="$VAR $item" or VAR="$VAR $f"
        m = re.search(r'(\w+)="\$\{?\1\}?\s', line)
        if m:
            var = m.group(1)
            findings.append(Finding(
                path, i + 1, "medium", "S07",
                f"Space-delimited string accumulation for {var} - "
                "filenames with spaces break",
                "Use a bash array: arr+=(\"$item\")"
            ))
    return findings


# ---------------------------------------------------------------------------
# S08: for f in $(...) - word-splitting on filenames
# Bug class: #13
# ---------------------------------------------------------------------------
def check_for_in_expansion(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if re.search(r"\bfor\s+\w+\s+in\s+\$\(", line):
            findings.append(Finding(
                path, i + 1, "medium", "S08",
                "for-in with unquoted $() - word-splits on spaces in filenames",
                "Use: while IFS= read -r var; do ... done < <(command)"
            ))
    return findings


# ---------------------------------------------------------------------------
# S09: "${arr[@]}" without + guard under set -u
# Bug classes: #14, #15
# ---------------------------------------------------------------------------
def check_empty_array_crash(path: str, content: str, lines: List[str]) -> List[Finding]:
    if not has_set_u(content):
        return []
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Match "${arr[@]}" but not "${arr[@]+"${arr[@]}"}"
        for m in re.finditer(r'"\$\{(\w+)\[@\]\}"', line):
            arr = m.group(1)
            # Check if this is the + guard pattern itself
            full = line[m.start():]
            if re.match(r'"\$\{\w+\[@\]\+', full):
                continue
            # Check if preceded by + guard: ${arr[@]+"${arr[@]}"}
            before = line[:m.start()]
            if re.search(rf'\$\{{{arr}\[@\]\+', before):
                continue
            findings.append(Finding(
                path, i + 1, "medium", "S09",
                f'"${{{arr}[@]}}" crashes under set -u if array is empty (bash < 4.4)',
                f'Use: ${{{arr}[@]+"${{{arr}[@]}}"}}',
            ))
    return findings


# ---------------------------------------------------------------------------
# S10: Unquoted variable in command position
# Bug class: #16
# ---------------------------------------------------------------------------
def check_unquoted_var_cmd(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # $( followed by ${var} without quoting (not $("${var}")
        if re.search(r'\$\(\s*\$\{', line) and not re.search(r'\$\(\s*"\$\{', line):
            findings.append(Finding(
                path, i + 1, "medium", "S10",
                "Unquoted ${var} in command substitution - breaks on paths with spaces",
                'Quote: $("${var}" ...)'
            ))
    return findings


# ---------------------------------------------------------------------------
# S11: grep with variable in pattern but no -F
# Bug classes: #3, #22, #24
# ---------------------------------------------------------------------------
def check_grep_var_no_fixed(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Must have grep command
        if not re.search(r"\bgrep\b", line):
            continue
        # Extract the part after 'grep'
        grep_match = re.search(r"\bgrep\s+(.*)", line)
        if not grep_match:
            continue
        after_grep = grep_match.group(1)
        # Must have a variable in the pattern (inside double quotes after flags)
        if not re.search(r'"[^"]*\$\{?\w+', after_grep):
            continue
        # Must NOT have -F flag
        if re.search(r"-[a-zA-Z]*F", after_grep) or "--fixed" in after_grep:
            continue
        # Skip if this is just a file argument (grep "pattern" "$file")
        # Heuristic: variable is in the FIRST quoted string after flags
        # Find the pattern argument (first quoted string after flags)
        flag_and_pat = re.match(r"(-[a-zA-Z]+\s+)*", after_grep)
        if flag_and_pat:
            rest = after_grep[flag_and_pat.end():]
            # rest should start with the pattern
            pat_m = re.match(r'"([^"]*)"', rest)
            if pat_m:
                pattern_text = pat_m.group(1)
                if re.search(r"\$\{?\w+", pattern_text):
                    findings.append(Finding(
                        path, i + 1, "medium", "S11",
                        "grep with variable in pattern but no -F - "
                        "variable content treated as regex",
                        "Use grep -F for fixed strings, or escape the variable"
                    ))
    return findings


# ---------------------------------------------------------------------------
# S12: grep in pipeline without || true under pipefail
# Bug class: #26
# ---------------------------------------------------------------------------
def check_grep_pipe_no_guard(path: str, content: str, lines: List[str]) -> List[Finding]:
    if not has_pipefail(content):
        return []
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Line has | grep
        if not re.search(r"\|\s*grep\s", line):
            continue
        stripped = line.lstrip()
        # Skip if has || true or || :
        if re.search(r"\|\|\s*(true|:|\{)", line):
            continue
        # Skip if inside if/while/elif condition
        if re.match(r"\s*(if|while|elif)\s", line):
            continue
        # Skip grep -c (returns count, not error)
        if re.search(r"grep\s+[^|]*-[a-zA-Z]*c", line):
            continue
        # Skip assignment with ||: at end (like $(... || :))
        if re.search(r"\|\|\s*:\s*\)", line):
            continue
        findings.append(Finding(
            path, i + 1, "low", "S12",
            "grep in pipeline without || true - kills script under pipefail if no match",
            stripped[:120]
        ))
    return findings


# ---------------------------------------------------------------------------
# S13: Case-insensitive grep for command names matching prose
# Bug classes: #19, #33
# ---------------------------------------------------------------------------
def check_grep_cmd_in_prose(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # grep with -i flag and a command name pattern
        if not re.search(r"\bgrep\b", line):
            continue
        # Has -i flag
        if not re.search(r"grep\s+[^|]*-[a-zA-Z]*i", line):
            continue
        # Has a command name that's also an English word
        if re.search(r"\\bmake\\b|['\"]make['\"]", line, re.IGNORECASE):
            findings.append(Finding(
                path, i + 1, "medium", "S13",
                "Case-insensitive grep for 'make' matches prose (e.g., 'Make sure...')",
                "Use case-sensitive grep or anchor to command context"
            ))
    return findings


# ---------------------------------------------------------------------------
# S14: Destructive git op without error handling
# Bug class: #21
# ---------------------------------------------------------------------------
def check_destructive_git(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    destructive = re.compile(
        r"git\s+(branch\s+-[dD]|worktree\s+remove|reset\s+--hard|clean\s+-[fd])"
    )
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if not destructive.search(line):
            continue
        # Skip if inside an if condition (proper error handling)
        if re.match(r"\s*if\s", line):
            continue
        # Check previous line for if
        if i > 0 and re.match(r"\s*if\s", lines[i - 1]):
            continue
        # Skip if has || (failure handler)
        if "||" in line:
            continue
        # Flag: destructive op without proper error handling
        # Especially bad if stderr is suppressed
        stderr_suppressed = "2>/dev/null" in line or "2>&1" in line
        findings.append(Finding(
            path, i + 1, "medium", "S14",
            "Destructive git operation without error handling"
            + (" (stderr suppressed)" if stderr_suppressed else ""),
            line.strip()[:120]
        ))
    return findings


# ---------------------------------------------------------------------------
# S15: mktemp without EXIT trap
# Bug class: #10
# ---------------------------------------------------------------------------
def check_mktemp_no_trap(path: str, content: str, lines: List[str]) -> List[Finding]:
    mktemp_lines = [
        i for i, line in enumerate(lines)
        if "mktemp" in line and not is_comment(line)
    ]
    if not mktemp_lines:
        return []
    has_trap = bool(re.search(r"trap\s.*EXIT|trap\s.*cleanup|trap\s.*_cleanup", content))
    if has_trap:
        return []
    return [Finding(
        path, mktemp_lines[0] + 1, "medium", "S15",
        f"{len(mktemp_lines)} mktemp call(s) but no EXIT trap for cleanup",
        "Add: trap cleanup_func EXIT"
    )]


# ---------------------------------------------------------------------------
# S16: Interpolating heredoc with shell variable expansion
# Bug class: #17
# ---------------------------------------------------------------------------
def check_heredoc_injection(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Match <<TAG (unquoted heredoc)
        m = re.search(r"<<\s*(\w+)", line)
        if not m:
            continue
        tag = m.group(1)
        # Skip if tag is quoted: <<'TAG' or <<"TAG" or <<\TAG
        if re.search(r"<<\s*['\"]", line) or re.search(r"<<\s*\\", line):
            continue
        # Check if heredoc body (following lines until tag) contains variable expansion
        body_has_var = False
        for j in range(i + 1, min(i + 100, len(lines))):
            if lines[j].strip() == tag:
                break
            if re.search(r"\$\{?\w+", lines[j]) and not is_comment(lines[j]):
                body_has_var = True
        if body_has_var:
            findings.append(Finding(
                path, i + 1, "medium", "S16",
                f"Interpolating heredoc <<{tag} - shell variables expand inside, "
                "enabling injection",
                f"Use <<'{tag}' (single-quoted) for literal content, pass variables via flags"
            ))
    return findings


# ---------------------------------------------------------------------------
# S17: jq filter with interpolated variables
# Bug class: #35
# ---------------------------------------------------------------------------
def check_jq_injection(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # Case 1: building a jq filter variable with ${VAR} inside
        # e.g., JQ_FILTER="${JQ_FILTER} | select(.x == \"${AUTHOR}\")"
        if re.search(r"\w*(?:FILTER|JQ)\w*=.*\$\{", line, re.IGNORECASE):
            # Skip simple self-append without new variable interpolation
            # e.g., JQ_FILTER="${JQ_FILTER} | .field" is fine
            # but JQ_FILTER="${JQ_FILTER} | select(... ${VAR}...)" is not
            m = re.search(r'="(.*)"', line)
            if m:
                rhs = m.group(1)
                # Count distinct ${...} patterns, excluding self-reference
                var_refs = re.findall(r"\$\{(\w+)\}", rhs)
                # Get the variable being assigned
                lhs_m = re.match(r"\s*(\w+)=", line)
                lhs = lhs_m.group(1) if lhs_m else ""
                non_self = [v for v in var_refs if v != lhs]
                if non_self:
                    findings.append(Finding(
                        path, i + 1, "medium", "S17",
                        "Variable interpolated in jq filter string - enables jq injection",
                        "Use jq --arg varname \"$VAR\" and reference $varname in filter"
                    ))
                    continue
        # Case 2: direct jq invocation with ${VAR}
        # Skip array expansions like ${arr[@]} which are arg-passing, not filter injection
        if re.search(r"\bjq\b", line) and "${" in line:
            # Strip array expansions, then check for remaining ${VAR}
            cleaned = re.sub(r"\$\{\w+\[@\][^}]*\}", "", line)
            if "${" in cleaned and "--arg" not in line:
                findings.append(Finding(
                    path, i + 1, "medium", "S17",
                    "Variable interpolated in jq invocation - enables jq injection",
                    "Use jq --arg varname \"$VAR\" and reference $varname in filter"
                ))
    return findings


# ---------------------------------------------------------------------------
# S18: YAML parser get_field() doesn't strip quotes
# Bug class: #8
# ---------------------------------------------------------------------------
def check_yaml_no_quote_strip(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\w*get_field\w*)\(\)\s*\{", line)
        if not m:
            continue
        fname = m.group(1)
        body = extract_function_body(lines, i)
        # Check if function strips quotes (sed with quote removal)
        # Handle complex bash quoting like '"'"' for single quotes in sed
        if re.search(r"""sed.*s/.*["']""", body):
            continue
        if re.search(r"tr\s+-d\s+[\"']", body):
            continue
        findings.append(Finding(
            path, i + 1, "medium", "S18",
            f"YAML parser {fname}() doesn't strip quotes - "
            'name: "foo" returns "foo" with quotes',
            """Add: | sed "s/^[\\\"']//; s/[\\\"']$//" """
        ))
    return findings


# ---------------------------------------------------------------------------
# S19: API query with fixed limit, no pagination
# Bug class: #18
# ---------------------------------------------------------------------------
def check_no_pagination(path: str, content: str, lines: List[str]) -> List[Finding]:
    limit_pattern = re.compile(r"first:\s*\d+|per_page|[?&]limit=\d+")
    pagination_pattern = re.compile(
        r"hasNextPage|next_page|cursor|pageInfo|page_info|pagination",
        re.IGNORECASE
    )
    limit_match = limit_pattern.search(content)
    if not limit_match:
        return []
    if pagination_pattern.search(content):
        return []
    # Find the line with the limit
    for i, line in enumerate(lines):
        if limit_pattern.search(line):
            return [Finding(
                path, i + 1, "medium", "S19",
                "API query with fixed limit but no pagination - silently drops data",
                "Add cursor-based pagination or warn when result count equals limit"
            )]
    return []


# ---------------------------------------------------------------------------
# S20: While-read loop processing markdown without code block tracking
# Bug class: #20
# ---------------------------------------------------------------------------
def check_no_codeblock_tracking(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    loops = find_while_read_loops(lines)
    for start, end in loops:
        loop_body = "\n".join(lines[start:end + 1])
        # Check if this loop counts bullets
        if not re.search(r"BULLET|bullet", loop_body):
            continue
        # Check if THIS loop body tracks code block state
        if re.search(r"IN_BLOCK|in_block|code_block|fenced|BVP_IN_BLOCK", loop_body):
            continue
        # This loop counts bullets but doesn't track code blocks
        findings.append(Finding(
            path, start + 1, "medium", "S20",
            "Markdown line processing counts bullets but doesn't track "
            "fenced code block state",
            "Code inside ``` blocks will be miscounted as bullets/paragraphs"
        ))
    return findings


# ---------------------------------------------------------------------------
# S21: Awk diff parser matching ^--- without header state
# Bug class: #12
# ---------------------------------------------------------------------------
def check_awk_diff_collision(path: str, content: str, lines: List[str]) -> List[Finding]:
    # Check if file has awk with ^--- pattern
    if not re.search(r"awk.*\^---|/\^---/", content):
        return []
    # Check if file tracks header state
    if re.search(r"got_minus|got_plus|header_state|in_header", content):
        return []
    for i, line in enumerate(lines):
        if re.search(r"awk.*\^---|/\^---/", line) and not is_comment(line):
            return [Finding(
                path, i + 1, "medium", "S21",
                "Awk matches ^--- without header state tracking - "
                "diff body lines starting with --- confuse parser",
                "Track got_minus/got_plus flags to distinguish headers from body"
            )]
    return []


# ---------------------------------------------------------------------------
# S22: echo "$var" | wc -l off-by-one
# Bug class: #28
# ---------------------------------------------------------------------------
def check_echo_wc_offbyone(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if re.search(r'echo\s+"?\$\w.*\|\s*wc\s+-l', line):
            findings.append(Finding(
                path, i + 1, "low", "S22",
                'echo "$var" | wc -l - echo adds trailing newline, off-by-one',
                'Use: wc -l < "$file" for file line counting'
            ))
    return findings


# ---------------------------------------------------------------------------
# S23: Timestamp without uniqueness suffix in filename
# Bug class: #29
# ---------------------------------------------------------------------------
def check_timestamp_collision(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    # Find timestamp assignments
    ts_vars = {}
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        m = re.search(r'(\w+)=.*\bdate\b.*\+', line)
        if m:
            ts_vars[m.group(1)] = i
    if not ts_vars:
        return []
    # Check if timestamp vars are used in filenames without $$ or $RANDOM
    for var, def_line in ts_vars.items():
        # Look in next 20 lines for filename usage
        for j in range(def_line, min(def_line + 20, len(lines))):
            line = lines[j]
            if re.search(rf"\${{?{var}}}?", line) and j != def_line:
                # Check if this looks like a filename (has extension or path separator)
                # Exclude sed substitution patterns (s/.../$var.../g)
                if re.search(r"\.(log|txt|md|yaml|json|sh)\b", line) or \
                   (re.search(r"/\$", line) and not re.search(r'\bsed\b|s/.*/', line)):
                    # Check for uniqueness suffix (skip comments)
                    context = "\n".join(l for l in lines[def_line:j + 1] if not is_comment(l))
                    if not re.search(r"\$\$|\$RANDOM|\$\{RANDOM\}|\$\{PID\}", context):
                        findings.append(Finding(
                            path, def_line + 1, "low", "S23",
                            "Timestamp in filename without PID/random suffix - "
                            "same-second collision",
                            "Add $$ or $RANDOM to ensure uniqueness"
                        ))
                    break
    return findings


# ---------------------------------------------------------------------------
# S24: cut -d: on path-like data
# Bug class: #25
# ---------------------------------------------------------------------------
def check_cut_colon_paths(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        if not re.search(r"cut\s+-d[':]\s*-f", line) and \
           not re.search(r'cut\s+-d:\s+-f', line):
            continue
        # Check context for file/path indicators
        context = line
        if i > 0:
            context = lines[i - 1] + "\n" + context
        if re.search(r"file|path|spec|range|RANGE", context, re.IGNORECASE):
            findings.append(Finding(
                path, i + 1, "low", "S24",
                "cut -d: on path-like data - filenames with colons break",
                "Use parameter expansion: ${var%%:*} and ${var#*:}"
            ))
    return findings


# ---------------------------------------------------------------------------
# S25: Fragile external command output parsing
# Bug class: #27
# ---------------------------------------------------------------------------
def check_fragile_output_parse(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # head -n1 or tail -n1 assigning to a variable
        m = re.search(r"(\w+)=\$\((head|tail)\s+-n\s*1", line)
        if not m:
            # Also match: VAR=$(head -n1 <<< "$OTHER")
            m = re.search(r"(\w+)=\$\((head|tail)\s", line)
        if not m:
            continue
        var = m.group(1)
        # Check if result is used without validation in next 10 lines
        validated = False
        for j in range(i + 1, min(i + 10, len(lines))):
            if re.search(rf'\[\[.*\${{{var}}}.*=~.*\[0-9\]|'
                         rf'\[\[.*\${{{var}}}.*-eq|'
                         rf'\[\[.*"{var}".*=~',
                         lines[j]):
                validated = True
                break
        if not validated:
            findings.append(Finding(
                path, i + 1, "low", "S25",
                f"External command output parsed by {m.group(2)} into ${var} "
                "without format validation",
                f'Validate: [[ "${var}" =~ ^[0-9]+$ ]]'
            ))
    return findings


# ---------------------------------------------------------------------------
# S26: Deep relative path navigation
# Bug class: #30
# ---------------------------------------------------------------------------
def check_deep_relative_path(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if is_comment(line):
            continue
        # 4+ levels of ../
        if re.search(r"\.\./\.\./\.\./\.\.", line):
            findings.append(Finding(
                path, i + 1, "low", "S26",
                "Deep relative path navigation (4+ levels up) - fragile fallback",
                "Require explicit path argument instead of guessing"
            ))
    return findings


# ---------------------------------------------------------------------------
# S27: Stale global variable not reset in loop
# Bug class: #32
# ---------------------------------------------------------------------------
def check_stale_global(path: str, content: str, lines: List[str]) -> List[Finding]:
    findings = []
    # Find global VAR="" assignments (uppercase with STDERR/OUTPUT/RESULT/ERR suffix)
    for i, line in enumerate(lines):
        m = re.match(r'^([A-Z_]+(STDERR|OUTPUT|RESULT|ERR))=""', line)
        if not m:
            continue
        var = m.group(1)
        # Check if used in a subsequent loop without reset
        rest = lines[i + 1:min(i + 60, len(lines))]
        rest_text = "\n".join(rest)
        has_loop = bool(re.search(r"\bwhile\b.*\bread\b|\bfor\b.*\bin\b", rest_text))
        has_usage = bool(re.search(rf"\${{?{var}}}?", rest_text))
        has_reset = bool(re.search(rf'^(\s+){var}=(""|\'\'|\$\()', rest_text, re.MULTILINE))
        if has_loop and has_usage and not has_reset:
            findings.append(Finding(
                path, i + 1, "low", "S27",
                f"${var} set once but used in loop without per-iteration reset",
                "Reset at top of loop body to avoid stale values"
            ))
    return findings


# ---------------------------------------------------------------------------
# All checks
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    # Critical
    check_pipe_delimiter,        # S01 - Bug #1
    check_suppressed_exit_code,  # S02 - Bug #2
    check_sed_empty_var,         # S03 - Bug #5
    check_template_mismatch,     # S04 - Bug #4
    # Medium: JSON safety
    check_json_no_escape,        # S05 - Bugs #6, #34
    check_json_escape_incomplete,  # S06 - Bug #9
    # Medium: Array/splitting
    check_space_delimited_list,  # S07 - Bug #7
    check_for_in_expansion,      # S08 - Bug #13
    check_empty_array_crash,     # S09 - Bugs #14, #15
    check_unquoted_var_cmd,      # S10 - Bug #16
    # Medium: Grep/regex safety
    check_grep_var_no_fixed,     # S11 - Bugs #3, #22, #24
    check_grep_pipe_no_guard,    # S12 - Bug #26
    check_grep_cmd_in_prose,     # S13 - Bugs #19, #33
    # Medium: Exit code / subprocess
    check_destructive_git,       # S14 - Bug #21
    check_mktemp_no_trap,        # S15 - Bug #10
    # Medium: Injection
    check_heredoc_injection,     # S16 - Bug #17
    check_jq_injection,          # S17 - Bug #35
    # Medium: YAML / parsing
    check_yaml_no_quote_strip,   # S18 - Bug #8
    check_no_pagination,         # S19 - Bug #18
    check_no_codeblock_tracking,  # S20 - Bug #20
    check_awk_diff_collision,    # S21 - Bug #12
    # Low
    check_echo_wc_offbyone,      # S22 - Bug #28
    check_timestamp_collision,   # S23 - Bug #29
    check_cut_colon_paths,       # S24 - Bug #25
    check_fragile_output_parse,  # S25 - Bug #27
    check_deep_relative_path,    # S26 - Bug #30
    check_stale_global,          # S27 - Bug #32
]


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def scan_file(path: str) -> List[Finding]:
    try:
        content = Path(path).read_text(errors="replace")
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return []
    lines = content.splitlines()
    findings = []
    for check_fn in ALL_CHECKS:
        try:
            findings.extend(check_fn(path, content, lines))
        except Exception as e:
            print(f"Warning: {check_fn.__name__} failed on {path}: {e}",
                  file=sys.stderr)
    return findings


def collect_files(target: str) -> List[str]:
    p = Path(target)
    if p.is_file():
        return [str(p)]
    if p.is_dir():
        return sorted(str(f) for f in p.rglob("*.sh") if f.is_file())
    print(f"Error: {target} is not a file or directory", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def json_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def format_finding_text(f: Finding) -> str:
    label = {"critical": "CRT", "medium": "MED", "low": "LOW"}.get(f.severity, "???")
    basename = os.path.basename(f.file)
    out = f"[{label}] {f.check}: {basename}:{f.line} -- {f.message}"
    if f.evidence:
        out += f"\n       {f.evidence}"
    return out


def format_finding_json(f: Finding) -> str:
    return jsonmod.dumps({
        "file": f.file,
        "line": f.line,
        "severity": f.severity,
        "check": f.check,
        "message": f.message,
        "evidence": f.evidence,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Static analysis linter for shell scripts"
    )
    parser.add_argument("target", help="File or directory to scan")
    parser.add_argument("--json", action="store_true", help="Output NDJSON")
    parser.add_argument(
        "--severity", default="all",
        choices=["critical", "medium", "low", "all"],
        help="Minimum severity to show (default: all)"
    )
    args = parser.parse_args()

    files = collect_files(args.target)
    if not files:
        print("No .sh files found", file=sys.stderr)
        sys.exit(0)

    filter_rank = SEVERITY_RANK.get(args.severity, 0)

    all_findings = []
    for f in files:
        all_findings.extend(scan_file(f))

    # Apply severity filter
    if args.severity != "all":
        all_findings = [
            f for f in all_findings
            if SEVERITY_RANK.get(f.severity, 0) >= filter_rank
        ]

    # Output
    for f in all_findings:
        if args.json:
            print(format_finding_json(f))
        else:
            print(format_finding_text(f))

    # Summary
    if args.json:
        print(jsonmod.dumps({"summary": True, "findings": len(all_findings)}))
    else:
        if all_findings:
            print(f"\n{len(all_findings)} finding(s) total.")
        else:
            print("No findings.")

    sys.exit(1 if all_findings else 0)


if __name__ == "__main__":
    main()
