#!/usr/bin/env python3
"""Extract review comments from staff-code-review markdown.

Parses conventional comments with severity labels and file:line
locations, filters per posting rules, and outputs a JSON array
compatible with the GitHub PR review API comments format.

Usage:
    ./parse_review_comments.py <review_file>
    ./parse_review_comments.py -   # read from stdin

Output (stdout): JSON array of comment objects:
    [{"path": "f.go", "line": 42, "body": "...", "side": "RIGHT"}]

Exit codes:
    0  Success (may output empty array)
    1  Runtime error
    2  Usage/input error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_LABELS: Final[frozenset[str]] = frozenset(
    {"blocking", "issue", "question", "suggestion", "thought", "nit", "praise"},
)

ALWAYS_INCLUDE: Final[frozenset[str]] = frozenset({"blocking", "issue"})
SAMPLED_LIMITS: Final[dict[str, int]] = {"suggestion": 5, "praise": 3}
ALWAYS_EXCLUDE: Final[frozenset[str]] = frozenset({"question", "thought", "nit"})

# ---------------------------------------------------------------------------
# Regex patterns (precompiled)
# ---------------------------------------------------------------------------

# Matches a conventional comment block:
#   **label:** message text (possibly multiline)
#   *Location:* `path/to/file:line`
#
# The message capture is non-greedy and stops at the *Location:* line.
COMMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"\*\*(?P<label>" + "|".join(VALID_LABELS) + r"):\*\*\s*"
    r"(?P<message>.+?)\n"
    r"\s*\*Location:\*\s*`(?P<path>[^`:\s]+):(?P<line>\d+)`",
    re.DOTALL,
)

# Leading ./ in paths
LEADING_DOT_SLASH_RE: Final[re.Pattern[str]] = re.compile(r"^\./")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewComment:
    """Single conventional comment extracted from review markdown."""

    label: str
    message: str
    path: str
    line: int


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_comments(text: str) -> list[ReviewComment]:
    """Extract all conventional comments with location from review markdown."""
    results: list[ReviewComment] = []
    for m in COMMENT_RE.finditer(text):
        path = LEADING_DOT_SLASH_RE.sub("", m.group("path").strip())
        line = int(m.group("line"))
        if line < 1:
            continue
        results.append(
            ReviewComment(
                label=m.group("label"),
                message=m.group("message").strip(),
                path=path,
                line=line,
            ),
        )
    return results


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_comments(comments: list[ReviewComment]) -> list[ReviewComment]:
    """Apply posting rules: all blockers/issues, limited suggestions/praises."""
    result: list[ReviewComment] = []
    counts: dict[str, int] = {}
    for c in comments:
        if c.label in ALWAYS_EXCLUDE:
            continue
        if c.label in ALWAYS_INCLUDE:
            result.append(c)
        elif c.label in SAMPLED_LIMITS:
            current = counts.get(c.label, 0)
            if current < SAMPLED_LIMITS[c.label]:
                result.append(c)
                counts[c.label] = current + 1
    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def to_github_comments(
    comments: list[ReviewComment],
) -> list[dict[str, str | int]]:
    """Convert filtered comments to GitHub review API comment format."""
    seen: set[tuple[str, int, str]] = set()
    result: list[dict[str, str | int]] = []
    for c in comments:
        body = f"**{c.label}:** {c.message}"
        key = (c.path, c.line, body)
        if key in seen:
            continue
        seen.add(key)
        result.append({"path": c.path, "line": c.line, "body": body, "side": "RIGHT"})
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: parse review markdown, output filtered comments."""
    parser = argparse.ArgumentParser(
        description="Extract review comments for GitHub PR review",
    )
    parser.add_argument(
        "review_file",
        help="Path to review markdown file (or - for stdin)",
    )
    args = parser.parse_args(argv)

    if args.review_file == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.review_file)
        if not path.is_file():
            print(f"Error: file not found: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")

    comments = parse_comments(text)
    filtered = filter_comments(comments)
    github_comments = to_github_comments(filtered)
    json.dump(github_comments, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
