#!/usr/bin/env python3
"""Validate `!` preprocessing directives in SKILL.md and referenced prose.

Sub-checks:
  - `PP-syntax`        - malformed directive markers
  - `PP-err-handling`  - error handling or safe commands
  - `PP-output-limit`  - bounded output or limiting
  - `PP-secret-leak`   - no secret leakage patterns
  - `PP-mutation`      - no state-changing at load time
  - `PP-slow-cmd`      - no slow commands blocking loading
  - `PP-redundant-dir` - no redundant CLAUDE_SKILL_DIR echo
  - `PP-interactive`   - no interactive/hanging commands

Output format is NDJSON, ending with a summary line that includes
`directives` count for compatibility with orchestration guards.

Exit codes:
- 0 when all emitted checks pass (or no directives found)
- 1 when one or more checks fail
- 2 for CLI usage/input errors
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
    is_instructional_prose_line,
    iter_reference_inputs,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# Sub-check identifiers
# ---------------------------------------------------------------------------

CHECK_SYNTAX: Final[str] = "PP-syntax"
CHECK_ERR: Final[str] = "PP-err-handling"
CHECK_OUT: Final[str] = "PP-output-limit"
CHECK_SEC: Final[str] = "PP-secret-leak"
CHECK_MUT: Final[str] = "PP-mutation"
CHECK_SLOW: Final[str] = "PP-slow-cmd"
CHECK_DUP: Final[str] = "PP-redundant-dir"
CHECK_HANG: Final[str] = "PP-interactive"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_SYNTAX,
    CHECK_ERR,
    CHECK_OUT,
    CHECK_SEC,
    CHECK_MUT,
    CHECK_SLOW,
    CHECK_DUP,
    CHECK_HANG,
)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# NOTE: DIRECTIVE_RE does not handle nested backticks inside directives.
# A directive like !`echo "`date`"` would be split at the first closing
# backtick. This is acceptable for lint purposes since nested backticks
# in preprocessing directives are extremely rare and inherently fragile.
DIRECTIVE_RE: Final[Pattern[str]] = re.compile(r"!`[^`]+`")
UNCLOSED_DIRECTIVE_RE: Final[Pattern[str]] = re.compile(r"!`[^`]*$")
EMPTY_DIRECTIVE_RE: Final[Pattern[str]] = re.compile(r"!``")

ERROR_HANDLING_RE: Final[Pattern[str]] = re.compile(
    r"2>/dev/null|2>&1|\|\|\s+(echo|true|printf|:)",
)
CONDITIONAL_FALLBACK_RE: Final[Pattern[str]] = re.compile(r"&&.*\|\|")

OUTPUT_DISCARDED_RE: Final[Pattern[str]] = re.compile(
    r">/dev/null.*&&\s*(echo|printf)",
)
TEST_OUTPUT_RE: Final[Pattern[str]] = re.compile(r"&&\s*(echo|printf)")
GIT_LOG_LIMIT_RE: Final[Pattern[str]] = re.compile(r"-\d+|--oneline\s+-\d+")
GIT_DIFF_LIMIT_RE: Final[Pattern[str]] = re.compile(
    r"--stat|--name-only|--numstat|--shortstat",
)
GIT_STATUS_LIMIT_RE: Final[Pattern[str]] = re.compile(r"--short|-s")
VERSION_RE: Final[Pattern[str]] = re.compile(
    r"(node|python|python3|ruby|go|java|rustc|cargo|npm|yarn|pip)\s+--version",
)
PIPE_LIMIT_RE: Final[Pattern[str]] = re.compile(
    r"\|\s*(head|tail|grep|wc|awk|sed|cut|sort|uniq|jq)",
)
GH_PR_DIFF_RE: Final[Pattern[str]] = re.compile(r"pr\s+diff")
MIN_COMMAND_WORDS: Final[int] = 2  # minimum tokens needed to extract a second word

SECRET_ENV_RE: Final[Pattern[str]] = re.compile(
    r"\$(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE_KEY|AUTH_TOKEN|AWS_SECRET"
    r"|DB_PASS|MYSQL_PWD|PGPASSWORD|SMTP_PASS)"
    r"|\$\{[^}]*(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE_KEY|AUTH_TOKEN"
    r"|AWS_SECRET|DB_PASS|MYSQL_PWD|PGPASSWORD|SMTP_PASS)[^}]*\}",
    re.IGNORECASE,
)
SECRET_FILTER_RE: Final[Pattern[str]] = re.compile(
    r"grep -v.*(SECRET|KEY|PASSWORD|TOKEN)",
    re.IGNORECASE,
)
SENSITIVE_HOME_READ_RE: Final[Pattern[str]] = re.compile(
    r"(cat|head|tail|less|more)\s+(~|\$HOME|\$\{HOME\})/\.(ssh/|aws/credentials|gnupg/)",
)
DOTENV_READ_RE: Final[Pattern[str]] = re.compile(r"(cat|head|tail)\s+\.env\b")

GIT_MUTATION_RE: Final[Pattern[str]] = re.compile(
    r"\bgit\s+(commit|push|reset|checkout|clean|stash|rebase|merge|cherry-pick|"
    r"tag\s+|remote\s+(add|remove|rm)|branch\s+-[dD])",
)
RM_RE: Final[Pattern[str]] = re.compile(r"\b(rm|rmdir)\s+")
MV_RE: Final[Pattern[str]] = re.compile(r"\bmv\s+[^|]+\s+[^|]")
PIPE_RE: Final[Pattern[str]] = re.compile(r"\|")

MUTATION_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"\b(npm|yarn|pnpm)\s+(install|add|remove|uninstall|publish)\b"),
    re.compile(r"\b(pip|pip3)\s+(install|uninstall)\b"),
    re.compile(r"\bcargo\s+(install|publish)\b"),
    re.compile(r"\bapt-get\s+(install|remove|purge)\b"),
    re.compile(r"\bbrew\s+(install|uninstall|remove)\b"),
    re.compile(
        r"\bkubectl\s+(apply|create|delete|patch|replace|drain|cordon|taint|rollout)\b",
    ),
    re.compile(r"\bhelm\s+(install|upgrade|uninstall|delete|rollback)\b"),
    re.compile(r"\bdocker\s+(run|build|push|pull|rm|rmi|stop|kill|restart|create)\b"),
    re.compile(r"\b(k3d|kind)\s+(cluster|create|delete)\b"),
)

SLOW_PATTERNS: Final[tuple[Pattern[str], ...]] = (
    re.compile(r"\b(npm|yarn|pnpm)\s+(test|run\s+build|run\s+test|run\s+lint)\b"),
    re.compile(r"\bcargo\s+(build|test|check|clippy)\b"),
    re.compile(r"\bgo\s+(build|test|vet)\b"),
    re.compile(r"\b(pytest|python\s+-m\s+pytest|mvn|gradle|make\s+test)\b"),
    re.compile(r"\bdocker\s+(build|pull)\b"),
    re.compile(r"\bgit\s+(fetch|pull|clone|push)\b"),
    re.compile(r"\b(npm|yarn|pnpm)\s+install\b"),
    re.compile(r"\b(pip|pip3)\s+install\b"),
    re.compile(r"\bapt-get\s+(install|update|upgrade)\b"),
    re.compile(r"\bbrew\s+(install|update|upgrade)\b"),
)

REDUNDANT_SKILL_DIR_RE: Final[Pattern[str]] = re.compile(
    r"echo\s+\"?\$\{?CLAUDE_SKILL_DIR\}?",
)

SSH_RE: Final[Pattern[str]] = re.compile(r"\bssh\b")
SSH_NONINTERACTIVE_RE: Final[Pattern[str]] = re.compile(
    r"-o\s*BatchMode|StrictHostKeyChecking",
)
SUDO_RE: Final[Pattern[str]] = re.compile(r"\bsudo\b")
SUDO_NONINTERACTIVE_RE: Final[Pattern[str]] = re.compile(r"-n\b")
MYSQL_RE: Final[Pattern[str]] = re.compile(r"\bmysql\b")
MYSQL_NONINTERACTIVE_RE: Final[Pattern[str]] = re.compile(r"-e\b")
PSQL_RE: Final[Pattern[str]] = re.compile(r"\bpsql\b")
PSQL_NONINTERACTIVE_RE: Final[Pattern[str]] = re.compile(r"-c\b")

ERR_SAFE_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "echo",
        "date",
        "uname",
        "whoami",
        "pwd",
        "hostname",
        "id",
        "basename",
        "dirname",
        "printf",
        "true",
        "mkdir",
        "touch",
    },
)

OUT_SAFE_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "echo",
        "date",
        "uname",
        "whoami",
        "pwd",
        "hostname",
        "id",
        "basename",
        "dirname",
        "printf",
        "true",
        "command",
    },
)

GIT_BOUNDED_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {
        "branch",
        "rev-parse",
        "symbolic-ref",
        "remote",
        "for-each-ref",
        "describe",
        "config",
    },
)

OUT_LARGE_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "cat",
        "find",
        "ls",
        "grep",
        "curl",
        "wget",
        "docker",
        "kubectl",
        "helm",
        "npm",
        "yarn",
        "pip",
        "cargo",
        "make",
        "mysql",
        "psql",
    },
)

INTERACTIVE_COMMANDS: Final[frozenset[str]] = frozenset(
    {"vi", "vim", "nvim", "nano", "emacs", "less", "more", "pico"},
)

NON_ACTIONABLE_DIRECTIVE_LINE_RE: Final[Pattern[str]] = re.compile(
    r"\b(?:"
    r"PP-[a-z-]+|"
    r"check-preprocessing(?:\.py)?|"
    r"automated\s+by|"
    r"directive\s+syntax|"
    r"validates\s+each\s+directive"
    r")\b",
    re.IGNORECASE,
)
DIRECTIVE_LIST_ITEM_RE: Final[Pattern[str]] = re.compile(
    r"^\s*(?:[-*+]\s+|\d+\.\s+).*!`[^`]+`",
)


# ---------------------------------------------------------------------------
# Command-level helpers
# ---------------------------------------------------------------------------


def _strip_directive(directive: str) -> str:
    """Strip leading `!`` and trailing backtick from a directive."""
    return directive[2:-1]


def _primary_command(command: str) -> str:
    """Return the primary command token from a shell snippet."""
    stripped = command.lstrip()
    if not stripped:
        return ""
    if stripped.startswith("["):
        return "["
    return stripped.split(maxsplit=1)[0]


def _second_word(command: str) -> str:
    """Return the second shell token, or empty string when missing."""
    parts = command.split()
    if len(parts) < MIN_COMMAND_WORDS:
        return ""
    return parts[1]


# Git options that consume the next token as their argument.
_GIT_ARG_OPTIONS: Final[frozenset[str]] = frozenset({"-C", "-c"})


def _git_subcommand(command: str) -> str:
    """Return the git subcommand, skipping global options.

    Git global options like ``-C <path>`` and ``-c <key>=<value>`` take an
    argument (skip 2 tokens); other flags starting with ``-`` skip 1.
    """
    parts = command.split()
    if len(parts) < MIN_COMMAND_WORDS:
        return ""
    i = 1
    while i < len(parts):
        token = parts[i]
        if not token.startswith("-"):
            return token
        if token in _GIT_ARG_OPTIONS:
            i += 2  # skip flag + its argument
        else:
            i += 1  # skip single flag
    return ""


def _has_error_handling(command: str) -> bool:
    """Check whether directive has fallback/error handling behavior."""
    primary = _primary_command(command)
    if primary in ERR_SAFE_COMMANDS:
        return True
    if ERROR_HANDLING_RE.search(command):
        return True
    return CONDITIONAL_FALLBACK_RE.search(command) is not None


def _is_bounded_git_output(command: str) -> bool | None:
    """Return whether a git command produces bounded output.

    Returns True if the git subcommand is inherently bounded or uses
    explicit limiting flags, False if unbounded, or None if the command
    is not a git command (sentinel used by caller to fall through).
    """
    if _primary_command(command) != "git":
        return None

    subcommand = _git_subcommand(command)
    if subcommand in GIT_BOUNDED_SUBCOMMANDS:
        return True
    if subcommand == "log":
        return GIT_LOG_LIMIT_RE.search(command) is not None
    if subcommand == "diff":
        return GIT_DIFF_LIMIT_RE.search(command) is not None
    if subcommand == "status":
        return GIT_STATUS_LIMIT_RE.search(command) is not None
    return False


def _has_bounded_output(command: str) -> bool:
    """Check whether directive output is constrained."""
    primary = _primary_command(command)
    if primary in OUT_SAFE_COMMANDS:
        return True

    has_direct_limit = (
        OUTPUT_DISCARDED_RE.search(command) is not None
        or (primary == "[" and TEST_OUTPUT_RE.search(command) is not None)
        or VERSION_RE.search(command) is not None
        or PIPE_LIMIT_RE.search(command) is not None
    )
    if has_direct_limit:
        return True

    git_bounded = _is_bounded_git_output(command)
    if git_bounded is not None:
        return git_bounded

    if primary == "gh":
        return GH_PR_DIFF_RE.search(command) is None

    return primary not in OUT_LARGE_COMMANDS


def _is_secret_safe(command: str) -> bool:
    """Check whether directive avoids obvious secret leakage patterns."""
    if SECRET_ENV_RE.search(command):
        return SECRET_FILTER_RE.search(command) is not None
    if SENSITIVE_HOME_READ_RE.search(command):
        return False
    if DOTENV_READ_RE.search(command):
        return SECRET_FILTER_RE.search(command) is not None
    return True


def _is_non_mutating(command: str) -> bool:
    """Check whether directive avoids load-time state changes."""
    if GIT_MUTATION_RE.search(command):
        return False
    if RM_RE.search(command):
        return False
    if MV_RE.search(command) and not PIPE_RE.search(command):
        return False
    return not any(pattern.search(command) for pattern in MUTATION_PATTERNS)


def _is_fast_enough(command: str) -> bool:
    """Check whether directive avoids known slow commands."""
    return not any(pattern.search(command) for pattern in SLOW_PATTERNS)


def _has_no_redundant_skill_dir_echo(command: str) -> bool:
    """Check whether directive avoids redundant CLAUDE_SKILL_DIR echo wrapping."""
    return REDUNDANT_SKILL_DIR_RE.search(command) is None


def _is_non_interactive(command: str) -> bool:
    """Check whether directive avoids interactive/hanging behavior."""
    primary = _primary_command(command)
    if primary in INTERACTIVE_COMMANDS:
        return False
    if SSH_RE.search(command) and not SSH_NONINTERACTIVE_RE.search(command):
        return False
    if SUDO_RE.search(command) and not SUDO_NONINTERACTIVE_RE.search(command):
        return False
    if MYSQL_RE.search(command) and not MYSQL_NONINTERACTIVE_RE.search(command):
        return False
    if PSQL_RE.search(command) and not PSQL_NONINTERACTIVE_RE.search(command):
        return False
    return primary not in {"read", "ftp"}


# ---------------------------------------------------------------------------
# Directive extraction
# ---------------------------------------------------------------------------


def _extract_directive_commands(prose_body: str) -> tuple[str, ...]:
    """Extract `!` preprocessing directive command strings from prose."""
    return tuple(_strip_directive(match) for match in DIRECTIVE_RE.findall(prose_body))


def _is_actionable_directive_line(line: str) -> bool:
    """Return whether a line with directives is actionable guidance."""
    if NON_ACTIONABLE_DIRECTIVE_LINE_RE.search(line):
        return False
    if DIRECTIVE_LIST_ITEM_RE.search(line):
        return True
    return is_instructional_prose_line(line)


def _scan_reference_directives(
    document: SkillDocument,
) -> tuple[tuple[str, ...], list[CheckRecord]]:
    """Extract directive commands and syntax errors from references."""
    commands: list[str] = []
    syntax_results: list[CheckRecord] = []
    first_unclosed = ""
    empty_count = 0

    for ref in iter_reference_inputs(document):
        for index, line in enumerate(ref.lines):
            if index in ref.skip_indices:
                continue
            if DIRECTIVE_RE.search(line) is None:
                continue
            if not _is_actionable_directive_line(line):
                continue

            commands.extend(
                _strip_directive(match) for match in DIRECTIVE_RE.findall(line)
            )

            if UNCLOSED_DIRECTIVE_RE.search(line) and not first_unclosed:
                first_unclosed = f"{ref.rel_path}:L{index + 1}"

            empty_count += len(EMPTY_DIRECTIVE_RE.findall(line))

    if first_unclosed:
        syntax_results.append(
            CheckRecord(
                check=CHECK_SYNTAX,
                passed=False,
                detail=(
                    "Unclosed preprocessing directive in referenced file "
                    f"at {first_unclosed} - missing closing backtick"
                ),
                tier="I18",
            ),
        )

    if empty_count > 0:
        syntax_results.append(
            CheckRecord(
                check=CHECK_SYNTAX,
                passed=False,
                detail=(
                    f"Found {empty_count} empty preprocessing directive(s) "
                    "in referenced files - !`` contains no command"
                ),
                tier="I18",
            ),
        )

    return tuple(commands), syntax_results


# ---------------------------------------------------------------------------
# Syntax check (returns 0-2 results)
# ---------------------------------------------------------------------------


def _check_syntax(prose_body: str) -> list[CheckRecord]:
    """Run syntax checks for malformed directive markers."""
    results: list[CheckRecord] = []

    unclosed_lines = [
        index
        for index, line in enumerate(prose_body.splitlines(), start=1)
        if UNCLOSED_DIRECTIVE_RE.search(line)
    ]
    if unclosed_lines:
        results.append(
            CheckRecord(
                check=CHECK_SYNTAX,
                passed=False,
                detail=(
                    "Unclosed preprocessing directive near body line "
                    f"{unclosed_lines[0]} - missing closing backtick"
                ),
                tier="I18",
            ),
        )

    empty_count = len(EMPTY_DIRECTIVE_RE.findall(prose_body))
    if empty_count > 0:
        results.append(
            CheckRecord(
                check=CHECK_SYNTAX,
                passed=False,
                detail=(
                    f"Found {empty_count} empty preprocessing directive(s) - "
                    "!`` contains no command"
                ),
                tier="I18",
            ),
        )

    return results


# ---------------------------------------------------------------------------
# Category checks (each takes commands tuple, returns CheckRecord)
# ---------------------------------------------------------------------------


def _check_err_handling(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for error handling."""
    failures = [cmd for cmd in commands if not _has_error_handling(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_ERR,
            passed=True,
            detail=(
                "All preprocessing directives have error handling or use safe commands"
            ),
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_ERR,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) lack error handling "
            f"(2>/dev/null, || echo fallback) - first: {failures[0]}"
        ),
        tier="I18",
    )


def _check_output_limit(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for bounded output."""
    failures = [cmd for cmd in commands if not _has_bounded_output(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_OUT,
            passed=True,
            detail=(
                "All preprocessing directives produce bounded output or use limiting"
            ),
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_OUT,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) could produce large output without limiting "
            f"(| head, | tail) - first: {failures[0]}"
        ),
        tier="I18",
    )


def _check_secret_leak(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for secret leakage."""
    failures = [cmd for cmd in commands if not _is_secret_safe(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_SEC,
            passed=True,
            detail="No secret-leaking patterns detected in preprocessing directives",
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_SEC,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) may leak secrets via env var expansion "
            f"- first: {failures[0]}"
        ),
        tier="I18",
    )


def _check_mutation(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for state-changing commands."""
    failures = [cmd for cmd in commands if not _is_non_mutating(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_MUT,
            passed=True,
            detail="No state-changing commands in preprocessing directives",
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_MUT,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) contain state-changing commands "
            f"that run at load time - first: {failures[0]}"
        ),
        tier="I18",
    )


def _check_slow_cmd(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for slow commands."""
    failures = [cmd for cmd in commands if not _is_fast_enough(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_SLOW,
            passed=True,
            detail="No slow commands detected in preprocessing directives",
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_SLOW,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) contain slow commands"
            " that block skill loading "
            f"- first: {failures[0]}"
        ),
        tier="I18",
    )


def _check_redundant_skilldir(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for redundant CLAUDE_SKILL_DIR echo."""
    failures = [cmd for cmd in commands if not _has_no_redundant_skill_dir_echo(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_DUP,
            passed=True,
            detail="No redundant CLAUDE_SKILL_DIR wrapping in preprocessing directives",
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_DUP,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) wrap CLAUDE_SKILL_DIR in echo - redundant, "
            "already a load-time substitution"
        ),
        tier="I18",
    )


def _check_interactive(commands: tuple[str, ...]) -> CheckRecord:
    """Check all directives for interactive/hanging commands."""
    failures = [cmd for cmd in commands if not _is_non_interactive(cmd)]
    if not failures:
        return CheckRecord(
            check=CHECK_HANG,
            passed=True,
            detail="No interactive/hanging commands in preprocessing directives",
            tier="I18",
        )
    return CheckRecord(
        check=CHECK_HANG,
        passed=False,
        detail=(
            f"{len(failures)} directive(s) may hang waiting for input "
            f"- first: {failures[0]}"
        ),
        tier="I18",
    )


CHECK_FUNCTIONS: Final[dict[str, Callable[[tuple[str, ...]], CheckRecord]]] = {
    CHECK_ERR: _check_err_handling,
    CHECK_OUT: _check_output_limit,
    CHECK_SEC: _check_secret_leak,
    CHECK_MUT: _check_mutation,
    CHECK_SLOW: _check_slow_cmd,
    CHECK_DUP: _check_redundant_skilldir,
    CHECK_HANG: _check_interactive,
}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> tuple[list[CheckRecord], dict[str, object]]:
    """Run preprocessing checks, return results and extra summary."""
    prose_body = document.prose_body
    ref_commands, ref_syntax_results = _scan_reference_directives(document)
    directive_commands = _extract_directive_commands(prose_body) + ref_commands
    directive_count = len(directive_commands)

    if not directive_commands:
        return [], {"directives": directive_count}

    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []

    if not selected or CHECK_SYNTAX in selected:
        results.extend(_check_syntax(prose_body))
        results.extend(ref_syntax_results)

    for check_name in CHECK_ORDER:
        if check_name == CHECK_SYNTAX:
            continue
        if selected and check_name not in selected:
            continue
        results.append(CHECK_FUNCTIONS[check_name](directive_commands))

    return results, {"directives": directive_count}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and return process exit code."""
    return run_check_cli(
        "Validate preprocessing directives in a skill SKILL.md",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
