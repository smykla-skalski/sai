"""Shared helpers for review-skill validation scripts.

Provides SKILL.md parsing (frontmatter, body, prose extraction),
section detection (headings, bundled resources, agent instructions,
arguments), data classes (CheckResult, ProseLine, SkillArgument,
SkillDocument), NDJSON output helpers, CLI boilerplate, fenced-block
utilities, and pattern matching utilities.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_OK: Final[int] = 0
EXIT_FAILURE: Final[int] = 1
EXIT_USAGE_ERROR: Final[int] = 2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FRONTMATTER_DELIMITER: Final[str] = "---"
FRONTMATTER_DELIMITER_COUNT: Final[int] = 2
BLOCK_SCALAR_MARKERS: Final[frozenset[str]] = frozenset(
    {">", ">-", "|", "|-"},
)
QUOTE_PAIR_LENGTH: Final[int] = 2
MIN_TABLE_COLUMNS: Final[int] = 2
SNIPPET_WIDTH: Final[int] = 80
RESOURCE_SUBDIRECTORIES: Final[tuple[str, ...]] = (
    "references",
    "scripts",
    "assets",
    "examples",
)


def read_text(path: Path) -> str:
    """Read text from a file using UTF-8 with replacement."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

FRONTMATTER_FIELD_RE: Final[Pattern[str]] = re.compile(
    r"^(?P<key>\w[\w-]*):\s*(?P<value>.*)$",
)
FENCE_RE: Final[Pattern[str]] = re.compile(r"^\s*```")
YAML_LIST_ITEM_RE: Final[Pattern[str]] = re.compile(r"^\s*-\s+(.*)$")
HEADING_L2_RE: Final[Pattern[str]] = re.compile(r"^##\s+")
HEADING_L3_RE: Final[Pattern[str]] = re.compile(r"^###\s+")
BUNDLED_HEADING_RE: Final[Pattern[str]] = re.compile(r"^##\s+[Bb]undled")
ARGUMENTS_HEADING_RE: Final[Pattern[str]] = re.compile(
    r"^##\s+[Aa]rguments",
)
TABLE_SEPARATOR_RE: Final[Pattern[str]] = re.compile(r"^\|[\s:-]+\|$")
BULLET_LIST_ITEM_RE: Final[Pattern[str]] = re.compile(r"^\s*[-*+]\s+")
NUMBERED_LIST_ITEM_RE: Final[Pattern[str]] = re.compile(r"^\s*\d+\.\s+")


# ---------------------------------------------------------------------------
# Pattern utility functions
# ---------------------------------------------------------------------------


def compile_patterns(
    raw_patterns: tuple[str, ...],
    *,
    flags: re.RegexFlag = re.IGNORECASE,
) -> tuple[Pattern[str], ...]:
    """Compile a tuple of raw regex strings into Pattern objects."""
    return tuple(re.compile(p, flags) for p in raw_patterns)


AGENT_SECTION_START_PATTERNS: Final[tuple[Pattern[str], ...]] = compile_patterns(
    (
        r"spawn\s+(a|an)\s+",
        r"create\s+the\s+agent\s+with",
        r"agent\s+instructions:",
        r"the\s+agent\s+must:",
        r"instruct\s+the\s+agent\s+to",
        r"pass\s+the\s+agent:",
    ),
)


def matches_any(
    text: str,
    patterns: tuple[Pattern[str], ...],
) -> bool:
    """Return whether any compiled pattern matches the text."""
    return any(pattern.search(text) for pattern in patterns)


def format_hit(
    index: int,
    text: str,
    *,
    body_start_line: int,
    width: int = SNIPPET_WIDTH,
) -> str:
    """Format one matching line as ``L<line>: <excerpt>``."""
    snippet = text.strip()[:width]
    return f"L{body_start_line + index}: {snippet}"


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class SkillLoadError(ValueError):
    """Represent an input or parsing error for skill loading."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    """Store one check output record."""

    check: str
    passed: bool
    detail: str

    def payload(self) -> dict[str, bool | str]:
        """Return a serializable payload for NDJSON output."""
        return {
            "check": self.check,
            "pass": self.passed,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ProseLine:
    """Store one prose line from the SKILL.md body."""

    index: int
    text: str


@dataclass(frozen=True)
class SkillArgument:
    """Store one parsed argument row from the Arguments table."""

    name: str
    default: str


@dataclass(frozen=True)
class SkillDocument:
    """Store parsed skill source and derived values for checks."""

    skill_dir: Path
    skill_md_path: Path
    content: str
    frontmatter: dict[str, str]
    body: str
    prose_body: str
    body_start_line: int
    resource_files: tuple[Path, ...]

    def field(self, name: str) -> str:
        """Return a parsed frontmatter field or an empty string."""
        return self.frontmatter.get(name, "")

    def has_field(self, name: str) -> bool:
        """Return whether a frontmatter field is present."""
        return name in self.frontmatter

    def line_number(self, body_line_index: int) -> int:
        """Return absolute file line number for a body-relative index."""
        return self.body_start_line + body_line_index


# ---------------------------------------------------------------------------
# NDJSON output helpers
# ---------------------------------------------------------------------------


def emit_record(payload: object) -> None:
    """Emit one NDJSON line to stdout."""
    sys.stdout.write(f"{json.dumps(payload, ensure_ascii=False)}\n")


def emit_error(message: str) -> None:
    """Write one error message to stderr."""
    sys.stderr.write(f"{message}\n")


def emit_results(
    results: list[CheckResult],
    *,
    extra_summary: dict[str, object] | None = None,
) -> int:
    """Emit all check records and summary, then return exit code."""
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    for result in results:
        emit_record(result.payload())

    summary: dict[str, object] = {
        "summary": True,
        "total": len(results),
        "passed": passed,
        "failed": failed,
    }
    if extra_summary:
        summary.update(extra_summary)
    emit_record(summary)

    if failed:
        return EXIT_FAILURE
    return EXIT_OK


@dataclass
class ResultCollector:
    """Collect check results and stream them as NDJSON."""

    total: int = field(default=0, init=False)
    passed: int = field(default=0, init=False)
    failed: int = field(default=0, init=False)

    def add(self, result: CheckResult) -> None:
        """Record one result and emit it immediately."""
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        emit_record(result.payload())

    def emit_summary(self) -> None:
        """Emit the final summary line."""
        emit_record(
            {
                "summary": True,
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
            },
        )


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def split_frontmatter(
    content: str,
) -> tuple[list[str], list[str], int]:
    """Split into frontmatter lines, body lines, and body start line."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return [], lines, 1

    delimiter_count = 0
    for index, line in enumerate(lines):
        if line.strip() == FRONTMATTER_DELIMITER:
            delimiter_count += 1
            if delimiter_count == FRONTMATTER_DELIMITER_COUNT:
                body_start_line = index + 2
                return (
                    lines[1:index],
                    lines[index + 1 :],
                    body_start_line,
                )

    return [], lines, 1


def strip_wrapping_quotes(value: str) -> str:
    """Strip matching single or double quotes from a scalar value."""
    if len(value) < QUOTE_PAIR_LENGTH:
        return value
    if value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def strip_inline_comment(value: str) -> str:
    """Strip YAML-style inline comments while respecting quotes."""
    in_single_quote = False
    in_double_quote = False
    escaped = False

    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if (
            char == "#"
            and not in_single_quote
            and not in_double_quote
            and (index == 0 or value[index - 1].isspace())
        ):
            return value[:index].rstrip()

    return value.strip()


def split_csv_like(value: str) -> list[str]:
    """Split comma-separated values while preserving quoted commas."""
    parts: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    escaped = False

    for char in value:
        if escaped:
            buffer.append(char)
            escaped = False
            continue
        if char == "\\":
            buffer.append(char)
            escaped = True
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            buffer.append(char)
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            buffer.append(char)
            continue

        if char == "," and not in_single_quote and not in_double_quote:
            part = "".join(buffer).strip()
            if part:
                parts.append(part)
            buffer.clear()
            continue

        buffer.append(char)

    trailing = "".join(buffer).strip()
    if trailing:
        parts.append(trailing)

    return parts


def _parse_inline_list_value(raw_value: str) -> str | None:
    """Parse a YAML inline list (``[a, b]``) to comma-separated."""
    value = strip_inline_comment(raw_value).strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None

    inner = value[1:-1].strip()
    if not inner:
        return ""

    items = [
        strip_wrapping_quotes(item.strip())
        for item in split_csv_like(inner)
        if item.strip()
    ]
    return ", ".join(items)


def _consume_block_scalar(
    lines: list[str],
    start_index: int,
) -> tuple[str, int]:
    """Consume one indented block scalar and return joined value."""
    values: list[str] = []
    index = start_index

    while index < len(lines) and lines[index][:1].isspace():
        stripped = lines[index].strip()
        if stripped:
            values.append(stripped)
        index += 1

    return " ".join(values), index


def _consume_list_value(
    lines: list[str],
    start_index: int,
) -> tuple[str, int]:
    """Consume an indented YAML-style list, return comma-joined."""
    items: list[str] = []
    index = start_index

    while index < len(lines):
        if not lines[index][:1].isspace():
            break

        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue

        match = YAML_LIST_ITEM_RE.match(stripped)
        if match is None:
            break

        item = strip_inline_comment(match.group(1).strip())
        items.append(strip_wrapping_quotes(item))
        index += 1

    return ", ".join(item for item in items if item), index


def parse_frontmatter_lines(
    frontmatter_lines: list[str],
) -> dict[str, str]:
    """Parse frontmatter lines into a simple key-value dictionary."""
    if not frontmatter_lines:
        return {}

    parsed: dict[str, str] = {}
    index = 0

    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        if line[:1].isspace():
            index += 1
            continue

        match = FRONTMATTER_FIELD_RE.match(line)
        if match is None:
            index += 1
            continue

        key = match.group("key")
        raw_value = match.group("value").strip()
        index += 1

        inline_list = _parse_inline_list_value(raw_value)
        if inline_list is not None:
            parsed[key] = inline_list
            continue

        if raw_value in BLOCK_SCALAR_MARKERS:
            parsed[key], index = _consume_block_scalar(
                frontmatter_lines,
                index,
            )
            continue

        if raw_value == "":
            parsed[key], index = _consume_list_value(
                frontmatter_lines,
                index,
            )
            continue

        clean_value = strip_inline_comment(raw_value)
        parsed[key] = strip_wrapping_quotes(clean_value)

    return parsed


def parse_allowed_tools(
    frontmatter: dict[str, str],
) -> frozenset[str]:
    """Parse allowed-tools into a normalized frozenset."""
    raw_tools = strip_inline_comment(
        frontmatter.get("allowed-tools", ""),
    )
    parsed_tools = [
        strip_wrapping_quotes(tool.strip())
        for tool in split_csv_like(raw_tools)
        if tool.strip()
    ]
    return frozenset(parsed_tools)


# ---------------------------------------------------------------------------
# Body and prose extraction
# ---------------------------------------------------------------------------


def strip_fenced_code_blocks(text: str) -> str:
    """Remove fenced code-block content from markdown text."""
    lines: list[str] = []
    in_fence = False

    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)

    return "\n".join(lines)


def extract_prose_lines(body: str) -> tuple[ProseLine, ...]:
    """Return body lines outside fenced code blocks."""
    prose_lines: list[ProseLine] = []
    in_fence = False

    for index, line in enumerate(body.splitlines()):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose_lines.append(ProseLine(index=index, text=line))

    return tuple(prose_lines)


def build_fenced_line_indices(lines: list[str]) -> frozenset[int]:
    """Return indices of lines that are inside or on fenced code blocks."""
    fenced: set[int] = set()
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced.add(i)
            in_fence = not in_fence
            continue
        if in_fence:
            fenced.add(i)
    return frozenset(fenced)


FENCE_LANG_RE: Final[Pattern[str]] = re.compile(
    r"^\s*```\s*(?P<language>[a-zA-Z0-9_-]+)?.*$",
)


def fence_language(line: str) -> str:
    """Extract normalized language token from an opening fence line."""
    without_fence = FENCE_RE.sub("", line, count=1)
    language = without_fence.strip().split(maxsplit=1)
    if not language:
        return ""
    return language[0].lower()


def iter_fence_lines(
    text: str,
    languages: frozenset[str],
) -> Iterator[ProseLine]:
    """Yield lines inside fenced code blocks matching given languages."""
    in_fence = False
    in_matching_fence = False

    for index, line in enumerate(text.splitlines()):
        if FENCE_RE.match(line):
            if in_fence:
                in_fence = False
                in_matching_fence = False
            else:
                in_fence = True
                in_matching_fence = fence_language(line) in languages
            continue

        if in_fence and in_matching_fence:
            yield ProseLine(index=index, text=line)


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------


def is_section_exit(stripped_line: str) -> bool:
    """Return whether a line starts a new level-two section."""
    return bool(
        HEADING_L2_RE.match(stripped_line) and not HEADING_L3_RE.match(stripped_line),
    )


def starts_new_paragraph(line_text: str) -> bool:
    """Return whether a line looks like new top-level narrative."""
    return (
        not line_text.startswith((" ", "\t"))
        and not BULLET_LIST_ITEM_RE.match(line_text)
        and not NUMBERED_LIST_ITEM_RE.match(line_text)
    )


def find_bundled_indices(
    prose_lines: tuple[ProseLine, ...],
) -> frozenset[int]:
    """Return line indices that belong to the Bundled section."""
    indices: set[int] = set()
    in_bundled = False

    for line in prose_lines:
        stripped = line.text.strip()
        if BUNDLED_HEADING_RE.match(stripped):
            in_bundled = True
            indices.add(line.index)
            continue

        if (
            in_bundled
            and HEADING_L2_RE.match(stripped)
            and not HEADING_L3_RE.match(stripped)
        ):
            in_bundled = False
            continue

        if in_bundled:
            indices.add(line.index)

    return frozenset(indices)


def find_agent_indices(
    prose_lines: tuple[ProseLine, ...],
) -> frozenset[int]:
    """Return line indices in spawned-agent instruction blocks."""
    indices: set[int] = set()
    in_agent = False
    blank_count = 0

    for line in prose_lines:
        stripped = line.text.strip()

        if in_agent and HEADING_L3_RE.match(stripped):
            in_agent = False
            blank_count = 0

        if in_agent:
            if not stripped:
                blank_count += 1
                continue
            if blank_count > 0 and starts_new_paragraph(line.text):
                in_agent = False
                blank_count = 0
            else:
                blank_count = 0
                indices.add(line.index)
                continue

        if not in_agent and matches_any(
            stripped,
            AGENT_SECTION_START_PATTERNS,
        ):
            in_agent = True
            blank_count = 0
            indices.add(line.index)

    return frozenset(indices)


# ---------------------------------------------------------------------------
# Argument table parsing
# ---------------------------------------------------------------------------


def extract_arguments_section_lines(body: str) -> list[str]:
    """Return stripped lines from the Arguments section."""
    section_lines: list[str] = []
    in_arguments = False
    in_fence = False

    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        stripped = line.strip()
        if ARGUMENTS_HEADING_RE.match(stripped):
            in_arguments = True
            continue
        if in_arguments and is_section_exit(stripped):
            break
        if in_arguments:
            section_lines.append(stripped)

    return section_lines


def split_markdown_table_cells(row: str) -> list[str]:
    r"""Split table cells supporting escaped pipes (``\|``)."""
    parts = re.split(r"(?<!\\)\|", row)
    cells = [part.replace(r"\|", "|").strip() for part in parts]
    return [cell for cell in cells if cell]


def try_parse_table_row(
    stripped_line: str,
) -> SkillArgument | None:
    """Parse one markdown table row into a SkillArgument."""
    cells = split_markdown_table_cells(stripped_line)
    if len(cells) < MIN_TABLE_COLUMNS:
        return None
    return SkillArgument(
        name=cells[0].strip("`").strip(),
        default=cells[1].strip("`").strip(),
    )


def parse_arguments(body: str) -> tuple[SkillArgument, ...]:
    """Parse the Arguments markdown table into structured data."""
    section_lines = extract_arguments_section_lines(body)
    table_started = False
    separator_seen = False
    arguments: list[SkillArgument] = []

    for stripped_line in section_lines:
        if not stripped_line.startswith("|"):
            if table_started and separator_seen:
                break
            continue

        if not table_started:
            table_started = True
            continue

        if TABLE_SEPARATOR_RE.match(stripped_line):
            separator_seen = True
            continue

        if not separator_seen:
            continue

        argument = try_parse_table_row(stripped_line)
        if argument is not None:
            arguments.append(argument)

    return tuple(arguments)


# ---------------------------------------------------------------------------
# Skill document loading
# ---------------------------------------------------------------------------


def find_plugin_root(
    skill_dir: Path,
    *,
    max_depth: int = 4,
) -> Path | None:
    """Find plugin root by walking up for `.claude-plugin/plugin.json`."""
    search_dir = Path(skill_dir).resolve()

    for _ in range(max_depth):
        search_dir = search_dir.parent
        plugin_manifest = search_dir / ".claude-plugin" / "plugin.json"
        if plugin_manifest.is_file():
            return search_dir

    return None


def _collect_resource_files(
    skill_dir: Path,
    skill_md_path: Path,
) -> tuple[Path, ...]:
    """Collect top-level resource files for shell checks."""
    files: list[Path] = [skill_md_path]

    for subdir_name in RESOURCE_SUBDIRECTORIES:
        subdir_path = skill_dir / subdir_name
        if not subdir_path.is_dir():
            continue
        files.extend(
            child_path
            for child_path in sorted(subdir_path.iterdir())
            if child_path.is_file()
        )

    return tuple(files)


def load_skill_document(skill_dir: Path) -> SkillDocument:
    """Load SKILL.md and derived parsing artifacts for checks."""
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
    except OSError as error:
        msg = f"Error reading {skill_md_path}: {error}"
        raise SkillLoadError(msg) from error

    fm_lines, body_lines, body_start = split_frontmatter(content)
    frontmatter = parse_frontmatter_lines(fm_lines)
    body = "\n".join(body_lines)

    return SkillDocument(
        skill_dir=skill_dir,
        skill_md_path=skill_md_path,
        content=content,
        frontmatter=frontmatter,
        body=body,
        prose_body=strip_fenced_code_blocks(body),
        body_start_line=body_start,
        resource_files=_collect_resource_files(
            skill_dir,
            skill_md_path,
        ),
    )


# ---------------------------------------------------------------------------
# CLI boilerplate helpers
# ---------------------------------------------------------------------------


def build_check_parser(
    description: str,
    check_order: tuple[str, ...] = (),
) -> argparse.ArgumentParser:
    """Build a standard CLI parser for checker scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "skill_directory",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    if check_order:
        parser.add_argument(
            "--check",
            action="append",
            choices=check_order,
            dest="checks",
            help="Run only the specified check (repeatable)",
        )
    return parser


def run_check_cli(
    description: str,
    check_order: tuple[str, ...],
    run_checks_fn: Callable[
        ...,
        list[CheckResult] | tuple[list[CheckResult], dict[str, object]],
    ],
    argv: list[str] | None = None,
) -> int:
    """Run standard checker CLI: parse args, load skill, run checks, emit.

    ``run_checks_fn`` receives ``(document, selected_checks)`` and returns
    either a plain ``list[CheckResult]`` or a ``(results, extra_summary)``
    tuple.
    """
    parser = build_check_parser(description, check_order)
    args = parser.parse_args(argv)

    try:
        document = load_skill_document(args.skill_directory)
    except SkillLoadError as error:
        emit_error(f"Error: {error}")
        return EXIT_USAGE_ERROR

    selected_checks = tuple(args.checks or ()) if check_order else ()
    outcome = run_checks_fn(document, selected_checks)

    if isinstance(outcome, tuple):
        results, extra_summary = outcome
        return emit_results(results, extra_summary=extra_summary)
    return emit_results(outcome)
