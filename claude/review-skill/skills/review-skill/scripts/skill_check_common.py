"""Shared helpers for review-skill validation scripts.

This module provides:
- loading/parsing `SKILL.md`
- frontmatter parsing with simple list/block-scalar support
- code-fence stripping for prose-only checks
- NDJSON result helpers shared by check scripts
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

FRONTMATTER_DELIMITER: Final[str] = "---"
FRONTMATTER_DELIMITER_COUNT: Final[int] = 2
BLOCK_SCALAR_MARKERS: Final[frozenset[str]] = frozenset({">", ">-", "|", "|-"})
RESOURCE_SUBDIRECTORIES: Final[tuple[str, ...]] = (
    "references",
    "scripts",
    "assets",
    "examples",
)
QUOTE_PAIR_LENGTH: Final[int] = 2

FIELD_PATTERN: Final[Pattern[str]] = re.compile(r"^(?P<key>\w[\w-]*):\s*(?P<value>.*)$")
LIST_ITEM_PATTERN: Final[Pattern[str]] = re.compile(r"^\s*-\s+(?P<value>.*)$")
FENCE_PATTERN: Final[Pattern[str]] = re.compile(r"^\s*```")


class SkillLoadError(ValueError):
    """Represent an input or parsing error for skill loading."""


@dataclass(frozen=True)
class CheckResult:
    """Store one check output record."""

    check: str
    passed: bool
    detail: str

    def payload(self) -> dict[str, bool | str]:
        """Return a serializable payload for NDJSON output."""
        return {"check": self.check, "pass": self.passed, "detail": self.detail}


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

    def line_number(self, body_line_index: int) -> int:
        """Return absolute file line number for a body-relative index."""
        return self.body_start_line + body_line_index


def emit_record(payload: object) -> None:
    """Emit one NDJSON line to stdout."""
    sys.stdout.write(f"{json.dumps(payload, ensure_ascii=False)}\n")


def emit_results(results: list[CheckResult]) -> int:
    """Emit all check records and summary, then return exit code."""
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    for result in results:
        emit_record(result.payload())

    emit_record(
        {
            "summary": True,
            "total": len(results),
            "passed": passed,
            "failed": failed,
        },
    )
    return 1 if failed > 0 else 0


def split_frontmatter(content: str) -> tuple[list[str], list[str], int]:
    """Split markdown into frontmatter lines, body lines, and body start line."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return [], lines, 1

    delimiter_count = 0
    for index, line in enumerate(lines):
        if line.strip() == FRONTMATTER_DELIMITER:
            delimiter_count += 1
            if delimiter_count == FRONTMATTER_DELIMITER_COUNT:
                body_start_line = index + 2
                return lines[1:index], lines[index + 1 :], body_start_line

    return [], lines, 1


def _strip_wrapping_quotes(value: str) -> str:
    """Strip matching single or double quotes from a scalar value."""
    if len(value) < QUOTE_PAIR_LENGTH:
        return value
    if value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _strip_inline_comment(value: str) -> str:
    """Strip a YAML-style inline comment while respecting quoted sections."""
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


def _split_csv_like(value: str) -> list[str]:
    """Split comma-separated values and preserve quoted commas."""
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
    """Parse an inline list (`[a, b]`) to a comma-separated string."""
    value = _strip_inline_comment(raw_value).strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None

    inner = value[1:-1].strip()
    if not inner:
        return ""

    items = [
        _strip_wrapping_quotes(item.strip())
        for item in _split_csv_like(inner)
        if item.strip()
    ]
    return ", ".join(items)


def _consume_block_scalar(lines: list[str], start_index: int) -> tuple[str, int]:
    """Consume indented block-scalar lines and return joined value plus index."""
    values: list[str] = []
    index = start_index

    while index < len(lines) and lines[index][:1].isspace():
        stripped = lines[index].strip()
        if stripped:
            values.append(stripped)
        index += 1

    return " ".join(values), index


def _consume_list_value(lines: list[str], start_index: int) -> tuple[str, int]:
    """Consume indented YAML list items and return joined value plus index."""
    items: list[str] = []
    index = start_index

    while index < len(lines):
        if not lines[index][:1].isspace():
            break

        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue

        match = LIST_ITEM_PATTERN.match(stripped)
        if match is None:
            break

        item = _strip_inline_comment(match.group("value").strip())
        items.append(_strip_wrapping_quotes(item))
        index += 1

    return ", ".join(item for item in items if item), index


def parse_frontmatter_lines(frontmatter_lines: list[str]) -> dict[str, str]:
    """Parse frontmatter lines into a flat string dictionary."""
    if not frontmatter_lines:
        return {}

    parsed: dict[str, str] = {}
    index = 0

    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        if line[:1].isspace():
            index += 1
            continue

        match = FIELD_PATTERN.match(line)
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
            parsed[key], index = _consume_block_scalar(frontmatter_lines, index)
            continue

        if raw_value == "":
            parsed[key], index = _consume_list_value(frontmatter_lines, index)
            continue

        cleaned = _strip_inline_comment(raw_value)
        parsed[key] = _strip_wrapping_quotes(cleaned)

    return parsed


def strip_fenced_code_blocks(text: str) -> str:
    """Remove fenced code-block content from markdown text."""
    lines: list[str] = []
    in_fence = False

    for line in text.splitlines():
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)

    return "\n".join(lines)


def _collect_resource_files(skill_dir: Path, skill_md_path: Path) -> tuple[Path, ...]:
    """Collect top-level resource files used by current shell checks."""
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
    """Load `SKILL.md` and derived parsing artifacts for checks."""
    skill_dir = Path(skill_dir)
    if not skill_dir.is_dir():
        msg = f"{skill_dir} is not a directory"
        raise SkillLoadError(msg)

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        msg = f"No SKILL.md found in {skill_dir}"
        raise SkillLoadError(msg)

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        msg = f"Error reading {skill_md_path}: {error}"
        raise SkillLoadError(msg) from error

    frontmatter_lines, body_lines, body_start_line = split_frontmatter(content)
    frontmatter = parse_frontmatter_lines(frontmatter_lines)
    body = "\n".join(body_lines)

    return SkillDocument(
        skill_dir=skill_dir,
        skill_md_path=skill_md_path,
        content=content,
        frontmatter=frontmatter,
        body=body,
        prose_body=strip_fenced_code_blocks(body),
        body_start_line=body_start_line,
        resource_files=_collect_resource_files(skill_dir, skill_md_path),
    )
