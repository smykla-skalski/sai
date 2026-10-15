#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["skills-ref==0.1.1"]
# ///
"""Validate portable skills against the Agent Skills spec, tolerating Claude-only keys.

'agentskills validate' (skills-ref) hard-codes six frontmatter fields and rejects
every other key. Claude Code reads 'argument-hint', 'user-invocable' and similar
keys only at the top level of SKILL.md, so they cannot move under the spec's
'metadata' map. This script removes the Claude-only keys listed in
CLAUDE_ONLY_KEYS (the ones documented in .claude/rules/skill-authoring.md) from
the parsed frontmatter, then runs the skills-ref validator on the rest. Any
other unknown key, a bad name, a name that differs from the directory and every
other spec violation still fail with the validator's message. SKILL.md files are
never modified.

Usage:
    scripts/validate_skills.py [SKILL_DIR_OR_SKILL_MD ...]

It needs uv on PATH. Without arguments it validates every 'plugins/*/skills/*'
directory of the repository. Run it with
'uv run --quiet --script scripts/validate_skills.py' when the executable bit is
not honored.

Output:
    'Valid skill: <path>' on stdout per valid skill.
    'Validation failed for <path>:' and one '  - <message>' line per error on stderr.

Exit codes:
    0  every skill is valid
    1  at least one skill has validation errors
    2  usage error (no skills found)

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Final

from skills_ref.errors import ParseError
from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate_metadata

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
SKILLS_GLOB: Final[str] = "plugins/*/skills/*"
SKILL_FILE_NAME: Final[str] = "SKILL.md"

CLAUDE_ONLY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "agent",
        "argument-hint",
        "context",
        "disable-model-invocation",
        "hooks",
        "model",
        "user-invocable",
    },
)

EXIT_OK: Final[int] = 0
EXIT_INVALID: Final[int] = 1
EXIT_USAGE: Final[int] = 2


def without_claude_only_keys(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Return the frontmatter minus the keys only Claude Code reads."""
    return {
        key: value for key, value in frontmatter.items() if key not in CLAUDE_ONLY_KEYS
    }


def resolve_skill_dir(path: Path) -> Path:
    """Map a SKILL.md file path to its skill directory, leave directories alone."""
    if path.is_file() and path.name.lower() == SKILL_FILE_NAME.lower():
        return path.parent
    return path


def discover_skill_dirs(root: Path) -> list[Path]:
    """List every skill directory under 'plugins/*/skills/*' in sorted order."""
    return sorted(path for path in root.glob(SKILLS_GLOB) if path.is_dir())


def display_path(path: Path) -> Path:
    """Show repository paths relative to the repository root."""
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def validate_skill(skill_dir: Path) -> list[str]:
    """Return the validation errors for one skill directory; empty means valid."""
    if not skill_dir.exists():
        return [f"Path does not exist: {skill_dir}"]
    if not skill_dir.is_dir():
        return [f"Not a directory: {skill_dir}"]

    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return [f"Missing required file: {SKILL_FILE_NAME}"]

    try:
        content = skill_md.read_text(encoding="utf-8")
        frontmatter, _ = parse_frontmatter(content)
    except UnicodeDecodeError as error:
        return [f"{SKILL_FILE_NAME} is not valid UTF-8: {error}"]
    except ParseError as error:
        return [str(error)]

    return validate_metadata(without_claude_only_keys(frontmatter), skill_dir)


def main(argv: list[str] | None = None) -> int:
    """Validate the given skills, or every repository skill when none are given."""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        skill_dirs = [resolve_skill_dir(Path(argument)) for argument in arguments]
    else:
        skill_dirs = discover_skill_dirs(REPO_ROOT)
        if not skill_dirs:
            print(f"No skills found under {REPO_ROOT / SKILLS_GLOB}", file=sys.stderr)
            return EXIT_USAGE

    failed = 0
    for skill_dir in skill_dirs:
        errors = validate_skill(skill_dir)
        if errors:
            failed += 1
            print(f"Validation failed for {display_path(skill_dir)}:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"Valid skill: {display_path(skill_dir)}")

    if failed:
        print(f"{failed} of {len(skill_dirs)} skill(s) failed", file=sys.stderr)
        return EXIT_INVALID
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
