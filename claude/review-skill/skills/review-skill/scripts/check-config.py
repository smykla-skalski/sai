#!/usr/bin/env python3
"""Validate configuration and tool-usage checks for a skill.

Sub-checks:
  - `persistent-state-xdg` - persistent state uses XDG paths
  - `allowed-tools-usage` - declared high-signal tools are actually referenced
  - `side-effect-guard` - side-effect skills set `disable-model-invocation: true`

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

import argparse
import re
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckResult,
    SkillDocument,
    SkillLoadError,
    compile_patterns,
    emit_error,
    emit_results,
    load_skill_document,
    matches_any,
    parse_allowed_tools,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

PERSISTENT_STATE_CHECK: Final[str] = "persistent-state-xdg"
ALLOWED_TOOLS_CHECK: Final[str] = "allowed-tools-usage"
SIDE_EFFECT_CHECK: Final[str] = "side-effect-guard"

CHECK_ORDER: Final[tuple[str, ...]] = (
    PERSISTENT_STATE_CHECK,
    ALLOWED_TOOLS_CHECK,
    SIDE_EFFECT_CHECK,
)

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

BAD_STATE_PATH_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
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
XDG_PATH_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"XDG_DATA_HOME",
        r"\$HOME/\.local/share",
    ),
)

TASK_IMPLIED_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bagent\b",
        r"\bspawn\b",
        r"\bsubagent\b",
    ),
)
TOOLSEARCH_IMPLIED_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"mcp__",
        r"select:",
    ),
)
ASK_USER_QUESTION_IMPLIED_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bask\s+the\s+user\b",
        r"\bprompt\s+the\s+user\b",
        r"\bconfirm\s+with\s+(the\s+)?user\b",
        r"\blet\s+the\s+user\s+(choose|decide|pick|select|confirm)\b",
    ),
)
HIGH_SIGNAL_TOOL_RULES: Final[dict[str, tuple[Pattern[str], ...]]] = {
    "Task": TASK_IMPLIED_PATTERNS,
    "ToolSearch": TOOLSEARCH_IMPLIED_PATTERNS,
    "AskUserQuestion": ASK_USER_QUESTION_IMPLIED_PATTERNS,
}

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


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_persistent_state_xdg(document: SkillDocument) -> CheckResult | None:
    """Validate that persistent state uses XDG-compliant paths."""
    body_text = document.prose_body
    if not matches_any(body_text, STATE_REFERENCE_PATTERNS):
        return None

    if matches_any(body_text, XDG_PATH_PATTERNS):
        return CheckResult(
            check=PERSISTENT_STATE_CHECK,
            passed=True,
            detail="Persistent state uses XDG-compliant path",
        )

    if matches_any(body_text, BAD_STATE_PATH_PATTERNS):
        return CheckResult(
            check=PERSISTENT_STATE_CHECK,
            passed=False,
            detail=(
                "Skill uses relative paths (./findings/ or "
                "${CLAUDE_SKILL_DIR}/findings/) for persistent state - use "
                "${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin}/ instead"
            ),
        )

    return CheckResult(
        check=PERSISTENT_STATE_CHECK,
        passed=True,
        detail="State references found; no bad path patterns detected",
    )


def check_allowed_tools_usage(document: SkillDocument) -> CheckResult | None:
    """Validate that declared high-signal tools are actually referenced."""
    if not document.field("allowed-tools"):
        return None

    declared_tools = parse_allowed_tools(document.frontmatter)
    unused_tools = sorted(
        bare_name
        for tool_name in declared_tools
        for bare_name in (tool_name.split("(")[0],)
        if bare_name in HIGH_SIGNAL_TOOL_RULES
        and not _tool_is_referenced(bare_name, document.prose_body)
    )

    if not unused_tools:
        return CheckResult(
            check=ALLOWED_TOOLS_CHECK,
            passed=True,
            detail="No unused high-signal tools detected in allowed-tools",
        )

    return CheckResult(
        check=ALLOWED_TOOLS_CHECK,
        passed=False,
        detail=(
            "allowed-tools lists unused tool(s): "
            f"{', '.join(unused_tools)} - remove to minimize granted permissions"
        ),
    )


def _count_side_effect_hits(body_text: str) -> int:
    """Count body lines that contain destructive or infrastructure commands."""
    return sum(
        1
        for line in body_text.splitlines()
        if SIDE_EFFECT_PATTERN.search(line) is not None
    )


def check_side_effect_guard(document: SkillDocument) -> CheckResult:
    """Validate that side-effect skills set `disable-model-invocation: true`."""
    side_effect_hits = _count_side_effect_hits(document.prose_body)
    if side_effect_hits == 0:
        return CheckResult(
            check=SIDE_EFFECT_CHECK,
            passed=True,
            detail="No side-effect patterns detected",
        )

    if document.field("disable-model-invocation").lower() == "true":
        return CheckResult(
            check=SIDE_EFFECT_CHECK,
            passed=True,
            detail="Side-effect skill has disable-model-invocation: true",
        )

    return CheckResult(
        check=SIDE_EFFECT_CHECK,
        passed=False,
        detail=(
            f"Skill contains {side_effect_hits} side-effect pattern(s) "
            "(destructive/infrastructure commands) but lacks "
            "disable-model-invocation: true"
        ),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECK_FUNCTIONS: Final[
    dict[str, Callable[[SkillDocument], CheckResult | None]]
] = {
    PERSISTENT_STATE_CHECK: check_persistent_state_xdg,
    ALLOWED_TOOLS_CHECK: check_allowed_tools_usage,
    SIDE_EFFECT_CHECK: check_side_effect_guard,
}


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckResult]:
    """Run all config checks and return emitted results in order."""
    selected = frozenset(selected_checks)
    results: list[CheckResult] = []
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


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate skill configuration and tool-usage checks.",
    )
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=CHECK_ORDER,
        dest="checks",
        help="Run only the specified check (repeatable)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
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
