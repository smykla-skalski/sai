#!/usr/bin/env python3
"""Locate the humanize skill's reference files next to this plugin.

Checks the install layouts of every supported agent, nearest ancestor first:

- flat skills directory (opencode, ~/.agents/skills): <skills>/humanize/
- portable checkout and Copilot CLI: <root>/humanize/skills/humanize/
- versioned plugin caches (Claude Code, Codex):
  <root>/humanize/<version>/skills/humanize/ (highest version wins; versions
  Claude Code marked as orphaned after an update or uninstall are skipped)

Only fixed candidate paths are probed; nothing is searched recursively.

Usage:
    find_humanize_refs.py [--skill-dir DIR]

Output (stdout, one NDJSON record):
    {"kind": "humanize-refs", "found": true, "patterns": "...",
     "elements_of_style": "..."}
    {"kind": "humanize-refs", "found": false, "searched": ["..."]}

Unreadable directories count as not found.

Exit codes: 0 lookup ran (found or not), 2 usage error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Final

REFERENCE_FILES: Final[dict[str, str]] = {
    "patterns": "patterns.md",
    "elements_of_style": "elements-of-style.md",
}
MAX_ANCESTORS: Final[int] = 4
VERSION_PART: Final[re.Pattern[str]] = re.compile(r"\d+")
SKILL_SUBPATH: Final[Path] = Path("skills") / "humanize" / "references"
ORPHAN_MARKER: Final[str] = ".orphaned_at"


def version_key(path: Path) -> tuple[int, ...]:
    """Sort key for version directory names such as 2.5.10."""
    return tuple(int(part) for part in VERSION_PART.findall(path.name))


def is_orphaned(version_dir: Path) -> bool:
    """Treat a version dir as orphaned when marked, or when it cannot be read."""
    try:
        return (version_dir / ORPHAN_MARKER).exists()
    except OSError:
        return True


def candidates_under(ancestor: Path) -> list[Path]:
    """Humanize reference directories to probe below one ancestor."""
    plugin_dir = ancestor / "humanize"
    found = [plugin_dir / "references", plugin_dir / SKILL_SUBPATH]
    try:
        children = [child for child in plugin_dir.iterdir() if child.is_dir()]
    except OSError:
        return found
    current = [
        child
        for child in children
        if VERSION_PART.match(child.name) and not is_orphaned(child)
    ]
    found.extend(
        child / SKILL_SUBPATH
        for child in sorted(current, key=version_key, reverse=True)
    )
    return found


def ancestors(skill_dir: Path) -> list[Path]:
    """Logical path first so a symlinked skill finds its siblings, then the real one."""
    starts = [Path(os.path.normpath(skill_dir.absolute())), skill_dir.resolve()]
    ordered: list[Path] = []
    for start in starts:
        for ancestor in list(start.parents)[:MAX_ANCESTORS]:
            if ancestor not in ordered:
                ordered.append(ancestor)
    return ordered


def is_readable_file(path: Path) -> bool:
    """Check that path is a regular file this process can read."""
    return path.is_file() and os.access(path, os.R_OK)


def has_references(directory: Path) -> bool:
    """Check that every reference file exists in directory."""
    try:
        return all(
            is_readable_file(directory / name) for name in REFERENCE_FILES.values()
        )
    except OSError:
        return False


def find_references(skill_dir: Path) -> tuple[Path | None, list[Path]]:
    """Return the first complete reference directory and every probed path."""
    searched: list[Path] = []
    for ancestor in ancestors(skill_dir):
        for candidate in candidates_under(ancestor):
            searched.append(candidate)
            if has_references(candidate):
                return candidate, searched
    return None, searched


def main(argv: list[str] | None = None) -> int:
    """Run the lookup and print one NDJSON record."""
    parser = argparse.ArgumentParser(description="Locate humanize reference files")
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=Path(__file__).absolute().parent.parent,
        help="staff-code-review skill directory (default: this script's parent)",
    )
    args = parser.parse_args(argv)
    try:
        valid = args.skill_dir.absolute().is_dir()
    except OSError:
        valid = False
    if not valid:
        print(f"error: not a directory: {args.skill_dir}", file=sys.stderr)
        return 2

    directory, searched = find_references(args.skill_dir)
    if directory is None:
        record: dict[str, object] = {
            "kind": "humanize-refs",
            "found": False,
            "searched": [str(path) for path in searched],
        }
    else:
        record = {"kind": "humanize-refs", "found": True}
        for key, name in REFERENCE_FILES.items():
            record[key] = str((directory / name).resolve())
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
