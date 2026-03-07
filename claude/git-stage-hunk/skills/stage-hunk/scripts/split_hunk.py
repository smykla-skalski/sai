#!/usr/bin/env python3
"""Split large git hunks into sub-hunks or select specific lines for staging.

Provides three modes for fine-grained hunk manipulation:

    --find-subhunks  Detect sub-hunks within a parent hunk using fine diff
    --extract-patch  Extract a single sub-hunk as an applicable patch
    --line-select    Build a partial patch from a line range selection

Input is read from stdin. Output is NDJSON to stdout, errors to stderr.

Exit codes:
    0  Success
    1  Runtime error (missing data, invalid range, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HUNK_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
)
PREVIEW_MAX_LEN: Final[int] = 120
NULL_BYTE_SEPARATOR: Final[str] = "\x00"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DiffHunk:
    """A single hunk from a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    body: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_hunk_header(line: str) -> tuple[int, int, int, int] | None:
    """Parse ``@@`` header, return (old_start, old_count, new_start, new_count)."""
    m = HUNK_HEADER_RE.match(line)
    if not m:
        return None
    old_start = int(m.group(1))
    old_count = int(m.group(2)) if m.group(2) is not None else 1
    new_start = int(m.group(3))
    new_count = int(m.group(4)) if m.group(4) is not None else 1
    return old_start, old_count, new_start, new_count


def _extract_file_path(line: str) -> str | None:
    """Extract the b/ file path from a ``diff --git`` line."""
    parts = line.strip().split(" ")
    if len(parts) < 4:  # noqa: PLR2004
        return None
    b_path = parts[-1]
    return b_path.removeprefix("b/")


def _flush_hunk(
    hunks: list[DiffHunk],
    current: DiffHunk | None,
) -> None:
    """Append *current* to *hunks* if it is not ``None``."""
    if current is not None:
        hunks.append(current)


def parse_diff_hunks(diff_text: str, target_file: str) -> list[DiffHunk]:
    """Parse a unified diff and return hunks for *target_file*."""
    hunks: list[DiffHunk] = []
    in_target = False
    current_hunk: DiffHunk | None = None

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            _flush_hunk(hunks, current_hunk)
            current_hunk = None

            file_path = _extract_file_path(line)
            in_target = file_path == target_file
            continue

        if not in_target:
            continue

        if line.startswith(("--- ", "+++ ")):
            continue

        parsed = parse_hunk_header(line)
        if parsed:
            _flush_hunk(hunks, current_hunk)
            old_start, old_count, new_start, new_count = parsed
            current_hunk = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=line.rstrip("\n"),
            )
            continue

        if current_hunk is not None and line and line[0] in (" ", "+", "-", "\\"):
            current_hunk.body.append(line.rstrip("\n"))

    _flush_hunk(hunks, current_hunk)
    return hunks


# ---------------------------------------------------------------------------
# Hunk utilities
# ---------------------------------------------------------------------------


def hunk_preview(body: list[str]) -> str:
    """First ``+`` line (or first ``-`` line) truncated to *PREVIEW_MAX_LEN*."""
    for line in body:
        if line.startswith("+"):
            return line[:PREVIEW_MAX_LEN]
    for line in body:
        if line.startswith("-"):
            return line[:PREVIEW_MAX_LEN]
    return ""


def hunk_in_parent(
    hunk: DiffHunk,
    parent_old_start: int,
    parent_old_count: int,
) -> bool:
    """Check if a fine hunk falls within the parent's old line range."""
    if parent_old_count == 0:
        return False

    if hunk.old_count == 0:
        return (
            hunk.old_start >= parent_old_start
            and hunk.old_start <= parent_old_start + parent_old_count - 1
        )

    h_end = hunk.old_start + hunk.old_count - 1
    p_end = parent_old_start + parent_old_count - 1
    return hunk.old_start >= parent_old_start and h_end <= p_end


def count_changes(body: list[str]) -> tuple[int, int]:
    """Count added and removed lines in a hunk body."""
    added = sum(1 for ln in body if ln.startswith("+"))
    removed = sum(1 for ln in body if ln.startswith("-"))
    return added, removed


# ---------------------------------------------------------------------------
# Patch construction
# ---------------------------------------------------------------------------


def make_patch_header(file_path: str) -> str:
    """Build the ``diff --git`` / ``---`` / ``+++`` header lines."""
    return (
        f"diff --git a/{file_path} b/{file_path}\n"
        f"--- a/{file_path}\n"
        f"+++ b/{file_path}\n"
    )


def make_hunk_patch(file_path: str, hunk: DiffHunk) -> str:
    """Build a complete patch string for a single hunk."""
    lines = [make_patch_header(file_path)]
    lines.append(
        f"@@ -{hunk.old_start},{hunk.old_count} "
        f"+{hunk.new_start},{hunk.new_count} @@\n",
    )
    lines.extend(body_line + "\n" for body_line in hunk.body)
    return "".join(lines)


# -- Mode: --find-subhunks --------------------------------------------------


def cmd_find_subhunks(args: argparse.Namespace) -> None:
    """Find sub-hunks within a parent hunk using fine diff."""
    stdin = sys.stdin.read()
    parts = stdin.split(NULL_BYTE_SEPARATOR)
    if len(parts) < 2:  # noqa: PLR2004
        print(
            json.dumps({"error": "expected two sections separated by null byte"}),
            file=sys.stderr,
        )
        sys.exit(1)

    fine_diff = parts[1]
    fine_hunks = parse_diff_hunks(fine_diff, args.file)

    matching = [
        h
        for h in fine_hunks
        if hunk_in_parent(h, args.old_start, args.old_count)
    ]

    if len(matching) <= 1:
        print(
            json.dumps({
                "parent": args.parent,
                "splittable": False,
                "reason": "single_hunk",
                "suggestion": f"use {args.parent}:START-END for line-level selection",
            }),
        )
        return

    for i, h in enumerate(matching, 1):
        added, removed = count_changes(h.body)
        print(
            json.dumps({
                "id": f"{args.parent}.{i}",
                "parent": args.parent,
                "file": args.file,
                "old_start": h.old_start,
                "old_count": h.old_count,
                "new_start": h.new_start,
                "new_count": h.new_count,
                "added": added,
                "removed": removed,
                "preview": hunk_preview(h.body),
            }),
        )

    print(
        json.dumps({
            "summary": True,
            "parent": args.parent,
            "splittable": True,
            "sub_hunks": len(matching),
        }),
    )


# -- Mode: --extract-patch --------------------------------------------------


def cmd_extract_patch(args: argparse.Namespace) -> None:
    """Extract a single sub-hunk as an applicable patch."""
    fine_diff = sys.stdin.read()
    fine_hunks = parse_diff_hunks(fine_diff, args.file)

    matching = [
        h
        for h in fine_hunks
        if hunk_in_parent(h, args.parent_old_start, args.parent_old_count)
    ]

    idx = args.sub_index
    if idx < 1 or idx > len(matching):
        print(
            json.dumps({
                "error": "sub_hunk_not_found",
                "id": args.id,
                "detail": (
                    f"parent {args.id.split('.')[0]} has {len(matching)} sub-hunks"
                ),
            }),
            file=sys.stderr,
        )
        sys.exit(1)

    hunk = matching[idx - 1]
    sys.stdout.write(make_hunk_patch(args.file, hunk))


# -- Mode: --line-select ----------------------------------------------------


def _parse_line_range(raw: str) -> tuple[int, int]:
    """Parse a ``START-END`` string into a (start, end) tuple."""
    parts = raw.split("-")
    return int(parts[0]), int(parts[1])


def _build_partial_body(
    body: list[str],
    start: int,
    end: int,
) -> tuple[list[str], bool]:
    """Build a filtered body from a line range selection.

    Returns the new body lines and whether any changes were kept.
    """
    new_body: list[str] = []
    has_changes = False

    for i, line in enumerate(body, 1):
        in_range = start <= i <= end

        if line.startswith("+"):
            if in_range:
                new_body.append(line)
                has_changes = True
        elif line.startswith("-"):
            if in_range:
                new_body.append(line)
                has_changes = True
            else:
                new_body.append(" " + line[1:])
        else:
            new_body.append(line)

    return new_body, has_changes


def _recalculate_counts(body: list[str]) -> tuple[int, int]:
    r"""Recalculate old/new counts from a patch body.

    ``\\ No newline`` lines do not count.
    """
    old_count = 0
    new_count = 0
    for ln in body:
        if ln.startswith(" "):
            old_count += 1
            new_count += 1
        elif ln.startswith("-"):
            old_count += 1
        elif ln.startswith("+"):
            new_count += 1
    return old_count, new_count


def cmd_line_select(args: argparse.Namespace) -> None:
    """Build a partial patch from a line range selection."""
    normal_diff = sys.stdin.read()
    all_hunks = parse_diff_hunks(normal_diff, args.file)

    hunk_num = args.hunk_num
    if hunk_num < 1 or hunk_num > len(all_hunks):
        print(
            json.dumps({
                "error": "hunk_not_found",
                "id": args.id,
                "detail": f"file {args.file} has {len(all_hunks)} hunks",
            }),
            file=sys.stderr,
        )
        sys.exit(1)

    hunk = all_hunks[hunk_num - 1]
    body = hunk.body

    start, end = _parse_line_range(args.lines)

    if start < 1 or end > len(body) or start > end:
        print(
            json.dumps({
                "error": "line_range_out_of_bounds",
                "id": args.id,
                "lines": args.lines,
                "max_lines": len(body),
            }),
            file=sys.stderr,
        )
        sys.exit(1)

    if start == 1 and end == len(body):
        print(
            json.dumps({
                "note": "full_hunk_selected",
                "id": args.id,
                "lines": args.lines,
            }),
            file=sys.stderr,
        )
        sys.stdout.write(make_hunk_patch(args.file, hunk))
        return

    new_body, has_changes = _build_partial_body(body, start, end)

    if not has_changes:
        print(
            json.dumps({
                "error": "no_changes_in_range",
                "id": args.id,
                "lines": args.lines,
                "detail": "selected range has no additions or removals",
            }),
            file=sys.stderr,
        )
        sys.exit(1)

    old_count, new_count = _recalculate_counts(new_body)

    patch = make_patch_header(args.file)
    patch += (
        f"@@ -{hunk.old_start},{old_count} "
        f"+{hunk.new_start},{new_count} @@\n"
    )
    for line in new_body:
        patch += line + "\n"

    sys.stdout.write(patch)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and dispatch to the appropriate mode handler."""
    parser = argparse.ArgumentParser(description="Split git hunks into sub-hunks")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--find-subhunks", action="store_true")
    mode_group.add_argument("--extract-patch", action="store_true")
    mode_group.add_argument("--line-select", action="store_true")

    # --find-subhunks args
    parser.add_argument("--parent")
    parser.add_argument("--old-start", type=int)
    parser.add_argument("--old-count", type=int)

    # --extract-patch args
    parser.add_argument("--id")
    parser.add_argument("--parent-old-start", type=int)
    parser.add_argument("--parent-old-count", type=int)
    parser.add_argument("--sub-index", type=int)

    # --line-select args
    parser.add_argument("--hunk-num", type=int)
    parser.add_argument("--lines")

    # Shared
    parser.add_argument("--file")

    args = parser.parse_args()

    if args.find_subhunks:
        for req in ("parent", "old_start", "old_count", "file"):
            if getattr(args, req) is None:
                parser.error(f"--find-subhunks requires --{req.replace('_', '-')}")
        cmd_find_subhunks(args)
    elif args.extract_patch:
        for req in ("id", "parent_old_start", "parent_old_count", "sub_index", "file"):
            if getattr(args, req) is None:
                parser.error(f"--extract-patch requires --{req.replace('_', '-')}")
        cmd_extract_patch(args)
    elif args.line_select:
        for req in ("id", "file", "hunk_num", "lines"):
            if getattr(args, req) is None:
                parser.error(f"--line-select requires --{req.replace('_', '-')}")
        cmd_line_select(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
