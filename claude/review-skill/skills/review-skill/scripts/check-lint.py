#!/usr/bin/env python3
"""Static analysis for shell and Python scripts.

This tool runs three layers of checks:
- custom shell heuristics (`CL-S01`..`CL-S27`)
- shellcheck integration (when installed)
- ruff integration for Python files (when installed)

Output modes:
- human-readable text
- NDJSON via `--json`

Exit codes:
- 0 when no findings remain after filtering
- 1 when findings remain after filtering
- 2 for usage/input errors
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from _skill_check_common import FindingRecord, SummaryRecord

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    Rule = Callable[["ScanContext"], list["FindingRecord"]]


@dataclass(frozen=True)
class ScanContext:
    """Shell script source and derived metadata used by custom checks."""

    path: Path
    content: str
    lines: tuple[str, ...]
    has_set_u: bool
    has_pipefail: bool


SEVERITY_RANK: Final[dict[str, int]] = {
    "critical": 3,
    "medium": 2,
    "low": 1,
}

SHELLCHECK_SEVERITY_MAP: Final[dict[str, str]] = {
    "error": "critical",
    "warning": "medium",
    "info": "low",
    "style": "low",
}

# Longest-prefix match. Keep specific prefixes before broad ones.
RUFF_PREFIX_SEVERITY: Final[tuple[tuple[str, str], ...]] = (
    ("E501", "low"),
    ("PLE", "critical"),
    ("PLW", "medium"),
    ("PLR", "low"),
    ("S", "critical"),
    ("F", "critical"),
    ("E", "critical"),
    ("B", "medium"),
    ("W", "low"),
    ("C", "low"),
    ("D", "low"),
    ("Q", "low"),
    ("COM", "low"),
    ("I", "low"),
    ("N", "low"),
    ("UP", "low"),
    ("ANN", "low"),
    ("A", "low"),
    ("FBT", "low"),
    ("T", "low"),
    ("SIM", "low"),
    ("PTH", "low"),
    ("RUF", "low"),
    ("ARG", "low"),
    ("ERA", "low"),
    ("TRY", "low"),
    ("PERF", "low"),
    ("BLE", "medium"),
    ("G", "low"),
    ("LOG", "low"),
    ("PT", "low"),
    ("RSE", "low"),
    ("PIE", "low"),
    ("ISC", "low"),
    ("YTT", "low"),
    ("ICN", "low"),
    ("INP", "low"),
    ("PYI", "low"),
    ("FURB", "low"),
    ("ASYNC", "low"),
    ("FA", "low"),
    ("TC", "low"),
    ("DJ", "low"),
    ("EM", "low"),
    ("EXE", "low"),
    ("FLY", "low"),
    ("INT", "low"),
    ("PD", "low"),
    ("NPY", "low"),
    ("AIR", "low"),
    ("SLOT", "low"),
    ("TD", "low"),
    ("FIX", "low"),
    ("TID", "low"),
    ("RET", "low"),
    ("SLF", "low"),
    ("TRIO", "low"),
)

PROSE_COMMAND_WORDS: Final[frozenset[str]] = frozenset({
    "make", "test", "find", "sort", "head", "cut",
    "split", "join", "read", "link", "diff", "patch",
    "date", "time", "file", "last", "watch", "kill",
})

SET_U_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bset\b[^#\n]*\s-[A-Za-z]*u[A-Za-z]*\b|\bset\s+-o\s+nounset\b",
)
PIPEFAIL_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bset\b[^#\n]*\bpipefail\b",
)
FUNCTION_DEF_RE: Final[re.Pattern[str]] = re.compile(r"^(\w+)\(\)\s*\{")
WHILE_READ_RE: Final[re.Pattern[str]] = re.compile(r"\bwhile\b.*\bread\b")
LOOP_KEYWORD_RE: Final[re.Pattern[str]] = re.compile(r"\b(while|for|until)\b")
DONE_RE: Final[re.Pattern[str]] = re.compile(r"\s*done\b")

DESTRUCTIVE_GIT_RE: Final[re.Pattern[str]] = re.compile(
    r"git\s+(branch\s+-[dD]|worktree\s+remove|reset\s+--hard|clean\s+-[fd])",
)
MKTEMP_RE: Final[re.Pattern[str]] = re.compile(r"\bmktemp\b")
TRAP_CLEANUP_RE: Final[re.Pattern[str]] = re.compile(
    r"trap\s+.*(EXIT|cleanup|_cleanup)",
)
TMPFILES_TRACKING_RE: Final[re.Pattern[str]] = re.compile(r"_TMPFILES\+\=")

LIMIT_PATTERN_RE: Final[re.Pattern[str]] = re.compile(
    r"first:\s*\d+|per_page|[?&]limit=\d+",
)
PAGINATION_PATTERN_RE: Final[re.Pattern[str]] = re.compile(
    r"hasNextPage|next_page|cursor|pageInfo|page_info|pagination",
    re.IGNORECASE,
)

# Hoisted static patterns (previously inline re.search/re.match calls).
SUPPRESSED_GREP_C_RE: Final[re.Pattern[str]] = re.compile(
    r"2>/dev/null.*\|\s*grep\s+-c",
)
PLACEHOLDER_RE: Final[re.Pattern[str]] = re.compile(r"__([A-Z_]+)__")
JSON_ECHO_RE: Final[re.Pattern[str]] = re.compile(r'echo\s+"?\{.*\\"')
JSON_ESCAPE_FN_RE: Final[re.Pattern[str]] = re.compile(r"json_escape\s*\(\)")
FOR_IN_EXPANSION_RE: Final[re.Pattern[str]] = re.compile(
    r"\bfor\s+\w+\s+in\s+\$\(",
)
PIPE_GREP_RE: Final[re.Pattern[str]] = re.compile(r"\|\s*grep\s")
CONDITIONAL_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"\s*(if|while|elif)\s",
)
GREP_COUNT_FLAG_RE: Final[re.Pattern[str]] = re.compile(
    r"grep\s+[^|]*-[a-zA-Z]*c",
)
COLON_GUARD_RE: Final[re.Pattern[str]] = re.compile(
    r"\|\|\s*:(?:\s*[)#]|\s*$)",
)
ALPHA_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+")
IF_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"\s*if\s")
JQ_COMMAND_RE: Final[re.Pattern[str]] = re.compile(r"\bjq\b")
DOUBLE_QUOTED_RHS_RE: Final[re.Pattern[str]] = re.compile(r'="(.*)"')
LHS_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(r"\s*(\w+)=")
SED_QUOTE_STRIP_RE: Final[re.Pattern[str]] = re.compile(r"sed.*s/.*[\"']")
TR_DELETE_QUOTE_RE: Final[re.Pattern[str]] = re.compile(r"tr\s+-d\s+[\"']")
BULLET_VAR_RE: Final[re.Pattern[str]] = re.compile(r"BULLET|bullet")
BLOCK_TRACKING_RE: Final[re.Pattern[str]] = re.compile(
    r"IN_BLOCK|in_block|code_block|fenced|BVP_IN_BLOCK",
)
AWK_TRIPLE_DASH_RE: Final[re.Pattern[str]] = re.compile(
    r"awk.*\^---|/\^---/",
)
DIFF_STATE_TRACKING_RE: Final[re.Pattern[str]] = re.compile(
    r"got_minus|got_plus|header_state|in_header",
)
ECHO_WC_L_RE: Final[re.Pattern[str]] = re.compile(
    r'echo\s+"?\$\w.*\|\s*wc\s+-l',
)
DATE_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(r"(\w+)=.*\bdate\b.*\+")
FILE_EXTENSION_RE: Final[re.Pattern[str]] = re.compile(
    r"\.(log|txt|md|yaml|json|sh)\b",
)
PATH_VAR_RE: Final[re.Pattern[str]] = re.compile(r"/\$")
SED_PATTERN_RE: Final[re.Pattern[str]] = re.compile(r"\bsed\b|s/.*/")
CUT_COLON_RE: Final[re.Pattern[str]] = re.compile(
    r"cut\s+-d[':]\s*-f|cut\s+-d:\s+-f",
)
PATH_CONTEXT_RE: Final[re.Pattern[str]] = re.compile(
    r"file|path|spec|range|RANGE",
    re.IGNORECASE,
)
HEAD_TAIL_ASSIGN_RE: Final[re.Pattern[str]] = re.compile(
    r"(\w+)=\$\((head|tail)\s+-n\s*1",
)
HEAD_TAIL_BARE_RE: Final[re.Pattern[str]] = re.compile(
    r"(\w+)=\$\((head|tail)\s",
)
DEEP_RELATIVE_RE: Final[re.Pattern[str]] = re.compile(r"\.\./\.\./\.\./\.\.")
STALE_GLOBAL_RE: Final[re.Pattern[str]] = re.compile(
    r'^([A-Z_]+(STDERR|OUTPUT|RESULT|ERR))=""',
)
LOOP_PATTERN_RE: Final[re.Pattern[str]] = re.compile(
    r"\bwhile\b.*\bread\b|\bfor\b.*\bin\b",
)
HEREDOC_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<<-?\s*(\w+)")
HEREDOC_QUOTED_RE: Final[re.Pattern[str]] = re.compile(r"<<-?\s*['\"]")
HEREDOC_ESCAPED_RE: Final[re.Pattern[str]] = re.compile(r"<<-?\s*\\")

_GREP_OPTIONS_WITH_ARG: Final[frozenset[str]] = frozenset({
    "-e", "-f", "-m", "-A", "-B", "-C",
    "--regexp", "--file", "--max-count",
    "--after-context", "--before-context", "--context",
    "--label", "--include", "--exclude", "--exclude-dir",
    "--color", "--colours",
})


def _is_comment(line: str) -> bool:
    """Return whether a line is a shell comment after left trim."""
    return line.lstrip().startswith("#")


def _iter_non_comment_lines(lines: Sequence[str]) -> Sequence[str]:
    """Return lines that are not shell comments."""
    return [line for line in lines if not _is_comment(line)]


def _detect_set_u(lines: Sequence[str]) -> bool:
    """Return whether script enables nounset mode on non-comment lines."""
    return any(SET_U_LINE_RE.search(line) for line in _iter_non_comment_lines(lines))


def _detect_pipefail(lines: Sequence[str]) -> bool:
    """Return whether script enables pipefail on non-comment lines."""
    return any(PIPEFAIL_LINE_RE.search(line) for line in _iter_non_comment_lines(lines))


def _extract_function_body(
    lines: Sequence[str],
    func_line: int,
    *,
    max_lines: int = 30,
) -> str:
    """Extract a shell function body starting at line index `func_line`."""
    depth = 0
    body_lines: list[str] = []
    upper = min(func_line + max_lines, len(lines))

    for index in range(func_line, upper):
        line = lines[index]
        depth += line.count("{") - line.count("}")
        body_lines.append(line)
        if depth <= 0 and index > func_line:
            break

    return "\n".join(body_lines)


def _find_while_read_loops(lines: Sequence[str]) -> list[tuple[int, int]]:
    """Return `(start, end)` indices for while-read loops."""
    loops: list[tuple[int, int]] = []
    index = 0

    while index < len(lines):
        current = lines[index]
        if _is_comment(current) or not WHILE_READ_RE.search(current):
            index += 1
            continue

        start = index
        depth = 0
        found_end = False

        for end in range(index, len(lines)):
            stripped = lines[end].lstrip()
            if _is_comment(stripped):
                continue
            if LOOP_KEYWORD_RE.search(stripped):
                depth += 1
            if DONE_RE.match(stripped) and depth > 0:
                depth -= 1
                if depth == 0:
                    loops.append((start, end))
                    index = end
                    found_end = True
                    break

        if not found_end:
            loops.append((start, min(start + 50, len(lines) - 1)))

        index += 1

    return loops


def _shell_tokens(line: str) -> list[str] | None:
    """Split one shell line into tokens, returning None on parse errors."""
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        return None


def _grep_tokens(line: str) -> list[str] | None:
    """Return token slice starting after first `grep` token, or None."""
    tokens = _shell_tokens(line)
    if not tokens:
        return None

    for index, arg in enumerate(tokens):
        if arg == "grep" or arg.endswith("/grep"):
            return tokens[index + 1 :]
    return None


def _grep_has_fixed_flag(tokens: Sequence[str]) -> bool:
    """Return whether grep options include fixed-string mode."""
    for arg in tokens:
        if arg == "--":
            break
        if arg == "--fixed-strings":
            return True
        if arg.startswith("-") and "F" in arg[1:]:
            return True
    return False


def _first_grep_pattern_token(tokens: Sequence[str]) -> str | None:
    """Return the first non-option grep token interpreted as pattern."""
    index = 0
    while index < len(tokens):
        arg = tokens[index]
        if arg == "--":
            index += 1
            break
        if arg.startswith("-") and arg != "-":
            if arg in _GREP_OPTIONS_WITH_ARG:
                index += 2
            else:
                index += 1
            continue
        break

    if index >= len(tokens):
        return None
    return tokens[index]


def _grep_ignore_case(tokens: Sequence[str]) -> bool:
    """Return whether grep token list enables case-insensitive mode."""
    for arg in tokens:
        if arg == "--":
            break
        if arg in {"-i", "--ignore-case"}:
            return True
        if arg.startswith("-") and "i" in arg[1:]:
            return True
    return False


def _ruff_severity(rule_code: str) -> str:
    """Map a Ruff rule code to severity using longest-prefix matching."""
    for prefix, severity in RUFF_PREFIX_SEVERITY:
        if rule_code.startswith(prefix):
            return severity
    return "low"


def _new_context(path: Path, content: str) -> ScanContext:
    """Build a reusable shell scan context for one file."""
    lines = tuple(content.splitlines())
    return ScanContext(
        path=path,
        content=content,
        lines=lines,
        has_set_u=_detect_set_u(lines),
        has_pipefail=_detect_pipefail(lines),
    )


def _check_pipe_delimiter(context: ScanContext) -> list[FindingRecord]:
    """Flag IFS='|' with read - pipe in data corrupts parsing."""
    findings: list[FindingRecord] = []
    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        has_pipe_ifs = "IFS='|'" in line or 'IFS="|"' in line
        if has_pipe_ifs and "read" in line:
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="critical",
                    check="CL-S01",
                    message=(
                        "Using | as field delimiter with read - data containing "
                        "pipes corrupts parsing"
                    ),
                    evidence="Use ASCII unit separator: IFS=$'\\x1f'",
                ),
            )
    return findings


def _check_suppressed_exit_code(context: ScanContext) -> list[FindingRecord]:
    """Flag stderr suppression before grep -c."""
    findings: list[FindingRecord] = []
    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if SUPPRESSED_GREP_C_RE.search(line):
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="critical",
                    check="CL-S02",
                    message=(
                        "Exit code suppressed (2>/dev/null) then piped to grep -c - "
                        "command failure produces count 0 (wrong default)"
                    ),
                    evidence="Check command exit code separately before counting",
                ),
            )
    return findings


def _check_sed_empty_var(context: ScanContext) -> list[FindingRecord]:
    """Flag sed with variable in range that crashes if empty."""
    findings: list[FindingRecord] = []
    pattern = re.compile(r"sed\s+(-n\s+)?[\"']?\$\{?(\w+)\}?.*,")

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue

        match = pattern.search(line)
        if not match:
            continue

        variable = match.group(2)
        escaped_var = re.escape(variable)
        guard_region = "\n".join(
            line_part
            for line_part in context.lines[max(0, index - 8) : index + 1]
            if not _is_comment(line_part)
        )
        guard_pattern = re.compile(
            rf"(if\s+)?\[\[?\s*-n\s+\"?\$\{{?{escaped_var}\}}?\"?\s*\]\]?"
            rf"|test\s+-n\s+\"?\$\{{?{escaped_var}\}}?\"?",
        )
        if guard_pattern.search(guard_region):
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="critical",
                check="CL-S03",
                message=(
                    f"sed with ${{{variable}}} in range - crashes if variable is empty"
                ),
                evidence=f'Guard with: if [[ -n "${variable}" ]]',
            ),
        )

    return findings


def _check_template_mismatch(context: ScanContext) -> list[FindingRecord]:
    """Flag template placeholders that don't match script substitutions."""
    findings: list[FindingRecord] = []
    placeholders = set(PLACEHOLDER_RE.findall(context.content))
    if not placeholders:
        return findings

    script_dir = context.path.parent
    parent_dir = script_dir.parent
    templates = {
        *parent_dir.rglob("*.template.*"),
        *parent_dir.rglob("*.tmpl"),
    }

    for template_path in sorted(templates):
        try:
            template_content = template_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        template_lines = template_content.splitlines()
        for placeholder in placeholders:
            bold_form = f"**{placeholder}**"
            for line_index, line in enumerate(template_lines):
                if bold_form not in line:
                    continue
                findings.append(
                    FindingRecord(
                        file=str(template_path),
                        line=line_index + 1,
                        severity="critical",
                        check="CL-S04",
                        message=(
                            f"Template uses {bold_form} but script substitutes "
                            f"__{placeholder}__"
                        ),
                        evidence=(
                            f"Change {bold_form} to __{placeholder}__ in the template"
                        ),
                    ),
                )
    return findings


def _check_json_no_escape(context: ScanContext) -> list[FindingRecord]:
    """Flag JSON output without escape helpers."""
    findings: list[FindingRecord] = []
    json_output_lines: list[int] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if JSON_ECHO_RE.search(line):
            json_output_lines.append(index)

    if not json_output_lines:
        return findings

    has_escape = JSON_ESCAPE_FN_RE.search(context.content) is not None
    emit_index = next(
        (
            index
            for index, line in enumerate(context.lines)
            if re.match(r"^emit\(\)\s*\{", line)
        ),
        None,
    )
    if emit_index is not None:
        emit_body = _extract_function_body(context.lines, emit_index)
        if "\\\\n" in emit_body or "$'\\n'" in emit_body:
            has_escape = True

    if has_escape:
        return findings

    first_line = json_output_lines[0]
    findings.append(
        FindingRecord(
            file=str(context.path),
            line=first_line + 1,
            severity="medium",
            check="CL-S05",
            message=(
                "Script outputs JSON but has no json_escape/emit helper - "
                "user content with backslashes/quotes/newlines breaks JSON"
            ),
            evidence='Add escaping for \\, ", \\n, \\t, \\r',
        ),
    )
    return findings


def _check_json_escape_incomplete(context: ScanContext) -> list[FindingRecord]:
    """Flag JSON escape functions missing newline/tab/CR handling."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        match = FUNCTION_DEF_RE.match(line)
        if not match:
            continue

        function_name = match.group(1)
        body = _extract_function_body(context.lines, index)
        has_backslash = "//\\\\/" in body
        has_quote = '//\\"/' in body
        if not (has_backslash and has_quote):
            continue

        has_newline = "\\\\n" in body or "$'\\n'" in body
        if has_newline:
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S06",
                message=(
                    f'JSON escaping in {function_name}() handles \\ and " but not '
                    "newlines/tabs/CRs - multi-line input breaks JSON"
                ),
                evidence="Add: ${var//$'\\n'/\\\\n} and same for \\t, \\r",
            ),
        )

    return findings


def _check_space_delimited_list(context: ScanContext) -> list[FindingRecord]:
    """Flag space-delimited string accumulation instead of arrays."""
    findings: list[FindingRecord] = []
    pattern = re.compile(r"(\w+)=\"\$\{?\1\}?\s")

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        match = pattern.search(line)
        if not match:
            continue

        variable = match.group(1)
        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S07",
                message=(
                    f"Space-delimited string accumulation for {variable} - "
                    "filenames with spaces break"
                ),
                evidence='Use a bash array: arr+=("$item")',
            ),
        )

    return findings


def _check_for_in_expansion(context: ScanContext) -> list[FindingRecord]:
    """Flag for-in with unquoted command substitution."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if not FOR_IN_EXPANSION_RE.search(line):
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S08",
                message=(
                    "for-in with unquoted $() - word-splits on spaces in filenames"
                ),
                evidence="Use: while IFS= read -r var; do ... done < <(command)",
            ),
        )

    return findings


def _check_empty_array_crash(context: ScanContext) -> list[FindingRecord]:
    """Flag empty array expansion that crashes under set -u."""
    if not context.has_set_u:
        return []

    findings: list[FindingRecord] = []
    match_re = re.compile(r"\"\$\{(\w+)\[@\]\}\"")

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue

        for match in match_re.finditer(line):
            array_name = match.group(1)
            full_tail = line[match.start() :]
            if re.match(r"\"\$\{\w+\[@\]\+", full_tail):
                continue

            before = line[: match.start()]
            guard_re = re.compile(rf"\$\{{{array_name}\[@\]\+")
            if guard_re.search(before):
                continue

            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="medium",
                    check="CL-S09",
                    message=(
                        f'"${{{array_name}[@]}}" crashes under set -u '
                        "if array is empty (bash < 4.4)"
                    ),
                    evidence=f'Use: ${{{array_name}[@]+"${{{array_name}[@]}}"}}',
                ),
            )

    return findings


def _check_unquoted_var_cmd(context: ScanContext) -> list[FindingRecord]:
    """Flag unquoted variable in command substitution."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if re.search(r"\$\(\s*\$\{", line) and not re.search(
            r"\$\(\s*\"\$\{",
            line,
        ):
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="medium",
                    check="CL-S10",
                    message=(
                        "Unquoted ${var} in command substitution - "
                        "breaks on paths with spaces"
                    ),
                    evidence='Quote: $("${var}" ...)',
                ),
            )

    return findings


def _check_grep_var_no_fixed(context: ScanContext) -> list[FindingRecord]:
    """Flag grep with variable pattern but no -F flag."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line) or "grep" not in line:
            continue

        tokens = _grep_tokens(line)
        if not tokens or _grep_has_fixed_flag(tokens):
            continue

        pattern_token = _first_grep_pattern_token(tokens)
        if not pattern_token:
            continue

        if re.search(r"\$\{?\w+", pattern_token):
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="medium",
                    check="CL-S11",
                    message=(
                        "grep with variable in pattern but no -F - "
                        "variable content treated as regex"
                    ),
                    evidence="Use grep -F for fixed strings, or escape the variable",
                ),
            )

    return findings


def _check_grep_pipe_no_guard(context: ScanContext) -> list[FindingRecord]:
    """Flag grep in pipeline without || true under pipefail."""
    if not context.has_pipefail:
        return []

    findings: list[FindingRecord] = []
    guard_re = re.compile(r"\|\|\s*(true|false|:|exit|return|\{)")

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if not PIPE_GREP_RE.search(line):
            continue
        if guard_re.search(line):
            continue
        if CONDITIONAL_PREFIX_RE.match(line):
            continue
        if GREP_COUNT_FLAG_RE.search(line):
            continue
        if COLON_GUARD_RE.search(line):
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="low",
                check="CL-S12",
                message=(
                    "grep in pipeline without || true - kills script under "
                    "pipefail if no match"
                ),
                evidence=line.lstrip()[:120],
            ),
        )

    return findings


def _check_grep_cmd_in_prose(context: ScanContext) -> list[FindingRecord]:
    """Flag case-insensitive grep for common command words."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line) or "grep" not in line:
            continue

        tokens = _grep_tokens(line)
        if not tokens or not _grep_ignore_case(tokens):
            continue

        pattern_token = _first_grep_pattern_token(tokens)
        if pattern_token is None:
            continue

        normalized = pattern_token.strip("'\"")
        if normalized.lower() not in PROSE_COMMAND_WORDS:
            continue
        if not ALPHA_WORD_RE.fullmatch(normalized):
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S13",
                message=(
                    f"Case-insensitive grep for '{normalized.lower()}' matches prose"
                ),
                evidence="Use case-sensitive grep or anchor to command context",
            ),
        )

    return findings


def _check_destructive_git(context: ScanContext) -> list[FindingRecord]:
    """Flag destructive git operations without error handling."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line) or not DESTRUCTIVE_GIT_RE.search(line):
            continue
        if IF_PREFIX_RE.match(line):
            continue
        if index > 0 and IF_PREFIX_RE.match(context.lines[index - 1]):
            continue
        if "||" in line:
            continue

        stderr_suppressed = "2>/dev/null" in line or "2>&1" in line
        suffix = " (stderr suppressed)" if stderr_suppressed else ""
        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S14",
                message=f"Destructive git operation without error handling{suffix}",
                evidence=line.strip()[:120],
            ),
        )

    return findings


def _check_mktemp_no_trap(context: ScanContext) -> list[FindingRecord]:
    """Flag mktemp calls without cleanup trap."""
    mktemp_lines = [
        index
        for index, line in enumerate(context.lines)
        if not _is_comment(line) and MKTEMP_RE.search(line)
    ]
    if not mktemp_lines:
        return []

    if TRAP_CLEANUP_RE.search(context.content) or TMPFILES_TRACKING_RE.search(
        context.content,
    ):
        return []

    first_line = mktemp_lines[0] + 1
    return [
        FindingRecord(
            file=str(context.path),
            line=first_line,
            severity="medium",
            check="CL-S15",
            message=f"{len(mktemp_lines)} mktemp call(s) but no cleanup mechanism",
            evidence="Add trap cleanup or _TMPFILES tracking",
        ),
    ]


def _check_heredoc_injection(context: ScanContext) -> list[FindingRecord]:
    """Flag interpolating heredocs that enable injection."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue

        match = HEREDOC_TAG_RE.search(line)
        if not match:
            continue
        if HEREDOC_QUOTED_RE.search(line) or HEREDOC_ESCAPED_RE.search(line):
            continue

        tag = match.group(1)
        body_has_var = False
        for offset in range(index + 1, min(index + 100, len(context.lines))):
            body_line = context.lines[offset]
            if body_line.strip() == tag:
                break
            if not _is_comment(body_line) and re.search(r"\$\{?\w+", body_line):
                body_has_var = True
                break

        if not body_has_var:
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S16",
                message=(
                    f"Interpolating heredoc <<{tag} - shell variables expand inside, "
                    "enabling injection"
                ),
                evidence=(
                    f"Use <<'{tag}' for literal content, pass variables via flags"
                ),
            ),
        )

    return findings


def _check_jq_injection(context: ScanContext) -> list[FindingRecord]:
    """Flag variable interpolation in jq filters."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue

        if re.search(r"\w*(?:FILTER|JQ)\w*=.*\$\{", line, re.IGNORECASE):
            assign_match = DOUBLE_QUOTED_RHS_RE.search(line)
            if assign_match:
                rhs = assign_match.group(1)
                var_refs = re.findall(r"\$\{(\w+)\}", rhs)
                lhs_match = LHS_ASSIGN_RE.match(line)
                lhs = lhs_match.group(1) if lhs_match else ""
                non_self = [value for value in var_refs if value != lhs]
                if non_self:
                    findings.append(
                        FindingRecord(
                            file=str(context.path),
                            line=index + 1,
                            severity="medium",
                            check="CL-S17",
                            message=(
                                "Variable interpolated in jq filter string - "
                                "enables jq injection"
                            ),
                            evidence=(
                                'Use jq --arg varname "$VAR" and '
                                "reference $varname in filter"
                            ),
                        ),
                    )
                    continue

        if not JQ_COMMAND_RE.search(line) or "${" not in line:
            continue

        cleaned = re.sub(r"\$\{\w+\[@\][^}]*\}", "", line)
        if "${" not in cleaned or "--arg" in line:
            continue

        jq_match = JQ_COMMAND_RE.search(cleaned)
        if jq_match is not None:
            jq_portion = cleaned[jq_match.start() :]
            jq_portion = re.sub(r"<<<\s*\"[^\"]*\"", "", jq_portion)
            jq_portion = re.sub(r"<<<\s*'[^']*'", "", jq_portion)
            jq_portion = re.sub(r"<<<\s*\S+", "", jq_portion)
            if "${" not in jq_portion:
                continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S17",
                message=(
                    "Variable interpolated in jq invocation - enables jq injection"
                ),
                evidence='Use jq --arg varname "$VAR" and reference $varname in filter',
            ),
        )

    return findings


def _check_yaml_no_quote_strip(context: ScanContext) -> list[FindingRecord]:
    """Flag YAML parser functions that don't strip quotes."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        match = re.match(r"^(\w*get_field\w*)\(\)\s*\{", line)
        if not match:
            continue

        function_name = match.group(1)
        body = _extract_function_body(context.lines, index)
        strips_with_sed = SED_QUOTE_STRIP_RE.search(body) is not None
        strips_with_tr = TR_DELETE_QUOTE_RE.search(body) is not None
        if strips_with_sed or strips_with_tr:
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="medium",
                check="CL-S18",
                message=(
                    f"YAML parser {function_name}() doesn't strip quotes - "
                    'name: "foo" returns "foo" with quotes'
                ),
                evidence='Add: | sed "s/^[\\"\']//; s/[\\"\']$//"',
            ),
        )

    return findings


def _check_no_pagination(context: ScanContext) -> list[FindingRecord]:
    """Flag API queries with fixed limit but no pagination."""
    if not LIMIT_PATTERN_RE.search(context.content):
        return []
    if PAGINATION_PATTERN_RE.search(context.content):
        return []

    for index, line in enumerate(context.lines):
        if LIMIT_PATTERN_RE.search(line):
            return [
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="medium",
                    check="CL-S19",
                    message=(
                        "API query with fixed limit but no pagination - "
                        "silently drops data"
                    ),
                    evidence=(
                        "Add cursor-based pagination or warn "
                        "when result count equals limit"
                    ),
                ),
            ]

    return []


def _check_no_codeblock_tracking(context: ScanContext) -> list[FindingRecord]:
    """Flag markdown processors counting bullets without fence tracking."""
    findings: list[FindingRecord] = []

    for start, end in _find_while_read_loops(context.lines):
        loop_body = "\n".join(context.lines[start : end + 1])
        if BULLET_VAR_RE.search(loop_body) is None:
            continue
        if BLOCK_TRACKING_RE.search(loop_body):
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=start + 1,
                severity="medium",
                check="CL-S20",
                message=(
                    "Markdown line processing counts bullets but doesn't track "
                    "fenced code block state"
                ),
                evidence=(
                    "Code inside ``` blocks will be miscounted as bullets/paragraphs"
                ),
            ),
        )

    return findings


def _check_awk_diff_collision(context: ScanContext) -> list[FindingRecord]:
    """Flag awk matching ^--- without diff header state tracking."""
    if AWK_TRIPLE_DASH_RE.search(context.content) is None:
        return []
    if DIFF_STATE_TRACKING_RE.search(context.content):
        return []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if AWK_TRIPLE_DASH_RE.search(line):
            return [
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="medium",
                    check="CL-S21",
                    message=(
                        "Awk matches ^--- without header state tracking - "
                        "diff body lines starting with --- confuse parser"
                    ),
                    evidence=(
                        "Track got_minus/got_plus flags to distinguish "
                        "headers from body"
                    ),
                ),
            ]

    return []


def _check_echo_wc_offbyone(context: ScanContext) -> list[FindingRecord]:
    """Flag echo var | wc -l off-by-one from trailing newline."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if ECHO_WC_L_RE.search(line):
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="low",
                    check="CL-S22",
                    message=(
                        'echo "$var" | wc -l - echo adds trailing newline, off-by-one'
                    ),
                    evidence='Use: wc -l < "$file" for file line counting',
                ),
            )

    return findings


def _check_timestamp_collision(context: ScanContext) -> list[FindingRecord]:
    """Flag timestamp in filename without PID/random suffix."""
    findings: list[FindingRecord] = []
    timestamp_vars: dict[str, int] = {}

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        match = DATE_ASSIGN_RE.search(line)
        if match:
            timestamp_vars[match.group(1)] = index

    if not timestamp_vars:
        return findings

    for variable, definition_index in timestamp_vars.items():
        upper = min(definition_index + 20, len(context.lines))
        for usage_index in range(definition_index + 1, upper):
            line = context.lines[usage_index]
            if re.search(rf"\$\{{?{variable}\}}?", line) is None:
                continue

            looks_like_filename = FILE_EXTENSION_RE.search(line)
            looks_like_path = PATH_VAR_RE.search(line)
            sed_pattern = SED_PATTERN_RE.search(line)
            if not looks_like_filename and not (looks_like_path and not sed_pattern):
                continue

            context_region = "\n".join(
                line_part
                for line_part in context.lines[definition_index : usage_index + 1]
                if not _is_comment(line_part)
            )
            if re.search(r"\$\$|\$RANDOM|\$\{RANDOM\}|\$\{PID\}", context_region):
                break

            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=definition_index + 1,
                    severity="low",
                    check="CL-S23",
                    message=(
                        "Timestamp in filename without PID/random suffix - "
                        "same-second collision"
                    ),
                    evidence="Add $$ or $RANDOM to ensure uniqueness",
                ),
            )
            break

    return findings


def _check_cut_colon_paths(context: ScanContext) -> list[FindingRecord]:
    """Flag cut -d: on path-like data."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        has_cut = CUT_COLON_RE.search(line)
        if not has_cut:
            continue

        context_line = line
        if index > 0:
            context_line = f"{context.lines[index - 1]}\n{line}"
        if PATH_CONTEXT_RE.search(context_line) is None:
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="low",
                check="CL-S24",
                message="cut -d: on path-like data - filenames with colons break",
                evidence="Use parameter expansion: ${var%%:*} and ${var#*:}",
            ),
        )

    return findings


def _check_fragile_output_parse(context: ScanContext) -> list[FindingRecord]:
    """Flag head/tail output parsed without format validation."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue

        match = HEAD_TAIL_ASSIGN_RE.search(line)
        if not match:
            match = HEAD_TAIL_BARE_RE.search(line)
        if not match:
            continue

        variable = match.group(1)
        validated = False
        upper = min(index + 10, len(context.lines))
        for cursor in range(index + 1, upper):
            validation_line = context.lines[cursor]
            if re.search(
                rf"\[\[.*\$\{{{variable}\}}.*=~.*\[0-9\]|"
                rf"\[\[.*\$\{{{variable}\}}.*-eq|"
                rf"\[\[.*\"{variable}\".*=~",
                validation_line,
            ):
                validated = True
                break

        if validated:
            continue

        findings.append(
            FindingRecord(
                file=str(context.path),
                line=index + 1,
                severity="low",
                check="CL-S25",
                message=(
                    f"External command output parsed by {match.group(2)} into "
                    f"${variable} without format validation"
                ),
                evidence=f'Validate: [[ "${variable}" =~ ^[0-9]+$ ]]',
            ),
        )

    return findings


def _check_deep_relative_path(context: ScanContext) -> list[FindingRecord]:
    """Flag 4+ level deep relative path navigation."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        if _is_comment(line):
            continue
        if DEEP_RELATIVE_RE.search(line):
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="low",
                    check="CL-S26",
                    message=(
                        "Deep relative path navigation (4+ levels up) - "
                        "fragile fallback"
                    ),
                    evidence="Require explicit path argument instead of guessing",
                ),
            )

    return findings


def _check_stale_global(context: ScanContext) -> list[FindingRecord]:
    """Flag global variable used in loop without per-iteration reset."""
    findings: list[FindingRecord] = []

    for index, line in enumerate(context.lines):
        match = STALE_GLOBAL_RE.match(line)
        if not match:
            continue

        variable = match.group(1)
        lookahead = context.lines[index + 1 : min(index + 60, len(context.lines))]
        lookahead_text = "\n".join(lookahead)
        has_loop = LOOP_PATTERN_RE.search(lookahead_text)
        has_usage = re.search(rf"\$\{{?{variable}\}}?", lookahead_text)
        has_reset = re.search(
            rf'^(\s+){variable}=(""|\'\'|\$\()',
            lookahead_text,
            re.MULTILINE,
        )

        if has_loop and has_usage and not has_reset:
            findings.append(
                FindingRecord(
                    file=str(context.path),
                    line=index + 1,
                    severity="low",
                    check="CL-S27",
                    message=(
                        f"${variable} set once but used in loop "
                        "without per-iteration reset"
                    ),
                    evidence="Reset at top of loop body to avoid stale values",
                ),
            )

    return findings


CUSTOM_SHELL_CHECKS: Final[tuple[Rule, ...]] = (
    _check_pipe_delimiter,
    _check_suppressed_exit_code,
    _check_sed_empty_var,
    _check_template_mismatch,
    _check_json_no_escape,
    _check_json_escape_incomplete,
    _check_space_delimited_list,
    _check_for_in_expansion,
    _check_empty_array_crash,
    _check_unquoted_var_cmd,
    _check_grep_var_no_fixed,
    _check_grep_pipe_no_guard,
    _check_grep_cmd_in_prose,
    _check_destructive_git,
    _check_mktemp_no_trap,
    _check_heredoc_injection,
    _check_jq_injection,
    _check_yaml_no_quote_strip,
    _check_no_pagination,
    _check_no_codeblock_tracking,
    _check_awk_diff_collision,
    _check_echo_wc_offbyone,
    _check_timestamp_collision,
    _check_cut_colon_paths,
    _check_fragile_output_parse,
    _check_deep_relative_path,
    _check_stale_global,
)


def _scan_shell_file(path: Path) -> list[FindingRecord]:
    """Run custom shell checks on one `.sh` file."""
    if path.suffix.lower() != ".sh":
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        _write_stderr(f"Error reading {path}: {error}")
        return []

    context = _new_context(path, content)
    findings: list[FindingRecord] = []
    for check_fn in CUSTOM_SHELL_CHECKS:
        findings.extend(check_fn(context))
    return findings


def _run_shellcheck(files: Sequence[Path]) -> list[FindingRecord]:
    """Run shellcheck and map diagnostics to FindingRecord records."""
    shellcheck_path = shutil.which("shellcheck")
    if shellcheck_path is None:
        return []

    findings: list[FindingRecord] = []
    for path in files:
        try:
            result = subprocess.run(  # noqa: S603
                [shellcheck_path, "-S", "warning", "-f", "json", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue

        if not result.stdout.strip():
            continue

        try:
            items = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue

        for item in items:
            level = item.get("level", "")
            severity = SHELLCHECK_SEVERITY_MAP.get(level, "low")
            code = item.get("code", 0)
            findings.append(
                FindingRecord(
                    file=str(path),
                    line=int(item.get("line", 0)),
                    severity=severity,
                    check=f"CL-SC{code}",
                    message=str(item.get("message", "")),
                    evidence=f"https://www.shellcheck.net/wiki/SC{code}",
                ),
            )

    return findings


def _run_ruff(files: Sequence[Path]) -> list[FindingRecord]:
    """Run ruff and map diagnostics to FindingRecord records."""
    ruff_path = shutil.which("ruff")
    if ruff_path is None:
        return []

    findings: list[FindingRecord] = []
    for path in files:
        try:
            result = subprocess.run(  # noqa: S603
                [ruff_path, "check", "--output-format", "json", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue

        if not result.stdout.strip():
            continue

        try:
            items = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue

        for item in items:
            code = str(item.get("code", ""))
            location = item.get("location", {})
            findings.append(
                FindingRecord(
                    file=str(path),
                    line=int(location.get("row", 0)),
                    severity=_ruff_severity(code),
                    check=f"CL-RU{code}",
                    message=str(item.get("message", "")),
                    evidence=f"https://docs.astral.sh/ruff/rules/{code}",
                ),
            )

    return findings


def _collect_files(target: Path) -> tuple[list[Path], list[Path]]:
    """Collect shell and Python files from target path."""
    if target.is_file():
        suffix = target.suffix.lower()
        if suffix == ".sh":
            return [target], []
        if suffix == ".py":
            return [], [target]
        return [], []

    if target.is_dir():
        shell_files = sorted(path for path in target.rglob("*.sh") if path.is_file())
        python_files = sorted(path for path in target.rglob("*.py") if path.is_file())
        return shell_files, python_files

    return [], []


def _format_text(finding: FindingRecord) -> str:
    """Render one finding in compact text format."""
    label = {"critical": "CRT", "medium": "MED", "low": "LOW"}.get(
        finding.severity,
        "???",
    )
    base = Path(finding.file).name
    line = f"[{label}] {finding.check}: {base}:{finding.line} -- {finding.message}"
    if finding.evidence:
        return f"{line}\n       {finding.evidence}"
    return line


def _format_json(finding: FindingRecord) -> str:
    """Render one finding as NDJSON object string."""
    return json.dumps(finding.payload(), ensure_ascii=False)


def _write_stdout(message: str) -> None:
    """Write one line to stdout."""
    sys.stdout.write(f"{message}\n")


def _write_stderr(message: str) -> None:
    """Write one line to stderr."""
    sys.stderr.write(f"{message}\n")


def _apply_severity_filter(
    findings: Sequence[FindingRecord],
    severity: str,
) -> list[FindingRecord]:
    """Filter findings by minimum severity (`all` disables filtering)."""
    if severity == "all":
        return list(findings)

    threshold = SEVERITY_RANK[severity]
    return [
        finding
        for finding in findings
        if SEVERITY_RANK.get(finding.severity, 0) >= threshold
    ]


def _sort_findings(findings: list[FindingRecord]) -> list[FindingRecord]:
    """Sort findings by severity desc, then file and line for stable output."""
    return sorted(
        findings,
        key=lambda finding: (
            -SEVERITY_RANK.get(finding.severity, 0),
            finding.file,
            finding.line,
            finding.check,
            finding.message,
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build and return CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Static analysis linter for shell and Python scripts",
    )
    parser.add_argument("target", help="File or directory to scan")
    parser.add_argument("--json", action="store_true", help="Output NDJSON")
    parser.add_argument(
        "--severity",
        default="all",
        choices=["critical", "medium", "low", "all"],
        help="Minimum severity to show (default: all)",
    )
    parser.add_argument(
        "--no-shellcheck",
        action="store_true",
        help="Skip shellcheck even if installed",
    )
    parser.add_argument(
        "--no-ruff",
        action="store_true",
        help="Skip ruff even if installed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run linter and return process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        _write_stderr(f"Error: {target} is not a file or directory")
        return 2

    shell_files, python_files = _collect_files(target)
    all_files = shell_files + python_files
    if not all_files:
        _write_stderr("No .sh or .py files found")
        return 0

    findings: list[FindingRecord] = []
    for shell_file in shell_files:
        findings.extend(_scan_shell_file(shell_file))

    if not args.no_shellcheck and shell_files:
        findings.extend(_run_shellcheck(shell_files))

    if not args.no_ruff and python_files:
        findings.extend(_run_ruff(python_files))

    filtered = _sort_findings(_apply_severity_filter(findings, args.severity))

    for finding in filtered:
        if args.json:
            _write_stdout(_format_json(finding))
        else:
            _write_stdout(_format_text(finding))

    critical_count = sum(1 for finding in filtered if finding.severity == "critical")
    medium_count = sum(1 for finding in filtered if finding.severity == "medium")
    low_count = sum(1 for finding in filtered if finding.severity == "low")

    if args.json:
        summary = SummaryRecord(
            total=len(filtered),
            passed=0,
            failed=0,
            extras={
                "critical": critical_count,
                "findings": len(filtered),
                "low": low_count,
                "medium": medium_count,
            },
        )
        _write_stdout(json.dumps(summary.payload(), ensure_ascii=False))
    elif filtered:
        _write_stdout("")
        _write_stdout(f"{len(filtered)} finding(s) total.")
    else:
        _write_stdout("No findings.")

    return 1 if filtered else 0


if __name__ == "__main__":
    raise SystemExit(main())
