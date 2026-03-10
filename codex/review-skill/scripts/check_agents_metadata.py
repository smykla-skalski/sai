#!/usr/bin/env python3
"""Metadata checks for agents/openai.yaml."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import TYPE_CHECKING

from _skill_check_common import (
    CheckRecord,
    ResultCollector,
    load_skill_document,
    read_text,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SHORT_DESCRIPTION_MIN = 25
SHORT_DESCRIPTION_MAX = 64
METADATA_PATH = "agents/openai.yaml"
REQUIRED_INTERFACE_FIELDS = {
    "display_name": "AM-display-name",
    "short_description": "AM-short-description",
    "default_prompt": "AM-default-prompt",
}
QUOTED_VALUE_PATTERN = r'"((?:[^"\\\n]|\\.)+)"'
INTERFACE_FIELD_INDENT = 2
TOOLS_ITEM_INDENT = 4
TOOLS_FIELD_INDENT = 6


def quoted_field(content: str, key: str, *, section: str = "interface") -> str | None:
    """Extract a quoted field value from a named block in openai.yaml."""
    block_lines = _block_lines(content, section, indent=0)
    if block_lines is None:
        return None

    field_prefix = " " * INTERFACE_FIELD_INDENT
    pattern = re.compile(
        rf"^{field_prefix}{re.escape(key)}:\s*{QUOTED_VALUE_PATTERN}\s*$",
    )
    for line in block_lines:
        match = pattern.match(line)
        if match is not None:
            return _decode_double_quoted(match.group(1))
    return None


def _check_present(skill_dir: Path) -> CheckRecord:
    metadata_path = skill_dir / "agents" / "openai.yaml"
    return CheckRecord(
        check="AM-present",
        passed=metadata_path.exists(),
        level="important",
        detail=(
            "agents/openai.yaml is present."
            if metadata_path.exists()
            else "Missing agents/openai.yaml."
        ),
        file=METADATA_PATH,
    )


def _check_required_field(skill_dir: Path, field: str, check_id: str) -> CheckRecord:
    content = _metadata_content(skill_dir)
    value = quoted_field(content, field)
    return CheckRecord(
        check=check_id,
        passed=value is not None,
        level="important",
        detail=(
            f"{field} is present and quoted."
            if value is not None
            else f"{field} is missing or not quoted in agents/openai.yaml."
        ),
        file=METADATA_PATH,
    )


def _check_short_description_length(skill_dir: Path) -> CheckRecord:
    content = _metadata_content(skill_dir)
    value = quoted_field(content, "short_description")
    passed = (
        value is not None
        and SHORT_DESCRIPTION_MIN <= len(value) <= SHORT_DESCRIPTION_MAX
    )
    return CheckRecord(
        check="AM-short-description-length",
        passed=passed,
        level="important",
        detail=(
            "short_description length is within the 25-64 character range."
            if passed
            else "short_description should be 25-64 characters."
        ),
        file=METADATA_PATH,
    )


def _check_default_prompt_skill_ref(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    prompt = quoted_field(_metadata_content(skill_dir), "default_prompt")
    expected = f"${doc.frontmatter.get('name', doc.skill_dir.name)}"
    return CheckRecord(
        check="AM-default-prompt-skill-ref",
        passed=prompt is not None and expected in prompt,
        level="important",
        detail=(
            f"default_prompt names {expected}."
            if prompt is not None and expected in prompt
            else f"default_prompt should explicitly mention {expected}."
        ),
        file=METADATA_PATH,
    )


def _check_policy_allow_implicit_invocation(skill_dir: Path) -> CheckRecord:
    content = _metadata_content(skill_dir)
    if _block_lines(content, "policy", indent=0) is None:
        return CheckRecord(
            check="AM-policy-allow-implicit-invocation",
            passed=True,
            level="info",
            detail="policy block is absent; review implicit invocation manually.",
            file=METADATA_PATH,
        )

    allow_implicit = quoted_bool(
        content,
        "allow_implicit_invocation",
        section="policy",
    )
    passed = allow_implicit is not None
    return CheckRecord(
        check="AM-policy-allow-implicit-invocation",
        passed=passed,
        level="important",
        detail=(
            "allow_implicit_invocation is present and boolean."
            if passed
            else "policy.allow_implicit_invocation must be true or false."
        ),
        file=METADATA_PATH,
    )


def _check_dependencies_shape(skill_dir: Path) -> CheckRecord:
    content = _metadata_content(skill_dir)
    dependencies_block = _block_lines(content, "dependencies", indent=0)
    if dependencies_block is None:
        return CheckRecord(
            check="AM-dependencies-shape",
            passed=True,
            level="info",
            detail="No dependencies block declared.",
            file=METADATA_PATH,
        )

    tools_block = _block_lines_from_lines(dependencies_block, "tools", indent=2)
    passed = tools_block is not None and _tools_block_has_valid_entries(tools_block)
    return CheckRecord(
        check="AM-dependencies-shape",
        passed=passed,
        level="important",
        detail=(
            "dependencies.tools entries declare quoted type and value."
            if passed
            else "dependencies.tools entries need quoted type and value."
        ),
        file=METADATA_PATH,
    )


def _metadata_content(skill_dir: Path) -> str:
    return read_text(skill_dir / "agents" / "openai.yaml")


def quoted_bool(content: str, key: str, *, section: str) -> bool | None:
    """Extract a boolean field value from a named block in openai.yaml."""
    block_lines = _block_lines(content, section, indent=0)
    if block_lines is None:
        return None

    field_prefix = " " * INTERFACE_FIELD_INDENT
    pattern = re.compile(rf"^{field_prefix}{re.escape(key)}:\s*(true|false)\s*$")
    for line in block_lines:
        match = pattern.match(line)
        if match is not None:
            return match.group(1) == "true"
    return None


def _block_lines(content: str, key: str, *, indent: int) -> list[str] | None:
    return _block_lines_from_lines(content.splitlines(), key, indent=indent)


def _block_lines_from_lines(
    lines: list[str],
    key: str,
    *,
    indent: int,
) -> list[str] | None:
    header_re = re.compile(rf"^{' ' * indent}{re.escape(key)}:\s*$")
    for index, line in enumerate(lines):
        if header_re.match(line) is None:
            continue

        block: list[str] = []
        for candidate in lines[index + 1 :]:
            if candidate.strip() and _line_indent(candidate) <= indent:
                break
            block.append(candidate)
        return block
    return None


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _decode_double_quoted(value: str) -> str:
    return re.sub(r'\\(["\\])', r"\1", value)


def _tools_block_has_valid_entries(lines: list[str]) -> bool:
    items = _tool_items(lines)
    return bool(items) and all(_tool_item_has_required_fields(item) for item in items)


def _tool_items(lines: list[str]) -> list[list[str]]:
    items: list[list[str]] = []
    current: list[str] = []
    item_start_re = re.compile(rf"^{' ' * TOOLS_ITEM_INDENT}-(?:\s|$)")

    for line in lines:
        if not line.strip():
            continue
        if item_start_re.match(line):
            if current:
                items.append(current)
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        items.append(current)
    return items


def _tool_item_has_required_fields(lines: list[str]) -> bool:
    item_prefix = " " * TOOLS_ITEM_INDENT
    field_prefix = " " * TOOLS_FIELD_INDENT
    type_re = re.compile(
        (
            rf"^{item_prefix}-\s*type:\s*{QUOTED_VALUE_PATTERN}\s*$"
            rf"|^{field_prefix}type:\s*{QUOTED_VALUE_PATTERN}\s*$"
        ),
    )
    value_re = re.compile(
        (
            rf"^{item_prefix}-\s*value:\s*{QUOTED_VALUE_PATTERN}\s*$"
            rf"|^{field_prefix}value:\s*{QUOTED_VALUE_PATTERN}\s*$"
        ),
    )
    has_type = any(type_re.match(line) is not None for line in lines)
    has_value = any(value_re.match(line) is not None for line in lines)
    return has_type and has_value


def _field_check(field: str, check_id: str) -> Callable[[Path], CheckRecord]:
    def runner(skill_dir: Path) -> CheckRecord:
        return _check_required_field(skill_dir, field, check_id)

    return runner


FIELD_CHECKS: dict[str, Callable[[Path], CheckRecord]] = {
    check_id: _field_check(field, check_id)
    for field, check_id in REQUIRED_INTERFACE_FIELDS.items()
}
CHECKS: dict[str, Callable[[Path], CheckRecord]] = {
    "AM-present": _check_present,
    **FIELD_CHECKS,
    "AM-short-description-length": _check_short_description_length,
    "AM-default-prompt-skill-ref": _check_default_prompt_skill_ref,
    "AM-policy-allow-implicit-invocation": _check_policy_allow_implicit_invocation,
    "AM-dependencies-shape": _check_dependencies_shape,
}


def run_checks(
    skill_dir: Path,
    collector: ResultCollector,
    *,
    selected: set[str] | None = None,
) -> None:
    """Run agents/openai.yaml checks for a skill directory."""
    names = selected or set(CHECKS)
    present_record = _check_present(skill_dir)
    if "AM-present" in names:
        collector.emit(present_record)
    if not present_record.passed:
        return

    for check_id, check_fn in CHECKS.items():
        if check_id == "AM-present":
            continue
        if check_id in names:
            collector.emit(check_fn(skill_dir))


def main(argv: list[str] | None = None) -> int:
    """Run agents/openai.yaml checks as a CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--check", action="append", dest="checks")
    args = parser.parse_args(argv)

    collector = ResultCollector()
    selected = set(args.checks) if args.checks else None
    run_checks(args.skill_dir, collector, selected=selected)
    collector.emit_summary()
    return 1 if collector.blocking_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
