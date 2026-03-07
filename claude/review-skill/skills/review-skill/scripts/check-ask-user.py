#!/usr/bin/env python3
"""Validate AskUserQuestion usage in SKILL.md files.

Checks declaration and usage consistency, implicit interaction patterns,
required-argument fallbacks, spawned-agent misuse, option structure,
destructive confirmation, ambiguity resolution, multiSelect grouping,
and wizard loop termination.

Usage:
    ./check-ask-user.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes:
    0 - all checks pass
    1 - one or more checks fail
    2 - usage error (bad arguments, missing files)
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

from _skill_check_common import (
    EXIT_USAGE_ERROR,
    CheckResult,
    ProseLine,
    SkillArgument,
    SkillLoadError,
    compile_patterns,
    emit_error,
    emit_results,
    extract_prose_lines,
    find_agent_indices,
    find_bundled_indices,
    format_hit,
    matches_any,
    parse_allowed_tools,
    parse_arguments,
    parse_frontmatter_lines,
    split_frontmatter,
)

# ---------------------------------------------------------------------------
# AskUserQuestion-specific constants
# ---------------------------------------------------------------------------

TOOL_NAME: Final[str] = "AskUserQuestion"

CHECK_DECLARATION: Final[str] = "auq-declaration-match"
CHECK_IMPLICIT: Final[str] = "auq-implicit-interaction"
CHECK_REQUIRED_ARG: Final[str] = "auq-required-arg-fallback"
CHECK_SPAWNED: Final[str] = "auq-spawned-agent"
CHECK_OPTION: Final[str] = "auq-option-structure"
CHECK_DESTRUCTIVE: Final[str] = "auq-destructive-no-confirm"
CHECK_AMBIGUITY: Final[str] = "auq-ambiguity-unresolved"
CHECK_MULTISELECT: Final[str] = "auq-multiselect-grouping"
CHECK_WIZARD: Final[str] = "auq-wizard-loop"

MEDIUM_SIGNAL_THRESHOLD: Final[int] = 2
AMBIGUITY_PREVIEW_WIDTH: Final[int] = 60
SUMMARY_HIT_LIMIT: Final[int] = 5
DETAIL_LIMIT: Final[int] = 3
REQUIRED_ARG_SEARCH_WINDOW: Final[int] = 2
OPTION_SCAN_START: Final[int] = -2
OPTION_SCAN_STOP: Final[int] = 11
AMBIGUITY_SCAN_START: Final[int] = -2
AMBIGUITY_SCAN_STOP: Final[int] = 6
CONFIRMATION_SCAN_START: Final[int] = -3
CONFIRMATION_SCAN_STOP: Final[int] = 4
DESCRIPTIVE_BULLET_THRESHOLD: Final[int] = 2

REQUIRED_DEFAULT_MARKERS: Final[frozenset[str]] = frozenset(
    {"", "-"},
)

# ---------------------------------------------------------------------------
# AskUserQuestion detection patterns
# ---------------------------------------------------------------------------

STRONG_INTERACTION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bask\s+the\s+user\b",
        r"\bask\s+user\b",
        r"\bprompt\s+the\s+user\b",
        r"\bprompt\s+user\b",
        r"\bprompt\s+interactively\b",
        r"\buse\s+AskUserQuestion\b",
        r"\bvia\s+AskUserQuestion\b",
        r"\bwith\s+AskUserQuestion\b",
    ),
)

MEDIUM_INTERACTION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\blet\s+the\s+user\s+(choose|decide|pick|select|confirm)\b",
        r"\bget\s+(user\s+|the\s+user's\s+|explicit\s+)?"
        r"(input|approval|confirmation|consent|decision)\b",
        r"\bconfirm\s+with\s+(the\s+)?user\b",
        r"\buser\s+(selects|decides|chooses|picks|approves|confirms)\b",
        r"\bpresent\s+.{0,40}\s+"
        r"(to\s+the\s+user|via.*question|as\s+options)\b",
        r"\boffer\s+.{0,30}\s+options\b",
    ),
)

NEGATION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bdo\s+NOT\s+ask\b",
        r"\bdon't\s+ask\b",
        r"\bwithout\s+asking\b",
        r"\bdo\s+not\s+ask\b",
        r"\bnever\s+ask\b",
        r"\bshould\s+NOT\b.*\bask\b",
    ),
)

AUQ_NON_WORKFLOW_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bcheck-ask-user(?:-[\w.-]+)?\.py\b",
        r"\bscripts/check-ask-user",
        r"\bAUQ-[A-Z-]+\b",
        r"\bI21\b",
        r"\bsub-checks?\b",
        r"\bvalidation\b",
    ),
)

SPAWNED_AGENT_PROHIBITION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\b(?:do\s+not|don't|never|cannot|can't)\b"
        r".*\bAskUserQuestion\b",
        r"\bAskUserQuestion\b"
        r".*\b(?:do\s+not|don't|never|cannot|can't)\b",
    ),
)

MISSING_INPUT_CONTEXT_RE: Final[Pattern[str]] = re.compile(
    r"AskUserQuestion.*(to\s+get|to\s+ask"
    r"|if\s+(no|omit|miss|not\s+provided))",
    re.IGNORECASE,
)
INPUT_COLLECTION_CONTEXT_RE: Final[Pattern[str]] = re.compile(
    r"(ask|collect|gather|get)\s+.{0,40}"
    r"(using|via)\s+AskUserQuestion"
    r"|AskUserQuestion\s+.{0,20}(ask|collect|gather|get)",
    re.IGNORECASE,
)
WITH_OPTIONS_RE: Final[Pattern[str]] = re.compile(
    r"with\s+options|options:",
    re.IGNORECASE,
)
QUOTED_BULLET_RE: Final[Pattern[str]] = re.compile(
    r"^\s*-\s+[\"']",
)
OPTION_KEYWORD_RE: Final[Pattern[str]] = re.compile(
    r"[Oo]ption\s*\d|[Oo]ptions:",
)
NUMBERED_OPTION_RE: Final[Pattern[str]] = re.compile(r"^\s*\d+\.\s+")
DESCRIPTIVE_BULLET_RE: Final[Pattern[str]] = re.compile(
    r"^\s*-\s+\S.{10,}",
)

DESTRUCTIVE_PATTERN_SPECS: Final[tuple[tuple[str, str], ...]] = (
    ("k3d cluster operation", r"k3d\s+(cluster|create|delete)"),
    ("git reset", r"git\s+reset"),
    ("git branch delete", r"git\s+branch\s+-[dD]"),
    ("git push --force", r"git\s+push\s+--force"),
    ("git clean", r"git\s+clean"),
    (
        "kubectl delete/drain/cordon",
        r"kubectl\s+(delete|drain|cordon)",
    ),
    ("helm uninstall/delete", r"helm\s+(uninstall|delete)"),
    ("rm -rf", r"\brm\s+-rf\b"),
    ("git apply --cached", r"git\s+apply\s+--cached"),
)
DESTRUCTIVE_PATTERNS: Final[
    tuple[tuple[str, Pattern[str]], ...]
] = tuple(
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in DESTRUCTIVE_PATTERN_SPECS
)

CONFIRMATION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bconfirm\b",
        r"\bapproval\b",
        r"\bapprove\b",
        r"\bask.*before\b",
        r"\bgate\b",
        r"\bAskUserQuestion\b",
    ),
)

AMBIGUITY_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bif\s+(unclear|ambiguous)\b",
        r"\bmultiple\s+.{0,20}\s+match\b",
        r"\bcould\s+mean\b",
        r"\bmore\s+than\s+one\b",
        r"\b(uncertain|unsure)\s+(which|what|whether)\b",
        r"\bcannot\s+determine\b",
        r"\bmultiple\s+(valid|possible)\s+"
        r"(interpretations|options|matches|candidates)\b",
    ),
)

RESOLUTION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bAskUserQuestion\b",
        r"\bask\b",
        r"\bprompt\b",
        r"\bconfirm\b",
        r"\bdefault\s+to\b",
        r"\bfall\s*back\b",
        r"\buse\s+the\s+first\b",
    ),
)

MULTISELECT_RE: Final[Pattern[str]] = re.compile(r"\bmultiSelect\b")
GROUPING_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\bgroup\s+by\b",
        r"\bpre-select\b",
        r"\bstrength\b",
        r"\bconfidence\b",
        r"\bpriority\b",
        r"\b[Ss]trong\s+signals?\b",
        r"\b[Mm]oderate\s+signals?\b",
    ),
)

WIZARD_CONFIRM_RE: Final[Pattern[str]] = re.compile(
    r"\bconfirm\b",
    re.IGNORECASE,
)
WIZARD_LOOP_RE: Final[Pattern[str]] = re.compile(
    r"\b(loop|repeat|again|until\s+user\s+confirms)\b",
    re.IGNORECASE,
)
WIZARD_TERMINATION_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"\buntil\s+user\s+confirms\b",
        r"\bLoop\s+until\b",
        r"\brepeat\s+until\b",
        r"\bconfirm\s+and\s+save\b",
        r"\buser\s+picks\b.*\bpresent\s+again\b",
    ),
)

ARG_PROMPT_TEMPLATES: Final[tuple[str, ...]] = (
    r"ask.*{name}",
    r"prompt.*{name}",
    r"AskUserQuestion.*{name}",
    r"{name}.*ask",
    r"{name}.*prompt",
)
POSITIONAL_PROMPT_PATTERNS: Final[
    tuple[Pattern[str], ...]
] = compile_patterns(
    (
        r"ask.*feature",
        r"ask.*name",
        r"prompt.*feature",
    ),
)
FALLBACK_KEYWORDS: Final[tuple[str, ...]] = (
    r"auto.?detect",
    r"default\s+to",
    r"fall\s*back",
    r"env\s*var",
    r"environment\s+variable",
    r"if\s+(no|not\s+provided|missing|omit)",
)


# ---------------------------------------------------------------------------
# ParsedSkill dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedSkill:
    """Store the parsed pieces needed by the AskUserQuestion checks."""

    frontmatter: dict[str, str]
    body: str
    body_start_line: int
    prose_lines: tuple[ProseLine, ...]
    bundled_indices: frozenset[int]
    agent_indices: frozenset[int]
    arguments: tuple[SkillArgument, ...]
    allowed_tools: frozenset[str]

    @property
    def declares_auq(self) -> bool:
        """Return whether AskUserQuestion is in allowed-tools."""
        return TOOL_NAME in self.allowed_tools

    @property
    def is_fork(self) -> bool:
        """Return whether the skill is a forked subagent."""
        return self.frontmatter.get("context", "") == "fork"

    @property
    def is_side_effect(self) -> bool:
        """Return whether disable-model-invocation is true."""
        return (
            self.frontmatter.get("disable-model-invocation", "")
            == "true"
        )

    def relevant_lines(
        self,
        *,
        exclude_bundled: bool = True,
        exclude_agents: bool = False,
    ) -> tuple[ProseLine, ...]:
        """Return prose lines filtered by section membership."""
        return tuple(
            line
            for line in self.prose_lines
            if (
                not exclude_bundled
                or line.index not in self.bundled_indices
            )
            and (
                not exclude_agents
                or line.index not in self.agent_indices
            )
        )

    def relevant_text(
        self,
        *,
        exclude_bundled: bool = True,
        exclude_agents: bool = False,
    ) -> str:
        """Return filtered prose joined into one searchable string."""
        return " ".join(
            line.text
            for line in self.relevant_lines(
                exclude_bundled=exclude_bundled,
                exclude_agents=exclude_agents,
            )
        )

    def prose_map(self) -> dict[int, str]:
        """Return a mapping from prose line index to line text."""
        return {line.index: line.text for line in self.prose_lines}

    def line_number(self, line_index: int) -> int:
        """Return a one-based file line number for a body line index."""
        return self.body_start_line + line_index


# ---------------------------------------------------------------------------
# Skill loading
# ---------------------------------------------------------------------------


def _format_signal_detail(
    strong_hits: list[str],
    medium_hits: list[str],
) -> str:
    """Build a compact detail string for implicit interaction hits."""
    samples = [*strong_hits, *medium_hits][:SUMMARY_HIT_LIMIT]
    return (
        f"{len(strong_hits)} strong, "
        f"{len(medium_hits)} medium signal(s): "
        + "; ".join(samples)
    )


def parse_skill(skill_dir: Path) -> ParsedSkill:
    """Parse one skill directory into the check structure."""
    skill_dir = Path(skill_dir)
    if not skill_dir.is_dir():
        msg = f"{skill_dir} is not a directory"
        raise SkillLoadError(msg)

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        msg = f"No SKILL.md found in {skill_dir}"
        raise SkillLoadError(msg)

    try:
        content = skill_md_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        msg = f"Error reading {skill_md_path}: {exc}"
        raise SkillLoadError(msg) from exc

    fm_lines, body_lines, body_start = split_frontmatter(content)
    frontmatter = parse_frontmatter_lines(fm_lines)
    body = "\n".join(body_lines)
    prose_lines = extract_prose_lines(body)

    return ParsedSkill(
        frontmatter=frontmatter,
        body=body,
        body_start_line=body_start,
        prose_lines=prose_lines,
        bundled_indices=find_bundled_indices(prose_lines),
        agent_indices=find_agent_indices(prose_lines),
        arguments=parse_arguments(body),
        allowed_tools=parse_allowed_tools(frontmatter),
    )


# ---------------------------------------------------------------------------
# AUQ-specific helper functions
# ---------------------------------------------------------------------------


def _mentions_in_prose(
    doc: ParsedSkill,
    keyword: str,
    *,
    skip_agents: bool = False,
    workflow_only: bool = False,
) -> bool:
    """Return whether keyword appears in relevant prose."""
    for line in doc.relevant_lines(exclude_agents=skip_agents):
        if keyword not in line.text:
            continue
        if (
            workflow_only
            and keyword == TOOL_NAME
            and not _is_auq_workflow_line(line.text)
        ):
            continue
        return True
    return False


def _is_auq_workflow_line(line_text: str) -> bool:
    """Return whether a line uses AskUserQuestion as workflow."""
    if TOOL_NAME not in line_text:
        return False
    return not matches_any(line_text, AUQ_NON_WORKFLOW_PATTERNS)


def _is_spawned_agent_violation(line_text: str) -> bool:
    """Return whether AUQ in an agent block is a real violation."""
    if not _is_auq_workflow_line(line_text):
        return False
    return not matches_any(
        line_text,
        SPAWNED_AGENT_PROHIBITION_PATTERNS,
    )


def _normalize_argument_name(name: str) -> str:
    """Normalize an argument name for prose matching."""
    cleaned = re.sub(r"^[-(]+", "", name).strip(")")
    return (cleaned.strip() or name.strip()).lower()


def _build_search_units(
    lines: tuple[ProseLine, ...],
    *,
    window_size: int = REQUIRED_ARG_SEARCH_WINDOW,
) -> tuple[str, ...]:
    """Build local search units from nearby lines."""
    lowered_lines = [line.text.lower() for line in lines]
    if not lowered_lines:
        return ()

    units: list[str] = [*lowered_lines]
    if window_size <= 1:
        return tuple(units)

    for index in range(len(lowered_lines)):
        window = lowered_lines[index : index + window_size]
        if len(window) > 1:
            units.append(" ".join(window))

    units.append(" ".join(lowered_lines))
    return tuple(units)


def _has_ask_mechanism(
    argument_name: str,
    search_units: tuple[str, ...],
) -> bool:
    """Return whether the prose mentions prompting for an argument."""
    escaped_name = re.escape(argument_name)
    for template in ARG_PROMPT_TEMPLATES:
        pattern = template.format(name=escaped_name)
        if any(
            re.search(pattern, unit, re.IGNORECASE)
            for unit in search_units
        ):
            return True

    return "positional" in argument_name and any(
        matches_any(unit, POSITIONAL_PROMPT_PATTERNS)
        for unit in search_units
    )


def _has_fallback_mechanism(
    argument_name: str,
    search_units: tuple[str, ...],
) -> bool:
    """Return whether the prose mentions a fallback for an argument."""
    escaped_name = re.escape(argument_name)
    for pattern in FALLBACK_KEYWORDS:
        if any(
            re.search(rf"{pattern}.*{escaped_name}", unit)
            or re.search(rf"{escaped_name}.*{pattern}", unit)
            for unit in search_units
        ):
            return True
    return False


def _is_input_collection_context(line_text: str) -> bool:
    """Return whether an AUQ mention is about collecting input."""
    return bool(
        MISSING_INPUT_CONTEXT_RE.search(line_text)
        or INPUT_COLLECTION_CONTEXT_RE.search(line_text)
        or WITH_OPTIONS_RE.search(line_text),
    )


def _is_explicit_option_line(line_text: str) -> bool:
    """Return whether a line clearly describes explicit choices."""
    if QUOTED_BULLET_RE.search(line_text):
        return True
    if OPTION_KEYWORD_RE.search(line_text):
        return True
    return bool(
        NUMBERED_OPTION_RE.search(line_text)
        and "option" in line_text.lower(),
    )


def _has_nearby_options(
    doc: ParsedSkill,
    site_index: int,
) -> bool:
    """Return whether a nearby window has credible option structure."""
    prose = doc.prose_map()
    descriptive_bullets = 0

    for offset in range(OPTION_SCAN_START, OPTION_SCAN_STOP):
        check_index = site_index + offset
        if (
            check_index in doc.bundled_indices
            or check_index in doc.agent_indices
        ):
            continue

        nearby = prose.get(check_index, "")
        if not nearby:
            continue

        if _is_explicit_option_line(nearby):
            return True

        if DESCRIPTIVE_BULLET_RE.search(nearby):
            descriptive_bullets += 1
            if descriptive_bullets >= DESCRIPTIVE_BULLET_THRESHOLD:
                return True

    return False


def _window_text(
    doc: ParsedSkill,
    center_index: int,
    *,
    start_offset: int,
    stop_offset: int,
    exclude_agents: bool = False,
) -> str:
    """Return a joined prose window around one line index."""
    prose = doc.prose_map()
    parts: list[str] = []

    for offset in range(start_offset, stop_offset):
        check_index = center_index + offset
        if check_index in doc.bundled_indices:
            continue
        if exclude_agents and check_index in doc.agent_indices:
            continue

        text = prose.get(check_index, "")
        if text:
            parts.append(text)

    return " ".join(parts)


def _has_nearby_resolution(
    doc: ParsedSkill,
    line_index: int,
) -> bool:
    """Return whether an ambiguity line has nearby resolution."""
    return matches_any(
        _window_text(
            doc,
            line_index,
            start_offset=AMBIGUITY_SCAN_START,
            stop_offset=AMBIGUITY_SCAN_STOP,
            exclude_agents=True,
        ),
        RESOLUTION_PATTERNS,
    )


def _matching_destructive_labels(
    line_text: str,
) -> tuple[str, ...]:
    """Return destructive operation labels matching one line."""
    return tuple(
        label
        for label, pattern in DESTRUCTIVE_PATTERNS
        if pattern.search(line_text)
    )


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------


def check_declaration_match(
    doc: ParsedSkill,
    *,
    has_implicit: bool,
) -> CheckResult:
    """Check whether declaration and valid usage agree."""
    declared = doc.declares_auq
    body_uses = (
        _mentions_in_prose(
            doc,
            TOOL_NAME,
            skip_agents=True,
            workflow_only=True,
        )
        or has_implicit
    )

    if declared and body_uses:
        return CheckResult(
            CHECK_DECLARATION,
            passed=True,
            detail=f"{TOOL_NAME} declared and used in body",
        )

    if not declared and not body_uses:
        return CheckResult(
            CHECK_DECLARATION,
            passed=True,
            detail=f"{TOOL_NAME} not declared and not used",
        )

    if declared:
        return CheckResult(
            CHECK_DECLARATION,
            passed=False,
            detail=(
                f"{TOOL_NAME} in allowed-tools but not referenced "
                "in valid workflow prose - phantom declaration, "
                "remove from allowed-tools"
            ),
        )

    return CheckResult(
        CHECK_DECLARATION,
        passed=False,
        detail=(
            f"Body references {TOOL_NAME} or implies user "
            f"interaction but {TOOL_NAME} missing from "
            "allowed-tools"
        ),
    )


def check_implicit_interaction(
    doc: ParsedSkill,
) -> tuple[CheckResult, bool]:
    """Check for natural-language user interaction patterns."""
    strong_hits: list[str] = []
    medium_hits: list[str] = []

    for line in doc.relevant_lines(exclude_agents=True):
        if matches_any(line.text, NEGATION_PATTERNS):
            continue
        if matches_any(line.text, STRONG_INTERACTION_PATTERNS):
            strong_hits.append(
                format_hit(
                    line.index,
                    line.text,
                    body_start_line=doc.body_start_line,
                ),
            )
        if matches_any(line.text, MEDIUM_INTERACTION_PATTERNS):
            medium_hits.append(
                format_hit(
                    line.index,
                    line.text,
                    body_start_line=doc.body_start_line,
                ),
            )

    has_implicit = (
        bool(strong_hits)
        or len(medium_hits) >= MEDIUM_SIGNAL_THRESHOLD
    )

    if doc.declares_auq:
        if has_implicit:
            detail = (
                f"{TOOL_NAME} in allowed-tools - implicit "
                "interaction patterns detected: "
                + _format_signal_detail(strong_hits, medium_hits)
            )
        else:
            detail = (
                f"{TOOL_NAME} in allowed-tools - no implicit "
                "user interaction patterns detected"
            )
        return (
            CheckResult(CHECK_IMPLICIT, passed=True, detail=detail),
            has_implicit,
        )

    if not has_implicit:
        if medium_hits:
            detail = (
                "1 medium signal (below threshold of "
                f"{MEDIUM_SIGNAL_THRESHOLD}): "
                f"{medium_hits[0].split(':', maxsplit=1)[0]}"
            )
        else:
            detail = "No implicit user interaction patterns detected"
        return (
            CheckResult(CHECK_IMPLICIT, passed=True, detail=detail),
            False,
        )

    return (
        CheckResult(
            CHECK_IMPLICIT,
            passed=False,
            detail=(
                "Implicit interaction signals detected but "
                f"{TOOL_NAME} not in allowed-tools: "
                + _format_signal_detail(strong_hits, medium_hits)
            ),
        ),
        True,
    )


def check_required_arg_fallback(
    doc: ParsedSkill,
) -> list[CheckResult]:
    """Check that required arguments have prompting or fallback."""
    if not doc.arguments:
        return [
            CheckResult(
                CHECK_REQUIRED_ARG,
                passed=True,
                detail="No argument table found - skipped",
            ),
        ]

    if not doc.declares_auq:
        return [
            CheckResult(
                CHECK_REQUIRED_ARG,
                passed=True,
                detail=(
                    f"{TOOL_NAME} not in allowed-tools - "
                    "skip required-arg check"
                ),
            ),
        ]

    required_arguments = [
        argument
        for argument in doc.arguments
        if argument.default in REQUIRED_DEFAULT_MARKERS
        and not argument.name.startswith("--")
    ]
    if not required_arguments:
        return [
            CheckResult(
                CHECK_REQUIRED_ARG,
                passed=True,
                detail="No required arguments (all have defaults)",
            ),
        ]

    search_units = _build_search_units(
        doc.relevant_lines(exclude_agents=True),
    )
    failures: list[CheckResult] = []

    for argument in required_arguments:
        normalized = _normalize_argument_name(argument.name)
        if _has_ask_mechanism(normalized, search_units):
            continue
        if _has_fallback_mechanism(normalized, search_units):
            continue
        failures.append(
            CheckResult(
                CHECK_REQUIRED_ARG,
                passed=False,
                detail=(
                    f"Required arg `{argument.name}` has no "
                    "ask/prompt mechanism and no fallback - "
                    f"{TOOL_NAME} is available but not used "
                    "for missing input"
                ),
            ),
        )

    if failures:
        return failures

    return [
        CheckResult(
            CHECK_REQUIRED_ARG,
            passed=True,
            detail=(
                f"All {len(required_arguments)} required arg(s) "
                "have ask or fallback paths"
            ),
        ),
    ]


def check_spawned_agent(doc: ParsedSkill) -> CheckResult:
    """Check that spawned-agent sections do not use AUQ."""
    if doc.is_fork:
        return CheckResult(
            CHECK_SPAWNED,
            passed=True,
            detail=(
                "context: fork - entire skill is a subagent, "
                "check skipped"
            ),
        )

    if not doc.agent_indices:
        return CheckResult(
            CHECK_SPAWNED,
            passed=True,
            detail="No spawned agent sections detected",
        )

    violations = [
        f"L{doc.line_number(line.index)}"
        for line in doc.prose_lines
        if line.index in doc.agent_indices
        and _is_spawned_agent_violation(line.text)
    ]
    if not violations:
        return CheckResult(
            CHECK_SPAWNED,
            passed=True,
            detail=f"No {TOOL_NAME} in spawned agent sections",
        )

    return CheckResult(
        CHECK_SPAWNED,
        passed=False,
        detail=(
            f"{TOOL_NAME} in spawned agent section (agents "
            "cannot interact with users): "
            + ", ".join(violations)
        ),
    )


def check_option_structure(doc: ParsedSkill) -> CheckResult:
    """Check that AUQ usage sites show nearby choices."""
    if not doc.declares_auq:
        return CheckResult(
            CHECK_OPTION,
            passed=True,
            detail=f"{TOOL_NAME} not in allowed-tools - skipped",
        )

    usage_sites = [
        line.index
        for line in doc.relevant_lines(exclude_agents=True)
        if _is_auq_workflow_line(line.text)
    ]
    if not usage_sites:
        return CheckResult(
            CHECK_OPTION,
            passed=True,
            detail=(
                f"No explicit {TOOL_NAME} mentions "
                "in workflow prose"
            ),
        )

    prose = doc.prose_map()
    violations: list[str] = []

    for site_index in usage_sites:
        line_text = prose.get(site_index, "")
        if _is_input_collection_context(line_text):
            continue
        if not _has_nearby_options(doc, site_index):
            violations.append(f"L{doc.line_number(site_index)}")

    if not violations:
        return CheckResult(
            CHECK_OPTION,
            passed=True,
            detail=(
                f"All {len(usage_sites)} {TOOL_NAME} site(s) "
                "have option structure"
            ),
        )

    return CheckResult(
        CHECK_OPTION,
        passed=False,
        detail=(
            f"{TOOL_NAME} mentioned without nearby "
            "options/choices: " + ", ".join(violations)
        ),
    )


def check_destructive(doc: ParsedSkill) -> CheckResult:
    """Check that destructive steps have nearby confirmation."""
    if not doc.is_side_effect:
        return CheckResult(
            CHECK_DESTRUCTIVE,
            passed=True,
            detail=(
                "disable-model-invocation not true - skipped"
            ),
        )

    destructive_hits: list[str] = []
    missing_confirmation: list[str] = []

    for line in doc.relevant_lines(exclude_agents=True):
        labels = _matching_destructive_labels(line.text)
        if not labels:
            continue

        destructive_hits.extend(labels)
        local_text = _window_text(
            doc,
            line.index,
            start_offset=CONFIRMATION_SCAN_START,
            stop_offset=CONFIRMATION_SCAN_STOP,
            exclude_agents=True,
        )
        if not matches_any(local_text, CONFIRMATION_PATTERNS):
            label_text = ", ".join(dict.fromkeys(labels))
            missing_confirmation.append(
                f"L{doc.line_number(line.index)}: {label_text}",
            )

    if not destructive_hits:
        return CheckResult(
            CHECK_DESTRUCTIVE,
            passed=True,
            detail="No destructive patterns detected",
        )

    if not missing_confirmation:
        return CheckResult(
            CHECK_DESTRUCTIVE,
            passed=True,
            detail=(
                "Destructive patterns present and each one has "
                "nearby confirmation guidance"
            ),
        )

    return CheckResult(
        CHECK_DESTRUCTIVE,
        passed=False,
        detail=(
            "Destructive patterns without nearby confirmation "
            "guidance: "
            + "; ".join(
                missing_confirmation[:DETAIL_LIMIT],
            )
        ),
    )


def check_ambiguity(doc: ParsedSkill) -> CheckResult:
    """Check that ambiguity guidance has a nearby resolution path."""
    violations: list[str] = []

    for line in doc.relevant_lines(exclude_agents=True):
        if not matches_any(line.text, AMBIGUITY_PATTERNS):
            continue
        if _has_nearby_resolution(doc, line.index):
            continue

        violations.append(
            format_hit(
                line.index,
                line.text,
                body_start_line=doc.body_start_line,
                width=AMBIGUITY_PREVIEW_WIDTH,
            ),
        )

    if not violations:
        return CheckResult(
            CHECK_AMBIGUITY,
            passed=True,
            detail="No unresolved ambiguity patterns",
        )

    return CheckResult(
        CHECK_AMBIGUITY,
        passed=False,
        detail=(
            "Ambiguity without resolution mechanism: "
            + "; ".join(violations[:DETAIL_LIMIT])
        ),
    )


def check_multiselect(doc: ParsedSkill) -> CheckResult:
    """Check that multiSelect usage includes grouping guidance."""
    relevant_text = doc.relevant_text(exclude_agents=True)
    if not MULTISELECT_RE.search(relevant_text):
        return CheckResult(
            CHECK_MULTISELECT,
            passed=True,
            detail="No multiSelect usage - skipped",
        )

    if matches_any(relevant_text, GROUPING_PATTERNS):
        return CheckResult(
            CHECK_MULTISELECT,
            passed=True,
            detail="multiSelect usage has grouping guidance",
        )

    return CheckResult(
        CHECK_MULTISELECT,
        passed=False,
        detail=(
            "multiSelect used without grouping guidance "
            "(group by strength/confidence recommended)"
        ),
    )


def check_wizard(doc: ParsedSkill) -> CheckResult:
    """Check that wizard loops have explicit termination."""
    relevant_text = doc.relevant_text(exclude_agents=True)
    has_wizard = (
        _mentions_in_prose(
            doc,
            TOOL_NAME,
            skip_agents=True,
            workflow_only=True,
        )
        and bool(WIZARD_CONFIRM_RE.search(relevant_text))
        and bool(WIZARD_LOOP_RE.search(relevant_text))
    )
    if not has_wizard:
        return CheckResult(
            CHECK_WIZARD,
            passed=True,
            detail=(
                "No confirmation wizard pattern detected "
                "- skipped"
            ),
        )

    if matches_any(relevant_text, WIZARD_TERMINATION_PATTERNS):
        return CheckResult(
            CHECK_WIZARD,
            passed=True,
            detail="Wizard pattern has explicit loop termination",
        )

    return CheckResult(
        CHECK_WIZARD,
        passed=False,
        detail=(
            "Wizard pattern detected without explicit "
            "loop termination"
        ),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_checks(doc: ParsedSkill) -> list[CheckResult]:
    """Run all AskUserQuestion checks in stable output order."""
    implicit_result, has_implicit = check_implicit_interaction(doc)
    declaration_result = check_declaration_match(
        doc,
        has_implicit=has_implicit,
    )

    return [
        declaration_result,
        implicit_result,
        *check_required_arg_fallback(doc),
        check_spawned_agent(doc),
        check_option_structure(doc),
        check_destructive(doc),
        check_ambiguity(doc),
        check_multiselect(doc),
        check_wizard(doc),
    ]


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate AskUserQuestion usage in SKILL.md files"
        ),
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
        parsed_skill = parse_skill(args.skill_directory)
    except SkillLoadError as exc:
        emit_error(f"Error: {exc}")
        return EXIT_USAGE_ERROR

    return emit_results(run_checks(parsed_skill))


if __name__ == "__main__":
    raise SystemExit(main())
