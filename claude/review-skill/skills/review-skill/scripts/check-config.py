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
import functools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Any, Final

from skill_check_common import SkillDocument, SkillLoadError, load_skill_document

EXIT_OK: Final[int] = 0
EXIT_FAILURE: Final[int] = 1
EXIT_USAGE_ERROR: Final[int] = 2

PERSISTENT_STATE_CHECK: Final[str] = "persistent-state-xdg"
ALLOWED_TOOLS_CHECK: Final[str] = "allowed-tools-usage"
SIDE_EFFECT_CHECK: Final[str] = "side-effect-guard"

BAD_STATE_PATH_PATTERNS: Final[tuple[Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\./findings/",
        r"\$SKILL_DIR/findings/",
        r"\$\{CLAUDE_SKILL_DIR\}/findings/",
    )
)
STATE_REFERENCE_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    BAD_STATE_PATH_PATTERNS
    + tuple(
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"\.last-run",
            r"\.covered-",
            r"state stored in",
            r"persistent.*state",
            r"state files",
        )
    )
)
XDG_PATH_PATTERNS: Final[tuple[Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"XDG_DATA_HOME",
        r"\$HOME/\.local/share",
    )
)

TASK_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bagent\b",
        r"\bspawn\b",
        r"\bsubagent\b",
    )
)
TOOLSEARCH_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"mcp__",
        r"select:",
    )
)
ASK_USER_QUESTION_IMPLIED_PATTERNS: Final[tuple[Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bask\s+the\s+user\b",
        r"\bprompt\s+the\s+user\b",
        r"\bconfirm\s+with\s+(the\s+)?user\b",
        r"\blet\s+the\s+user\s+(choose|decide|pick|select|confirm)\b",
    )
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
    r"|git\s+push\s+--force"
    r"|kubectl\s+(delete|drain|cordon)"
    r"|helm\s+(uninstall|delete)"
    r"|rm\s+-rf",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CheckResult:
    """Store the result of one validation check."""

    check: str
    passed: bool
    detail: str

    def payload(self) -> dict[str, Any]:
        """Serialize the result into the NDJSON output format."""
        return {
            "check": self.check,
            "pass": self.passed,
            "detail": self.detail,
        }


def _emit_json_line(payload: Any) -> None:
    """Write one JSON object to stdout as a single line."""
    print(json.dumps(payload, ensure_ascii=False), file=sys.stdout)


def _emit_error(message: str) -> None:
    """Write one error line to stderr."""
    print(message, file=sys.stderr)


def _matches_any(text: str, patterns: tuple[Pattern[str], ...]) -> bool:
    """Return whether any compiled pattern matches the text."""
    return any(pattern.search(text) for pattern in patterns)


def _parse_declared_tools(raw_tools: str) -> tuple[str, ...]:
    """Parse a comma-separated `allowed-tools` field in stable order."""
    ordered_unique_tools = dict.fromkeys(
        tool.strip() for tool in raw_tools.split(",") if tool.strip()
    )
    return tuple(ordered_unique_tools)


@functools.lru_cache(maxsize=32)
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
    return _matches_any(body_text, implied_patterns)


def check_persistent_state_xdg(document: SkillDocument) -> CheckResult | None:
    """Validate that persistent state uses XDG-compliant paths."""
    body_text = document.prose_body
    if not _matches_any(body_text, STATE_REFERENCE_PATTERNS):
        return None

    if _matches_any(body_text, XDG_PATH_PATTERNS):
        return CheckResult(
            check=PERSISTENT_STATE_CHECK,
            passed=True,
            detail="Persistent state uses XDG-compliant path",
        )

    if _matches_any(body_text, BAD_STATE_PATH_PATTERNS):
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
        detail="State references found but no relative path issues detected",
    )


def check_allowed_tools_usage(document: SkillDocument) -> CheckResult | None:
    """Validate that declared high-signal tools are actually referenced."""
    raw_allowed_tools = document.field("allowed-tools")
    if not raw_allowed_tools:
        return None

    declared_tools = _parse_declared_tools(raw_allowed_tools)
    unused_tools = [
        tool_name
        for tool_name in declared_tools
        if tool_name in HIGH_SIGNAL_TOOL_RULES
        and not _tool_is_referenced(tool_name, document.body)
    ]

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
    side_effect_hits = _count_side_effect_hits(document.body)
    if side_effect_hits == 0:
        return CheckResult(
            check=SIDE_EFFECT_CHECK,
            passed=True,
            detail="No side-effect patterns detected",
        )

    if str(document.field("disable-model-invocation")).lower() == "true":
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


def run_checks(document: SkillDocument) -> list[CheckResult]:
    """Run all config checks and return emitted results in order."""
    results: list[CheckResult] = []

    persistent_state_result = check_persistent_state_xdg(document)
    if persistent_state_result is not None:
        results.append(persistent_state_result)

    allowed_tools_result = check_allowed_tools_usage(document)
    if allowed_tools_result is not None:
        results.append(allowed_tools_result)

    results.append(check_side_effect_guard(document))
    return results


def emit_results(results: list[CheckResult]) -> int:
    """Emit check results and return the process exit code."""
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    for result in results:
        _emit_json_line(result.payload())

    _emit_json_line(
        {
            "summary": True,
            "total": len(results),
            "passed": passed,
            "failed": failed,
        },
    )

    if failed > 0:
        return EXIT_FAILURE
    return EXIT_OK


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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entry point and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        document = load_skill_document(args.skill_directory)
    except SkillLoadError as error:
        _emit_error(f"Error: {error}")
        return EXIT_USAGE_ERROR

    return emit_results(run_checks(document))


if __name__ == "__main__":
    raise SystemExit(main())
