#!/usr/bin/env python3
"""Common helpers for Codex review-skill validators."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

RESOURCE_DIRS = ("references", "scripts", "agents", "examples", "assets")
EXTERNAL_TARGET_PREFIXES = ("http://", "https://", "mailto:", "app://", "#", "/")
QUOTE_DELIMS = {'"', "'"}
MIN_QUOTED_LENGTH = 2

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class SkillDocument:
    skill_dir: Path
    skill_md_path: Path
    content: str
    frontmatter: dict[str, str]
    body: str
    body_start_line: int
    resource_files: tuple[Path, ...]


@dataclass(frozen=True)
class MarkdownLink:
    label: str
    target: str
    line: int


@dataclass(frozen=True)
class CodeBlock:
    info: str
    text: str
    line: int


@dataclass(frozen=True)
class CheckRecord:
    check: str
    passed: bool
    level: str
    detail: str
    file: str | None = None
    line: int | None = None


class SkillLoadError(RuntimeError):
    """Raised when a skill bundle cannot be loaded."""


class ResultCollector:
    """Collect NDJSON check output and aggregate summary counts."""

    def __init__(self) -> None:
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.info = 0
        self.blocking_failed = 0

    def emit(self, record: CheckRecord) -> None:
        payload: dict[str, object] = {
            "kind": "check",
            "check": record.check,
            "pass": record.passed,
            "level": record.level,
            "detail": record.detail,
        }
        if record.file is not None:
            payload["file"] = record.file
        if record.line is not None:
            payload["line"] = record.line
        emit_record(payload)
        self.total += 1
        if record.level == "info":
            self.info += 1
        if record.passed:
            self.passed += 1
        else:
            self.failed += 1
            if record.level != "info":
                self.blocking_failed += 1

    def emit_summary(self) -> None:
        emit_record(
            {
                "kind": "summary",
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "info": self.info,
            },
        )


def emit_record(record: dict[str, object]) -> None:
    print(json.dumps(record, ensure_ascii=True))


def load_skill_document(skill_dir: Path) -> SkillDocument:
    """Load SKILL.md and bundled resources from a skill directory."""
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        message = f"SKILL.md not found in {skill_dir}"
        raise SkillLoadError(message)

    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"Unable to read {skill_md_path}: {error}"
        raise SkillLoadError(message) from error

    frontmatter, body, body_start_line = parse_frontmatter(content)
    resource_files = tuple(gather_resource_files(skill_dir))
    return SkillDocument(
        skill_dir=skill_dir,
        skill_md_path=skill_md_path,
        content=content,
        frontmatter=frontmatter,
        body=body,
        body_start_line=body_start_line,
        resource_files=resource_files,
    )


def parse_frontmatter(content: str) -> tuple[dict[str, str], str, int]:
    """Parse simple top-level YAML frontmatter fields from SKILL.md."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content, 1

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, content, 1

    block_lines = lines[1:closing_index]
    frontmatter: dict[str, str] = {}
    for raw_line in block_lines:
        if not raw_line or raw_line.startswith(" "):
            continue
        key, sep, value = raw_line.partition(":")
        if not sep:
            continue
        frontmatter[key.strip()] = strip_quotes(value.strip())

    body = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    body_start_line = closing_index + 2
    return frontmatter, body, body_start_line


def strip_quotes(value: str) -> str:
    """Remove matching surrounding quotes from a simple YAML scalar."""
    if (
        len(value) >= MIN_QUOTED_LENGTH
        and value[0] == value[-1]
        and value[0] in QUOTE_DELIMS
    ):
        return value[1:-1]
    return value


def gather_resource_files(skill_dir: Path) -> list[Path]:
    """Collect bundled resource files under the standard skill directories."""
    files: list[Path] = []
    for directory in RESOURCE_DIRS:
        root = skill_dir / directory
        if not root.exists():
            continue
        files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(files)


def body_line_count(body: str) -> int:
    """Count markdown body lines."""
    return len(body.splitlines())


def relative_links(markdown: str) -> list[MarkdownLink]:
    """Return relative markdown links from a markdown string."""
    pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    matches: list[MarkdownLink] = []
    for match in pattern.finditer(markdown):
        target = match.group(2).strip()
        if not is_relative_target(target):
            continue
        line = markdown.count("\n", 0, match.start()) + 1
        matches.append(MarkdownLink(match.group(1), target, line))
    return matches


def is_relative_target(target: str) -> bool:
    """Return True when the markdown target is local to the skill bundle."""
    lowered = target.lower()
    return not lowered.startswith(EXTERNAL_TARGET_PREFIXES)


def resolve_link_target(skill_dir: Path, target: str) -> Path:
    """Resolve a relative markdown link target against a skill directory."""
    clean_target = target.split("#", 1)[0].split("?", 1)[0]
    return skill_dir / clean_target


def fenced_code_blocks(markdown: str) -> list[CodeBlock]:
    """Extract fenced code blocks with their info string and starting line."""
    pattern = re.compile(r"(?ms)^```([^\n`]*)\n(.*?)^```$")
    blocks: list[CodeBlock] = []
    for match in pattern.finditer(markdown):
        line = markdown.count("\n", 0, match.start()) + 1
        blocks.append(CodeBlock(match.group(1).strip(), match.group(2), line))
    return blocks


def file_relative_to(path: Path, root: Path) -> str:
    """Render a file path relative to the skill root."""
    return str(path.relative_to(root))


def read_text(path: Path) -> str:
    """Read a text file as UTF-8."""
    return path.read_text(encoding="utf-8")
