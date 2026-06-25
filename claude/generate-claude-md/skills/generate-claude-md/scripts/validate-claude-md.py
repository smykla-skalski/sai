#!/usr/bin/env python3
"""Validate a generated CLAUDE.md against the lean, high-signal rubric.

Purpose:
    Deterministic gate for the generate-claude-md skill. After synthesis, the
    skill runs this over the candidate file and revises until every critical
    check passes. The checks mirror the same best-practices the review-claude-md
    plugin audits against (Anthropic docs + empirical studies) - including all of
    its Critical checks - so a file that passes here cannot earn a review FAIL.

Checks:
    GC-file-exists      - target CLAUDE.md exists and is non-empty (gate).
    GC-line-count       - file within the line limit (<=150, matches review C2).
    GC-readme-dup       - leading lines not copied from README.
    GC-generic-advice   - no advice Claude already knows ("write clean code").
    GC-directory-tree   - no ASCII directory tree / file-by-file enumeration.
    GC-long-code-block  - no fenced block over the snippet budget (pointers win).
    GC-bullets-ratio    - structured as bullets, not prose paragraphs.
    GC-build-command    - a build command is present (mirrors review has-build).
    GC-test-command     - a test command is present (mirrors review has-test).
    GC-lint-command     - a lint command is present (mirrors review has-lint).
    GC-precommit        - a pre-commit gate is documented (review has-precommit).
    GC-file-pointers    - uses file or file:line pointers (advisory).
    GC-emphasis         - IMPORTANT / YOU MUST used sparingly (advisory).

    GC-build/test/lint/precommit skip for AGENTS.md bridge files (@import first
    line), whose commands live in the imported file.

Usage:
    validate-claude-md.py PATH [--max-lines 150] [--human]

    PATH         CLAUDE.md file, or a repo root containing CLAUDE.md.
    --max-lines  Line limit; over it fails GC-line-count (default: 150).
    --human      Print a readable summary to stderr instead of NDJSON.

Output:
    NDJSON on stdout: one CheckRecord per line (stable check order), then one
    SummaryRecord. With --human: a readable report on stderr, nothing on stdout.

Exit codes:
    0  all checks passed (info/skip allowed).
    1  one or more checks failed.
    2  usage error (no readable path given).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_MAX_LINES: Final[int] = 150
MAX_FILE_BYTES: Final[int] = 1_000_000
MAX_CODE_BLOCK_LINES: Final[int] = 10
README_OVERLAP_LINES: Final[int] = 5
README_OVERLAP_FAIL: Final[int] = 3
MIN_BULLET_RATIO: Final[int] = 60
PARAGRAPH_RUN: Final[int] = 3
TREE_LINE_THRESHOLD: Final[int] = 4
EMPHASIS_BUDGET: Final[int] = 5
DETAIL_SNIPPET_LEN: Final[int] = 80
PERCENT: Final[int] = 100

CHECK_FILE_EXISTS: Final[str] = "GC-file-exists"
CHECK_LINE_COUNT: Final[str] = "GC-line-count"
CHECK_README_DUP: Final[str] = "GC-readme-dup"
CHECK_GENERIC: Final[str] = "GC-generic-advice"
CHECK_TREE: Final[str] = "GC-directory-tree"
CHECK_LONG_BLOCK: Final[str] = "GC-long-code-block"
CHECK_BULLETS: Final[str] = "GC-bullets-ratio"
CHECK_BUILD: Final[str] = "GC-build-command"
CHECK_TEST: Final[str] = "GC-test-command"
CHECK_LINT: Final[str] = "GC-lint-command"
CHECK_PRECOMMIT: Final[str] = "GC-precommit"
CHECK_POINTERS: Final[str] = "GC-file-pointers"
CHECK_EMPHASIS: Final[str] = "GC-emphasis"

# Stable output order.
CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_FILE_EXISTS,
    CHECK_LINE_COUNT,
    CHECK_README_DUP,
    CHECK_GENERIC,
    CHECK_TREE,
    CHECK_LONG_BLOCK,
    CHECK_BULLETS,
    CHECK_BUILD,
    CHECK_TEST,
    CHECK_LINT,
    CHECK_PRECOMMIT,
    CHECK_POINTERS,
    CHECK_EMPHASIS,
)

# Map check IDs to the review-claude-md rubric tier they enforce.
CHECK_TIER: Final[dict[str, str]] = {
    CHECK_LINE_COUNT: "C2",
    CHECK_README_DUP: "C4",
    CHECK_GENERIC: "C3",
    CHECK_LONG_BLOCK: "I7",
    CHECK_BULLETS: "I6",
    CHECK_BUILD: "C1",
    CHECK_TEST: "C1",
    CHECK_LINT: "C1",
    CHECK_PRECOMMIT: "I5",
    CHECK_POINTERS: "I7",
}

# Generic advice Claude already knows; case-insensitive substring match.
GENERIC_PATTERNS: Final[tuple[str, ...]] = (
    "write clean code",
    "handle errors gracefully",
    "follow best practices",
    "use best practices",
    "always add tests",
    "keep code dry",
    "use meaningful names",
    "use descriptive variable names",
    "write readable code",
    "comment your code",
    "ensure code quality",
    "make sure to test",
)

# Result levels (string values are the NDJSON contract; names avoid S105).
LEVEL_OK: Final[str] = "pass"
LEVEL_FAIL: Final[str] = "fail"
LEVEL_INFO: Final[str] = "info"
LEVEL_SKIP: Final[str] = "skip"

FENCE_RE: Final[re.Pattern[str]] = re.compile(r"^\s*```")
HEADING_RE: Final[re.Pattern[str]] = re.compile(r"^#{1,6}\s")
BULLET_RE: Final[re.Pattern[str]] = re.compile(r"^\s*([-*+]|\d+\.)\s")
TABLE_ROW_RE: Final[re.Pattern[str]] = re.compile(r"^\s*\|.*\|\s*$")
TREE_CHARS_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(?:[│├└─]+|[|`+]\s?--)")
DIR_ENTRY_RE: Final[re.Pattern[str]] = re.compile(r"^\s*[\w.\-]+/(?:\s{2,}\S.*)?\s*$")
IMPORT_RE: Final[re.Pattern[str]] = re.compile(r"^@\S")
POINTER_RE: Final[re.Pattern[str]] = re.compile(
    r"`[^`]*?(?:[\w./\-]+\."
    r"(?:py|ts|tsx|js|jsx|go|rs|rb|java|kt|c|h|cpp|md|ya?ml|toml|json|sh)"
    r"(?::\d+)?|[\w\-]+/[\w./\-]+)[^`]*?`",
)
EMPHASIS_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:IMPORTANT|YOU MUST|NEVER|ALWAYS|CRITICAL)\b",
)

# Command-family detectors. These mirror review-claude-md's validate-commands.sh
# so the two plugins agree on what counts as a build/test/lint/pre-commit command.
BUILD_RE: Final[re.Pattern[str]] = re.compile(
    r"npm run build|cargo build|go build|mvn |gradle |bazel build",
    re.IGNORECASE,
)
MAKE_RE: Final[re.Pattern[str]] = re.compile(r"(?:^|[|;&`])\s*make\b", re.MULTILINE)
TEST_RE: Final[re.Pattern[str]] = re.compile(
    r"npm test|pytest|cargo test|go test|jest|vitest|make test|yarn test|bun test",
    re.IGNORECASE,
)
LINT_RE: Final[re.Pattern[str]] = re.compile(
    r"eslint|biome|ruff|golangci-lint|clippy|prettier|make lint|yarn lint|npm run lint",
    re.IGNORECASE,
)
PRECOMMIT_RE: Final[re.Pattern[str]] = re.compile(
    r"pre-commit|precommit|before commit|commit checklist|before pushing|pre commit",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


@dataclass
class CheckRecord:
    """One validation result, emitted as a CheckRecord NDJSON line."""

    check: str
    level: str
    detail: str
    tier: str | None = None

    @property
    def passed(self) -> bool:
        """Return True unless the check failed."""
        return self.level != LEVEL_FAIL

    def to_json(self) -> str:
        """Serialize to a single NDJSON line with stable key order."""
        obj: dict[str, object] = {
            "kind": "check",
            "check": self.check,
            "pass": self.passed,
            "level": self.level,
        }
        if self.tier:
            obj["tier"] = self.tier
        obj["detail"] = self.detail
        return json.dumps(obj, ensure_ascii=False)


def ok(check: str, detail: str) -> CheckRecord:
    """Build a passing record."""
    return CheckRecord(check, LEVEL_OK, detail, CHECK_TIER.get(check))


def fail(check: str, detail: str) -> CheckRecord:
    """Build a failing record."""
    return CheckRecord(check, LEVEL_FAIL, detail, CHECK_TIER.get(check))


def info(check: str, detail: str) -> CheckRecord:
    """Build an advisory record that never fails the run."""
    return CheckRecord(check, LEVEL_INFO, detail, CHECK_TIER.get(check))


def skip(check: str, detail: str) -> CheckRecord:
    """Build a skipped record for an unmet precondition."""
    return CheckRecord(check, LEVEL_SKIP, detail, CHECK_TIER.get(check))


@dataclass
class Document:
    """Parsed CLAUDE.md plus its repo context."""

    path: Path
    text: str = ""
    lines: list[str] = field(default_factory=list)
    readme: str | None = None

    @property
    def line_count(self) -> int:
        """Return the newline count, matching review-claude-md's `wc -l`."""
        return self.text.count("\n")


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #


def read_text(path: Path) -> str:
    """Read a file as UTF-8 with replacement for invalid bytes."""
    return path.read_text(encoding="utf-8", errors="replace")


def code_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start_line, body_line_count) for each fenced block (1-based)."""
    blocks: list[tuple[int, int]] = []
    in_block = False
    start = 0
    body = 0
    for idx, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            if in_block:
                blocks.append((start, body))
                in_block = False
            else:
                in_block = True
                start = idx
                body = 0
        elif in_block:
            body += 1
    return blocks


def in_code_spans(lines: list[str]) -> list[bool]:
    """Mark each line True if it sits inside a fenced code block."""
    flags: list[bool] = []
    in_block = False
    for line in lines:
        if FENCE_RE.match(line):
            flags.append(True)
            in_block = not in_block
        else:
            flags.append(in_block)
    return flags


def truncate(text: str, limit: int = DETAIL_SNIPPET_LEN) -> str:
    """Trim a snippet to a fixed length for compact detail messages."""
    return text[:limit]


def is_bridge(lines: list[str]) -> bool:
    """Return True if the file bridges an AGENTS.md via an @import first line."""
    for line in lines:
        if not line.strip():
            continue
        return bool(IMPORT_RE.match(line.strip()))
    return False


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


def check_line_count(doc: Document, max_lines: int) -> CheckRecord:
    """Verify the file fits the length budget (matches review-claude-md C2)."""
    n = doc.line_count
    if n <= max_lines:
        return ok(CHECK_LINE_COUNT, f"{n} lines, within the {max_lines}-line limit")
    return fail(
        CHECK_LINE_COUNT,
        f"{n} lines exceeds the {max_lines}-line limit - split into .claude/rules/",
    )


def check_readme_dup(doc: Document) -> CheckRecord:
    """Flag leading lines copy-pasted from the README."""
    if doc.readme is None:
        return skip(CHECK_README_DUP, "No README.md found, duplication check skipped")
    claude_lines = [ln.strip() for ln in doc.lines if ln.strip()][:README_OVERLAP_LINES]
    readme_lines = {ln.strip() for ln in doc.readme.splitlines() if ln.strip()}
    shared = sum(1 for ln in claude_lines if ln in readme_lines)
    total = len(claude_lines)
    if shared >= README_OVERLAP_FAIL:
        return fail(
            CHECK_README_DUP,
            f"{shared}/{total} leading lines copied from README - dedupe vs README",
        )
    return ok(CHECK_README_DUP, f"{shared}/{total} leading lines shared with README")


def check_generic_advice(doc: Document) -> CheckRecord:
    """Flag generic advice that adds no project-specific signal."""
    spans = in_code_spans(doc.lines)
    hits: list[str] = []
    for idx, line in enumerate(doc.lines):
        if spans[idx]:
            continue
        low = line.lower()
        match = next((pat for pat in GENERIC_PATTERNS if pat in low), None)
        if match:
            hits.append(f"L{idx + 1}: '{match}' in \"{truncate(line.strip())}\"")
    if hits:
        return fail(
            CHECK_GENERIC,
            f"{len(hits)} generic-advice line(s) Claude knows - first: {hits[0]}",
        )
    return ok(CHECK_GENERIC, "No generic advice patterns found")


def check_directory_tree(doc: Document) -> CheckRecord:
    """Flag ASCII directory trees and file-by-file enumeration."""
    count = 0
    first_hit = 0
    for idx, line in enumerate(doc.lines, start=1):
        if TREE_CHARS_RE.match(line) or DIR_ENTRY_RE.match(line):
            count += 1
            first_hit = first_hit or idx
    if count >= TREE_LINE_THRESHOLD:
        return fail(
            CHECK_TREE,
            f"{count} tree/enumeration line(s) at L{first_hit} - map, not a listing",
        )
    return ok(CHECK_TREE, "No directory tree or file-by-file enumeration")


def check_long_code_block(doc: Document) -> CheckRecord:
    """Flag fenced blocks larger than the snippet budget."""
    offenders = [b for b in code_blocks(doc.lines) if b[1] > MAX_CODE_BLOCK_LINES]
    if offenders:
        start, body = offenders[0]
        return fail(
            CHECK_LONG_BLOCK,
            f"{len(offenders)} block(s) over {MAX_CODE_BLOCK_LINES} lines - "
            f"first L{start} ({body} lines); use a file:line pointer",
        )
    return ok(CHECK_LONG_BLOCK, f"No code block exceeds {MAX_CODE_BLOCK_LINES} lines")


def count_bullets_and_prose(doc: Document) -> tuple[int, int]:
    """Return (bullet line count, prose line count) outside code blocks."""
    spans = in_code_spans(doc.lines)
    bullets = 0
    prose = 0
    run = 0
    for idx, line in enumerate(doc.lines):
        is_bullet = bool(BULLET_RE.match(line)) and not spans[idx]
        structural = (
            spans[idx]
            or bool(FENCE_RE.match(line))
            or not line.strip()
            or bool(HEADING_RE.match(line))
            or bool(TABLE_ROW_RE.match(line))
            or is_bullet
        )
        if structural:
            if run >= PARAGRAPH_RUN:
                prose += run
            run = 0
            bullets += int(is_bullet)
        else:
            run += 1
    if run >= PARAGRAPH_RUN:
        prose += run
    return bullets, prose


def check_bullets_ratio(doc: Document) -> CheckRecord:
    """Verify content is mostly bullets rather than prose paragraphs."""
    bullets, prose = count_bullets_and_prose(doc)
    total = bullets + prose
    if not total:
        return ok(CHECK_BULLETS, "No prose or bullet content to score")
    ratio = bullets * PERCENT // total
    detail = f"Bullet ratio {ratio}% ({bullets} bullet, {prose} prose lines)"
    if ratio >= MIN_BULLET_RATIO:
        return ok(CHECK_BULLETS, detail)
    return fail(CHECK_BULLETS, f"{detail} - prefer bullets (>={MIN_BULLET_RATIO}%)")


def check_build(doc: Document, *, bridge: bool) -> CheckRecord:
    """Verify a build command is present (mirrors review has-build)."""
    if bridge:
        return skip(CHECK_BUILD, "Bridge file (@import) - commands live in AGENTS.md")
    if BUILD_RE.search(doc.text) or MAKE_RE.search(doc.text):
        return ok(CHECK_BUILD, "Build command found")
    return fail(CHECK_BUILD, "No build command - list the exact build invocation")


def check_test(doc: Document, *, bridge: bool) -> CheckRecord:
    """Verify a test command is present (mirrors review has-test)."""
    if bridge:
        return skip(CHECK_TEST, "Bridge file (@import) - commands live in AGENTS.md")
    if TEST_RE.search(doc.text):
        return ok(CHECK_TEST, "Test command found")
    return fail(CHECK_TEST, "No test command - include a single-test invocation")


def check_lint(doc: Document, *, bridge: bool) -> CheckRecord:
    """Verify a lint command is present (mirrors review has-lint)."""
    if bridge:
        return skip(CHECK_LINT, "Bridge file (@import) - commands live in AGENTS.md")
    if LINT_RE.search(doc.text):
        return ok(CHECK_LINT, "Lint command found")
    return fail(CHECK_LINT, "No lint command - list the linter invocation")


def check_precommit(doc: Document, *, bridge: bool) -> CheckRecord:
    """Verify a pre-commit gate is documented (mirrors review has-precommit)."""
    if bridge:
        return skip(CHECK_PRECOMMIT, "Bridge file (@import) - gate lives in AGENTS.md")
    if PRECOMMIT_RE.search(doc.text):
        return ok(CHECK_PRECOMMIT, "Pre-commit gate documented")
    return fail(CHECK_PRECOMMIT, "No pre-commit gate - name the pre-commit check")


def check_pointers(doc: Document) -> CheckRecord:
    """Report whether the file uses file:line pointers."""
    spans = in_code_spans(doc.lines)
    count = sum(
        len(POINTER_RE.findall(line))
        for idx, line in enumerate(doc.lines)
        if not spans[idx]
    )
    if count:
        return info(CHECK_POINTERS, f"{count} file pointer(s) found - good")
    return info(CHECK_POINTERS, "No file:line pointers - reference exact locations")


def check_emphasis(doc: Document) -> CheckRecord:
    """Report whether emphasis markers stay within budget."""
    spans = in_code_spans(doc.lines)
    count = sum(
        len(EMPHASIS_RE.findall(line))
        for idx, line in enumerate(doc.lines)
        if not spans[idx]
    )
    if count <= EMPHASIS_BUDGET:
        return info(CHECK_EMPHASIS, f"{count} emphasis marker(s), within budget")
    return info(CHECK_EMPHASIS, f"{count} emphasis markers - keep emphasis rare")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def resolve_target(raw: Path) -> Path:
    """Resolve a file or repo root to the CLAUDE.md path to validate."""
    if raw.is_file():
        return raw
    if raw.is_dir():
        candidate = raw / "CLAUDE.md"
        if candidate.is_file():
            return candidate
        nested = raw / ".claude" / "CLAUDE.md"
        if nested.is_file():
            return nested
        return candidate
    return raw


def load_document(target: Path) -> Document | None:
    """Load the target CLAUDE.md and its sibling README, or None if missing."""
    if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
        return None
    text = read_text(target)
    readme = None
    readme_path = target.parent / "README.md"
    if readme_path.is_file() and readme_path.stat().st_size <= MAX_FILE_BYTES:
        readme = read_text(readme_path)
    return Document(path=target, text=text, lines=text.splitlines(), readme=readme)


def run_checks(doc: Document, max_lines: int) -> list[CheckRecord]:
    """Run every check in stable order and return the records."""
    bridge = is_bridge(doc.lines)
    return [
        ok(CHECK_FILE_EXISTS, f"Found '{doc.path.name}' ({doc.line_count} lines)"),
        check_line_count(doc, max_lines),
        check_readme_dup(doc),
        check_generic_advice(doc),
        check_directory_tree(doc),
        check_long_code_block(doc),
        check_bullets_ratio(doc),
        check_build(doc, bridge=bridge),
        check_test(doc, bridge=bridge),
        check_lint(doc, bridge=bridge),
        check_precommit(doc, bridge=bridge),
        check_pointers(doc),
        check_emphasis(doc),
    ]


def summary_record(records: list[CheckRecord]) -> str:
    """Build the trailing SummaryRecord NDJSON line."""
    passed = sum(1 for r in records if r.level == LEVEL_OK)
    failed = sum(1 for r in records if r.level == LEVEL_FAIL)
    skipped = sum(1 for r in records if r.level == LEVEL_SKIP)
    informational = sum(1 for r in records if r.level == LEVEL_INFO)
    obj: dict[str, object] = {
        "kind": "summary",
        "total": len(records),
        "passed": passed,
        "failed": failed,
    }
    if skipped:
        obj["skipped"] = skipped
    if informational:
        obj["info"] = informational
    return json.dumps(obj, ensure_ascii=False)


def emit_ndjson(records: list[CheckRecord]) -> None:
    """Print every record followed by the summary as NDJSON on stdout."""
    for record in records:
        print(record.to_json())
    print(summary_record(records))


def emit_human(records: list[CheckRecord], target: Path) -> None:
    """Print a readable verdict report on stderr."""
    glyph = {
        LEVEL_OK: "PASS",
        LEVEL_FAIL: "FAIL",
        LEVEL_INFO: "INFO",
        LEVEL_SKIP: "SKIP",
    }
    print(f"CLAUDE.md validation: {target}", file=sys.stderr)
    for record in records:
        tier = f" [{record.tier}]" if record.tier else ""
        line = f"  [{glyph[record.level]}]{tier} {record.check}: {record.detail}"
        print(line, file=sys.stderr)
    failed = sum(1 for r in records if r.level == LEVEL_FAIL)
    verdict = "PASS" if failed == 0 else f"FAIL ({failed} failing check(s))"
    print(f"Verdict: {verdict}", file=sys.stderr)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Validate a generated CLAUDE.md")
    parser.add_argument("path", help="CLAUDE.md file or repo root containing it")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--human", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate the target file and emit results; return the exit code."""
    args = parse_args(argv)
    target = resolve_target(Path(args.path))
    if not target.is_file() and not target.parent.is_dir():
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2

    doc = load_document(target)
    if doc is None:
        records = [fail(CHECK_FILE_EXISTS, f"CLAUDE.md not found at '{target}'")]
    else:
        records = run_checks(doc, args.max_lines)

    if args.human:
        emit_human(records, target)
    else:
        emit_ndjson(records)
    return 1 if any(r.level == LEVEL_FAIL for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
