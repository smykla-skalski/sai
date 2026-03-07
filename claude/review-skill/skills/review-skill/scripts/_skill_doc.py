"""Shared helpers for parsing `SKILL.md` files.

The helpers in this module are intentionally small and conservative.
They support the subset of frontmatter patterns used by the review-skill
validators: simple scalars, block scalars, and YAML-style top-level lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

FRONTMATTER_DELIMITER: Final[str] = "---"
FRONTMATTER_DELIMITER_COUNT: Final[int] = 2
QUOTE_PAIR_LENGTH: Final[int] = 2
BLOCK_SCALAR_MARKERS: Final[frozenset[str]] = frozenset({">", ">-", "|", "|-"})

FRONTMATTER_FIELD_RE: Final[Pattern[str]] = re.compile(
    r"^(?P<key>\w[\w-]*):\s*(?P<value>.*)$",
)
FENCE_RE: Final[Pattern[str]] = re.compile(r"^\s*```")
YAML_LIST_ITEM_RE: Final[Pattern[str]] = re.compile(r"^\s*-\s+(.*)$")


class SkillDocumentError(ValueError):
    """Raised when a skill directory or `SKILL.md` file cannot be loaded."""

    @classmethod
    def not_directory(cls, skill_dir: Path) -> SkillDocumentError:
        """Build an error for a missing skill directory."""
        message = f"{skill_dir} is not a directory"
        return cls(message)

    @classmethod
    def missing_skill_md(cls, skill_dir: Path) -> SkillDocumentError:
        """Build an error for a directory without `SKILL.md`."""
        message = f"No SKILL.md found in {skill_dir}"
        return cls(message)

    @classmethod
    def unreadable_file(
        cls,
        skill_md_path: Path,
        error: OSError,
    ) -> SkillDocumentError:
        """Build an error for an unreadable `SKILL.md` file."""
        message = f"Error reading {skill_md_path}: {error}"
        return cls(message)


@dataclass(frozen=True)
class SkillDocument:
    """Parsed representation of one skill directory."""

    skill_dir: Path
    skill_md_path: Path
    content: str
    frontmatter: dict[str, str]
    body: str
    body_without_code_fences: str

    def field(self, name: str) -> str:
        """Return a parsed frontmatter field or an empty string."""
        return self.frontmatter.get(name, "")


def _split_frontmatter_and_body(content: str) -> tuple[list[str], list[str]]:
    """Split a document into frontmatter lines and body lines."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return [], lines

    delimiter_count = 0
    for index, line in enumerate(lines):
        if line.strip() == FRONTMATTER_DELIMITER:
            delimiter_count += 1
            if delimiter_count == FRONTMATTER_DELIMITER_COUNT:
                return lines[1:index], lines[index + 1 :]

    return [], lines


def _strip_wrapping_quotes(value: str) -> str:
    """Strip matching single or double quotes from a scalar value."""
    if len(value) < QUOTE_PAIR_LENGTH:
        return value
    if value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _consume_block_scalar(
    lines: list[str],
    start_index: int,
) -> tuple[str, int]:
    """Consume an indented block scalar value."""
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
    """Consume an indented YAML-style top-level list."""
    items: list[str] = []
    index = start_index

    while index < len(lines) and lines[index][:1].isspace():
        match = YAML_LIST_ITEM_RE.match(lines[index].strip())
        if match is not None:
            items.append(_strip_wrapping_quotes(match.group(1).strip()))
        index += 1

    return ", ".join(items), index


def _parse_frontmatter(frontmatter_lines: list[str]) -> dict[str, str]:
    """Parse frontmatter lines into a dictionary of string values."""
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

        if raw_value in BLOCK_SCALAR_MARKERS:
            parsed[key], index = _consume_block_scalar(frontmatter_lines, index)
            continue

        if raw_value == "":
            parsed[key], index = _consume_list_value(frontmatter_lines, index)
            continue

        parsed[key] = _strip_wrapping_quotes(raw_value)

    return parsed


def _strip_fenced_code_blocks(body_lines: list[str]) -> str:
    """Return the body text with fenced code blocks removed."""
    prose_lines: list[str] = []
    in_fence = False

    for line in body_lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose_lines.append(line)

    return "\n".join(prose_lines)


def load_skill_document(skill_dir: Path) -> SkillDocument:
    """Load and parse a skill directory into a `SkillDocument`."""
    if not skill_dir.is_dir():
        raise SkillDocumentError.not_directory(skill_dir)

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise SkillDocumentError.missing_skill_md(skill_dir)

    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise SkillDocumentError.unreadable_file(skill_md_path, error) from error

    frontmatter_lines, body_lines = _split_frontmatter_and_body(content)
    body = "\n".join(body_lines)
    return SkillDocument(
        skill_dir=skill_dir,
        skill_md_path=skill_md_path,
        content=content,
        frontmatter=_parse_frontmatter(frontmatter_lines),
        body=body,
        body_without_code_fences=_strip_fenced_code_blocks(body_lines),
    )
