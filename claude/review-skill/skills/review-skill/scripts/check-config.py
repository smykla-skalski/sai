#!/usr/bin/env python3
"""Validate configuration and tool-usage checks for a skill.

Sub-checks:
  - `CF-state-xdg` - persistent state uses XDG paths
  - `CF-tools-usage` - declared high-signal tools are actually referenced
  - `CF-side-effect` - side-effect skills set `disable-model-invocation: true`
  - `CF-mcp-format` - MCP tool references use double-underscore format

Usage:
    ./check-config.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes:
    0 - all emitted checks pass
    1 - one or more emitted checks fail
    2 - usage error
"""

from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import (
    CheckRecord,
    SkillDocument,
    compile_patterns,
    is_instructional_prose_line,
    iter_reference_inputs,
    matches_any,
    parse_allowed_tools,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

PERSISTENT_STATE_CHECK: Final[str] = "CF-state-xdg"
ALLOWED_TOOLS_CHECK: Final[str] = "CF-tools-usage"
SIDE_EFFECT_CHECK: Final[str] = "CF-side-effect"
MCP_FORMAT_CHECK: Final[str] = "CF-mcp-format"

CHECK_ORDER: Final[tuple[str, ...]] = (
    PERSISTENT_STATE_CHECK,
    ALLOWED_TOOLS_CHECK,
    SIDE_EFFECT_CHECK,
    MCP_FORMAT_CHECK,
)

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

BAD_STATE_PATH_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\./findings/",
        r"\$\{CLAUDE_SKILL_DIR\}/findings/",
    ),
)
STATE_REFERENCE_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    BAD_STATE_PATH_PATTERNS
    + compile_patterns(
        (
            r"\.last-run",
            r"\.covered-",
            r"state stored in",
            r"persistent.*state",
            r"state files",
        ),
    )
)
XDG_PATH_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"XDG_DATA_HOME",
        r"\$HOME/\.local/share",
    ),
)

TASK_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bagent\b",
        r"\bspawn\b",
        r"\bsubagent\b",
    ),
)
TOOLSEARCH_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"mcp__",
        r"select:",
    ),
)
ASK_USER_QUESTION_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bask\s+the\s+user\b",
        r"\bprompt\s+the\s+user\b",
        r"\bconfirm\s+with\s+(the\s+)?user\b",
        r"\blet\s+the\s+user\s+(choose|decide|pick|select|confirm)\b",
    ),
)
GLOB_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bglob\b",
        r"\bfind.*files?\b",
        r"\bfile.*search\b",
        r"\bpattern.*match\b",
    ),
)
GREP_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bgrep\b",
        r"\bsearch.*content\b",
        r"\bcontent.*search\b",
        r"\bfind.*text\b",
    ),
)
WRITE_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bwrite.*file\b",
        r"\bcreate.*file\b",
        r"\bsave\b.*\bfile\b",
        r"\bgenerate.*output\b",
    ),
)
EDIT_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bedit.*file\b",
        r"\bmodify.*file\b",
        r"\bupdate.*file\b",
        r"\brewrite\b",
    ),
)
WEBSEARCH_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bweb.*search\b",
        r"\bsearch.*web\b",
        r"\bsearch.*online\b",
    ),
)
WEBFETCH_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bfetch.*url\b",
        r"\bdownload\b",
        r"\bhttp[s]?://\b",
        r"\bURL\b",
    ),
)
# spawn/subagent overlap with TASK_IMPLIED_PATTERNS is intentional -
# both Task and Agent tools relate to subagent workflows.
AGENT_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bspawn\b",
        r"\bsubagent\b",
        r"\bbackground.*agent\b",
    ),
)
HIGH_SIGNAL_TOOL_RULES: Final[dict[str, tuple[Pattern[str], ...]]] = {
    "Task": TASK_IMPLIED_PATTERNS,
    "ToolSearch": TOOLSEARCH_IMPLIED_PATTERNS,
    "AskUserQuestion": ASK_USER_QUESTION_IMPLIED_PATTERNS,
    "Glob": GLOB_IMPLIED_PATTERNS,
    "Grep": GREP_IMPLIED_PATTERNS,
    "Write": WRITE_IMPLIED_PATTERNS,
    "Edit": EDIT_IMPLIED_PATTERNS,
    "WebSearch": WEBSEARCH_IMPLIED_PATTERNS,
    "WebFetch": WEBFETCH_IMPLIED_PATTERNS,
    "Agent": AGENT_IMPLIED_PATTERNS,
}

TOOL_SIDE_EFFECTS: Final[frozenset[str]] = frozenset({"Write", "Edit"})

API_SIDE_EFFECT_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bmcp__\w+",
        r"\bNotion\b.*\b(create|update|write|post)\b",
        r"\bSlack\b.*\b(send|post|message)\b",
        r"\bGitHub\b.*\b(create|comment|review|merge|push)\b",
        r"\bpbcopy\b",
        r"\bxclip\b",
        r"\bclipboard\b",
        r"\bgh\s+pr\s+(create|comment|review|merge)\b",
        r"\bgh\s+issue\s+(create|comment|close)\b",
    ),
)

SIDE_EFFECT_PATTERN: Final[Pattern[str]] = re.compile(
    r"k3d\s+(cluster|create|delete)"
    r"|kind\s+(create|delete)\s+cluster"
    r"|git\s+reset"
    r"|git\s+branch\s+-[dD]"
    r"|git\s+apply\s+--cached"
    r"|git\s+clean\s+-"
    r"|git\s+push\s+--force(?!-with-lease)"
    r"|kubectl\s+(delete|drain|cordon)"
    r"|helm\s+(uninstall|delete)"
    r"|rm\s+-rf"
    r"|docker\s+(rm|rmi|system\s+prune)"
    r"|git\s+push\s+--delete"
    r"|terraform\s+(destroy|apply\s+.*--destroy)"
    r"|pulumi\s+destroy",
    re.IGNORECASE,
)

INLINE_CODE_RE: Final[Pattern[str]] = re.compile(r"`[^`]*`")

MCP_PRESENCE_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"\bMCP\b",
        r"\bmcp__\w+",
        r"\bmcp_\w+",
    ),
)
MCP_SINGLE_UNDERSCORE_RE: Final[Pattern[str]] = re.compile(r"\bmcp_(?!_)\w+")


# ---------------------------------------------------------------------------
# Tool reference helpers
# ---------------------------------------------------------------------------


def _get_tool_reference_pattern(tool_name: str) -> Pattern[str]:
    """Compile and cache the regex pattern for a specific tool."""
    return re.compile(rf"(?<![\w-]){re.escape(tool_name)}(?![\w-])")


def _has_direct_tool_reference(tool_name: str, body_text: str) -> bool:
    """Return whether the body explicitly mentions a tool by name."""
    pattern = _get_tool_reference_pattern(tool_name)
    return pattern.search(body_text) is not None


def _tool_is_referenced(tool_name: str, body_text: str) -> bool:
    """Return whether a high-signal tool is used or strongly implied."""
    if _has_direct_tool_reference(tool_name, body_text):
        return True

    implied_patterns = HIGH_SIGNAL_TOOL_RULES.get(tool_name)
    if implied_patterns is None:
        return False
    return matches_any(body_text, implied_patterns)


def _declared_tool_names(document: SkillDocument) -> frozenset[str]:
    """Return allowed-tools names without parameter suffixes."""
    return frozenset(
        tool_name.split("(")[0]
        for tool_name in parse_allowed_tools(document.frontmatter)
    )


def _matching_lines(
    body_text: str,
    patterns: tuple[Pattern[str], ...],
) -> tuple[str, ...]:
    """Return body lines that match any of the supplied patterns."""
    hits: list[str] = []
    for raw_line in body_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if matches_any(line, patterns):
            hits.append(line)
    return tuple(hits)


def _iter_reference_actionable_lines(document: SkillDocument) -> tuple[str, ...]:
    """Return actionable prose lines from referenced text files.

    Filters out headings, tables, blockquotes, and pedagogical sections to avoid
    false positives from checklist or examples-only content.
    """
    hits: list[str] = []
    for ref in iter_reference_inputs(document):
        for index, line in enumerate(ref.lines):
            if index in ref.skip_indices:
                continue
            if not is_instructional_prose_line(line):
                continue
            sanitized = INLINE_CODE_RE.sub("", line).strip()
            if not sanitized:
                continue
            hits.append(f"{ref.rel_path}: {sanitized}")

    return tuple(hits)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_persistent_state_xdg(document: SkillDocument) -> CheckRecord | None:
    """Validate that persistent state uses XDG-compliant paths."""
    body_text = document.prose_body
    if not matches_any(body_text, STATE_REFERENCE_PATTERNS):
        return None

    has_bad_path = matches_any(body_text, BAD_STATE_PATH_PATTERNS)
    has_xdg_path = matches_any(body_text, XDG_PATH_PATTERNS)

    if has_bad_path:
        return CheckRecord(
            check=PERSISTENT_STATE_CHECK,
            passed=False,
            detail=(
                "Skill uses relative paths (./findings/ or "
                "${CLAUDE_SKILL_DIR}/findings/) for persistent state - use "
                "${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin}/ instead"
            ),
            tier="I11",
        )

    if has_xdg_path:
        return CheckRecord(
            check=PERSISTENT_STATE_CHECK,
            passed=True,
            detail="Persistent state uses XDG-compliant path",
            tier="I11",
        )

    return CheckRecord(
        check=PERSISTENT_STATE_CHECK,
        passed=True,
        detail="State references found; no bad path patterns detected",
        tier="I11",
    )


def check_allowed_tools_usage(document: SkillDocument) -> CheckRecord | None:
    """Validate that declared high-signal tools are actually referenced."""
    if not document.field("allowed-tools"):
        return None

    declared_tools = _declared_tool_names(document)
    unused_tools = sorted(
        tool_name
        for tool_name in declared_tools
        if tool_name in HIGH_SIGNAL_TOOL_RULES
        and not _tool_is_referenced(tool_name, document.prose_body)
    )

    if not unused_tools:
        return CheckRecord(
            check=ALLOWED_TOOLS_CHECK,
            passed=True,
            detail="No unused purpose-specific tools detected in allowed-tools",
            tier="I16",
        )

    return CheckRecord(
        check=ALLOWED_TOOLS_CHECK,
        passed=False,
        detail=(
            "Allowed-tools lists unused tool(s): "
            f"{', '.join(unused_tools)} - remove to minimize granted permissions"
        ),
        tier="I16",
    )


def _first_line_snippet(line: str, width: int = 80) -> str:
    """Return one trimmed line excerpt for check detail output."""
    return line.strip()[:width]


def check_side_effect_guard(document: SkillDocument) -> CheckRecord:
    """Validate that side-effect skills set `disable-model-invocation: true`."""
    declared_tools = _declared_tool_names(document)
    tool_hits = sorted(TOOL_SIDE_EFFECTS & declared_tools)
    api_hits = _matching_lines(document.prose_body, API_SIDE_EFFECT_PATTERNS)
    command_hits = _matching_lines(document.prose_body, (SIDE_EFFECT_PATTERN,))
    ref_lines = _iter_reference_actionable_lines(document)
    ref_api_hits = tuple(
        line for line in ref_lines if matches_any(line, API_SIDE_EFFECT_PATTERNS)
    )
    ref_command_hits = tuple(
        line for line in ref_lines if matches_any(line, (SIDE_EFFECT_PATTERN,))
    )
    side_effect_hits = (
        len(tool_hits)
        + len(api_hits)
        + len(command_hits)
        + len(ref_api_hits)
        + len(ref_command_hits)
    )

    if side_effect_hits == 0:
        return CheckRecord(
            check=SIDE_EFFECT_CHECK,
            passed=True,
            detail="No side-effect patterns detected",
            tier="I17",
        )

    evidence_parts: list[str] = []
    if tool_hits:
        evidence_parts.append(f"tools={','.join(tool_hits)}")
    if api_hits:
        evidence_parts.append(f"api={_first_line_snippet(api_hits[0])}")
    if command_hits:
        evidence_parts.append(f"cmd={_first_line_snippet(command_hits[0])}")
    if ref_api_hits:
        evidence_parts.append(f"ref-api={_first_line_snippet(ref_api_hits[0])}")
    if ref_command_hits:
        evidence_parts.append(f"ref-cmd={_first_line_snippet(ref_command_hits[0])}")
    evidence = "; ".join(evidence_parts)

    if document.field("disable-model-invocation").lower() == "true":
        return CheckRecord(
            check=SIDE_EFFECT_CHECK,
            passed=True,
            detail=(
                "Side-effect signals detected and disable-model-invocation: true "
                f"is set ({evidence})"
            ),
            tier="I17",
        )

    return CheckRecord(
        check=SIDE_EFFECT_CHECK,
        passed=False,
        detail=(
            "Side-effect signals detected but disable-model-invocation: true is "
            f"missing ({evidence})"
        ),
        tier="I17",
    )


def check_mcp_format(document: SkillDocument) -> CheckRecord | None:
    """Validate that MCP tool references use double-underscore format."""
    combined_text = document.prose_body
    for ref in iter_reference_inputs(document):
        combined_text += "\n" + "\n".join(ref.lines)

    if not matches_any(combined_text, MCP_PRESENCE_PATTERNS):
        return None

    typo_match = MCP_SINGLE_UNDERSCORE_RE.search(combined_text)
    if typo_match:
        return CheckRecord.info(
            MCP_FORMAT_CHECK,
            (
                f"Single-underscore MCP reference detected: {typo_match.group(0)} "
                "- use double-underscore format (mcp__server__tool)"
            ),
            tier="P19",
        )

    return CheckRecord.ok(
        MCP_FORMAT_CHECK,
        "MCP tool references use correct double-underscore format",
        tier="P19",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[dict[str, Callable[[SkillDocument], CheckRecord | None]]] = {
    PERSISTENT_STATE_CHECK: check_persistent_state_xdg,
    ALLOWED_TOOLS_CHECK: check_allowed_tools_usage,
    SIDE_EFFECT_CHECK: check_side_effect_guard,
    MCP_FORMAT_CHECK: check_mcp_format,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    """Run all config checks and return emitted results in order."""
    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []
    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        result = CHECK_FUNCTIONS[check_name](document)
        if result is not None:
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    return run_check_cli(
        "Validate skill configuration and tool-usage checks.",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
