#!/usr/bin/env python3
"""Heuristic, language-agnostic code-smell scan for refactoring targets.

Purpose:
    Give the refactoring council concrete, located evidence before the personas
    review. These are deliberately coarse structural heuristics - the personas
    and the reading of actual code do the real diagnosis. The scan exists to
    point attention, not to be authoritative.

Checks:
    SM-long-file       - file exceeds a line-count budget (Large Class / Bloater).
    SM-long-function   - a function/method span exceeds a line budget (Long Method).
    SM-long-params     - a function signature has too many parameters.
    SM-deep-nesting    - indentation depth proxy for tangled conditionals.
    SM-todo-marker     - TODO/FIXME/HACK/XXX debt markers.

Function-length and parameter checks are best-effort: brace-matched for C-family
languages and indentation-based for Python; other languages get file-level checks
only. Treat results as leads, never as ground truth.

Usage:
    smell_scan.py PATH [PATH ...] [--max-file-lines 400] [--max-function-lines 50]
                  [--max-params 5] [--max-nesting 4] [--top 0] [--human]

    PATH                 Files or directories to scan.
    --max-file-lines     Long-file threshold (default: 400).
    --max-function-lines Long-function threshold (default: 50).
    --max-params         Long-parameter-list threshold (default: 5).
    --max-nesting        Deep-nesting depth threshold (default: 4).
    --top                Keep only the N highest-severity findings (0 = all).
    --human              Print a readable summary to stderr instead of NDJSON.

Output:
    NDJSON on stdout: one FindingRecord per line (sorted by file, line), then one
    SummaryRecord. With --human: a readable report on stderr, nothing on stdout.

Exit codes:
    0  scan ran (with or without findings).
    2  usage error (no readable path given).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_MAX_FILE_LINES: Final[int] = 400
DEFAULT_MAX_FUNCTION_LINES: Final[int] = 50
DEFAULT_MAX_PARAMS: Final[int] = 5
DEFAULT_MAX_NESTING: Final[int] = 4
MAX_FILE_BYTES: Final[int] = 2_000_000
SIGNATURE_LOOKAHEAD_LINES: Final[int] = 6
EVIDENCE_SNIPPET_LEN: Final[int] = 80
DEFAULT_INDENT_UNIT: Final[int] = 4
HIGH_NESTING_MARGIN: Final[int] = 2
HIGH_PARAMS_MARGIN: Final[int] = 3
UNKNOWN_SEVERITY_RANK: Final[int] = 3

CHECK_LONG_FILE: Final[str] = "SM-long-file"
CHECK_LONG_FUNCTION: Final[str] = "SM-long-function"
CHECK_LONG_PARAMS: Final[str] = "SM-long-params"
CHECK_DEEP_NESTING: Final[str] = "SM-deep-nesting"
CHECK_TODO: Final[str] = "SM-todo-marker"

SEVERITY_RANK: Final[dict[str, int]] = {"high": 0, "medium": 1, "low": 2}

BRACE_EXTS: Final[frozenset[str]] = frozenset(
    {".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h", ".cpp", ".cc", ".cxx",
     ".hpp", ".hh", ".cs", ".go", ".rs", ".kt", ".kts", ".swift", ".php",
     ".scala", ".m", ".mm"},
)
PYTHON_EXTS: Final[frozenset[str]] = frozenset({".py", ".pyi"})
SOURCE_EXTS: Final[frozenset[str]] = BRACE_EXTS | PYTHON_EXTS | frozenset(
    {".rb", ".ex", ".exs", ".lua", ".pl", ".sh", ".bash", ".zsh"},
)

SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {".git", "node_modules", "vendor", "dist", "build", "target", ".venv",
     "venv", "__pycache__", ".mypy_cache", ".tox", "out", "bin", "obj",
     ".next", ".nuxt", "coverage", ".gradle"},
)

# Function-signature start, brace languages. Captures the name for evidence.
BRACE_FUNC_RE: Final[re.Pattern[str]] = re.compile(
    r"""^\s*
        (?:(?:export|public|private|protected|internal|static|final|async|
            func|fn|fun|def|function|override|virtual|inline|const|pub)\s+)*
        (?:[\w<>\[\],.*&:?]+\s+)?      # optional return type
        (?P<name>[A-Za-z_]\w*)\s*
        \(                            # opening paren of the param list
    """,
    re.VERBOSE,
)
PY_FUNC_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<indent>\s*)def\s+(?P<name>\w+)\s*\(",
)
TODO_RE: Final[re.Pattern[str]] = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
KEYWORD_CALL_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(if|for|while|switch|catch|return|throw|else|elif|with|do)\b",
)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    """A single located smell finding, emitted as one NDJSON record."""

    file: str
    line: int
    check: str
    severity: str
    message: str
    evidence: str

    def sort_key(self) -> tuple[str, int, int]:
        """Stable ordering key: file, then line, then severity."""
        rank = SEVERITY_RANK.get(self.severity, UNKNOWN_SEVERITY_RANK)
        return (self.file, self.line, rank)

    def as_record(self) -> dict[str, object]:
        """Render the finding as an NDJSON FindingRecord dict."""
        return {
            "kind": "finding",
            "file": self.file,
            "line": self.line,
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }


# --------------------------------------------------------------------------- #
# File discovery
# --------------------------------------------------------------------------- #


def discover(paths: list[str]) -> list[Path]:
    """Expand the given files/directories into a sorted list of source files."""
    found: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            found.add(p)
        elif p.is_dir():
            for child in p.rglob("*"):
                if (
                    child.is_file()
                    and not _skipped(child)
                    and child.suffix in SOURCE_EXTS
                ):
                    found.add(child)
    return sorted(found)


def _skipped(path: Path) -> bool:
    """Return True if any path component is a build/vendor directory."""
    return any(part in SKIP_DIRS for part in path.parts)


def read_lines(path: Path) -> list[str] | None:
    """Read a file's lines, or None if it is too large or unreadable."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# Sanitizing (strip comments/strings so braces and commas are real)
# --------------------------------------------------------------------------- #


def strip_noise(line: str) -> str:
    """Remove line comments and string/char literal contents (heuristic)."""
    out: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        nxt = line[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            break
        if ch == "#" and out[-1:] != ["$"]:
            break
        if ch in "\"'`":
            quote = ch
            i += 1
            while i < n:
                if line[i] == "\\":
                    i += 2
                    continue
                if line[i] == quote:
                    i += 1
                    break
                i += 1
            out.append('""')
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


def check_long_file(rel: str, lines: list[str], threshold: int) -> list[Finding]:
    """Flag files whose line count exceeds the budget (Large Class)."""
    loc = len(lines)
    if loc <= threshold:
        return []
    severity = "high" if loc > threshold * 2 else "medium"
    return [
        Finding(
            rel, 1, CHECK_LONG_FILE, severity,
            f"File is {loc} lines (> {threshold}) - candidate Large Class / split",
            f"loc={loc} threshold={threshold}",
        ),
    ]


def check_todos(rel: str, lines: list[str]) -> list[Finding]:
    """Flag TODO/FIXME/HACK/XXX debt markers."""
    out: list[Finding] = []
    for idx, line in enumerate(lines, start=1):
        m = TODO_RE.search(line)
        if m:
            out.append(
                Finding(
                    rel, idx, CHECK_TODO, "low",
                    f"Debt marker: {m.group(1)}",
                    f"L{idx}: {line.strip()[:EVIDENCE_SNIPPET_LEN]}",
                ),
            )
    return out


def infer_indent_unit(lines: list[str]) -> int:
    """Guess the file's indentation width from the smallest positive indent."""
    widths: set[int] = set()
    for line in lines:
        stripped = line.lstrip(" ")
        spaces = len(line) - len(stripped)
        if spaces and stripped:
            widths.add(spaces)
    positives = sorted(w for w in widths if w > 0)
    return positives[0] if positives else DEFAULT_INDENT_UNIT


def check_deep_nesting(rel: str, lines: list[str], threshold: int) -> list[Finding]:
    """Flag the deepest indentation as a proxy for tangled conditionals."""
    unit = infer_indent_unit(lines)
    worst_depth = 0
    worst_line = 0
    for idx, line in enumerate(lines, start=1):
        stripped = line.lstrip(" \t")
        if not stripped:
            continue
        leading = line[: len(line) - len(stripped)]
        spaces = leading.replace("\t", " " * unit).count(" ")
        depth = spaces // unit
        if depth > worst_depth:
            worst_depth = depth
            worst_line = idx
    if worst_depth <= threshold:
        return []
    severity = "high" if worst_depth >= threshold + HIGH_NESTING_MARGIN else "medium"
    return [
        Finding(
            rel, worst_line, CHECK_DEEP_NESTING, severity,
            f"Nesting depth ~{worst_depth} (> {threshold}) - tangled conditionals",
            f"L{worst_line} depth~{worst_depth} unit={unit}",
        ),
    ]


def count_top_level_commas(text: str) -> int:
    """Count commas at bracket depth zero (parameter separators)."""
    depth = 0
    commas = 0
    for ch in text:
        if ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            commas += 1
    return commas


def extract_param_text(lines: list[str], start: int) -> str | None:
    """Return the text inside the first (...) at/after line `start`."""
    depth = 0
    started = False
    collected: list[str] = []
    for offset in range(min(SIGNATURE_LOOKAHEAD_LINES, len(lines) - start)):
        clean = strip_noise(lines[start + offset])
        for ch in clean:
            if ch == "(":
                depth += 1
                started = True
                if depth == 1:
                    continue
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return "".join(collected)
            if started and depth >= 1:
                collected.append(ch)
    return None


def check_params(
    rel: str,
    lines: list[str],
    idx: int,
    name: str,
    threshold: int,
) -> Finding | None:
    """Flag a function signature with more than `threshold` parameters."""
    inner = extract_param_text(lines, idx)
    if inner is None:
        return None
    inner = inner.strip()
    if not inner:
        return None
    params = count_top_level_commas(inner) + 1
    if params <= threshold:
        return None
    severity = "high" if params >= threshold + HIGH_PARAMS_MARGIN else "medium"
    return Finding(
        rel, idx + 1, CHECK_LONG_PARAMS, severity,
        f"'{name}' takes {params} parameters (> {threshold}) - Long Parameter List",
        f"L{idx + 1} params={params}",
    )


def brace_function_span(lines: list[str], start: int) -> int | None:
    """Return the line span of the brace-language function starting at `start`."""
    depth = 0
    opened = False
    for offset in range(len(lines) - start):
        clean = strip_noise(lines[start + offset])
        for ch in clean:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return offset + 1
        if opened and depth <= 0 and offset > 0:
            return offset + 1
    return None


def python_function_span(lines: list[str], start: int, indent: str) -> int:
    """Return the line span of the Python function starting at `start`."""
    base = len(indent)
    end = start
    for offset in range(1, len(lines) - start):
        line = lines[start + offset]
        if not line.strip():
            continue
        leading = len(line) - len(line.lstrip(" \t"))
        if leading <= base:
            break
        end = start + offset
    return end - start + 1


def _long_function_finding(
    rel: str,
    idx: int,
    name: str,
    span: int,
    max_fn: int,
) -> Finding:
    """Build a Long Method finding for a function exceeding the budget."""
    severity = "high" if span > max_fn * 2 else "medium"
    return Finding(
        rel, idx + 1, CHECK_LONG_FUNCTION, severity,
        f"'{name}' spans ~{span} lines (> {max_fn}) - Long Method",
        f"L{idx + 1} span~{span}",
    )


def check_brace_functions(
    rel: str,
    lines: list[str],
    max_fn: int,
    max_params: int,
) -> list[Finding]:
    """Find long functions and long parameter lists in brace languages."""
    out: list[Finding] = []
    for idx, line in enumerate(lines):
        clean = strip_noise(line)
        if "(" not in clean or KEYWORD_CALL_RE.match(clean):
            continue
        m = BRACE_FUNC_RE.match(clean)
        if not m:
            continue
        name = m.group("name")
        param_finding = check_params(rel, lines, idx, name, max_params)
        if param_finding:
            out.append(param_finding)
        span = brace_function_span(lines, idx)
        if span and span > max_fn:
            out.append(_long_function_finding(rel, idx, name, span, max_fn))
    return out


def check_python_functions(
    rel: str,
    lines: list[str],
    max_fn: int,
    max_params: int,
) -> list[Finding]:
    """Find long functions and long parameter lists in Python."""
    out: list[Finding] = []
    for idx, line in enumerate(lines):
        m = PY_FUNC_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        param_finding = check_params(rel, lines, idx, name, max_params)
        if param_finding:
            out.append(param_finding)
        span = python_function_span(lines, idx, m.group("indent"))
        if span > max_fn:
            out.append(_long_function_finding(rel, idx, name, span, max_fn))
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def scan_file(path: Path, args: argparse.Namespace) -> list[Finding]:
    """Run every applicable check against a single file."""
    lines = read_lines(path)
    if lines is None:
        return []
    rel = path.as_posix()
    findings = check_long_file(rel, lines, args.max_file_lines)
    findings += check_deep_nesting(rel, lines, args.max_nesting)
    findings += check_todos(rel, lines)
    if path.suffix in BRACE_EXTS:
        findings += check_brace_functions(
            rel, lines, args.max_function_lines, args.max_params,
        )
    elif path.suffix in PYTHON_EXTS:
        findings += check_python_functions(
            rel, lines, args.max_function_lines, args.max_params,
        )
    return findings


def emit(record: dict[str, object]) -> None:
    """Write one compact NDJSON record to stdout."""
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")


def emit_ndjson(findings: list[Finding], files: int) -> None:
    """Emit each finding then a summary record with per-check counts."""
    by_check: dict[str, int] = {}
    for f in findings:
        emit(f.as_record())
        by_check[f.check] = by_check.get(f.check, 0) + 1
    summary: dict[str, object] = {
        "kind": "summary", "total": len(findings), "files": files,
    }
    summary.update({k: by_check[k] for k in sorted(by_check)})
    emit(summary)


def emit_human(findings: list[Finding], files: int) -> None:
    """Print a readable findings list to stderr."""
    out = sys.stderr
    out.write(f"\nScanned {files} file(s), {len(findings)} finding(s):\n")
    for f in findings:
        out.write(
            f"  [{f.severity:<6}] {f.check:<17} {f.file}:{f.line}  {f.message}\n",
        )
    out.write("\n")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Heuristic code-smell scan.")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan.")
    parser.add_argument("--max-file-lines", type=int, default=DEFAULT_MAX_FILE_LINES)
    parser.add_argument(
        "--max-function-lines", type=int, default=DEFAULT_MAX_FUNCTION_LINES,
    )
    parser.add_argument("--max-params", type=int, default=DEFAULT_MAX_PARAMS)
    parser.add_argument("--max-nesting", type=int, default=DEFAULT_MAX_NESTING)
    parser.add_argument(
        "--top", type=int, default=0, help="Keep N highest-severity findings (0=all).",
    )
    parser.add_argument("--human", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Discover files, run checks, and emit findings."""
    args = parse_args(argv)
    files = discover(args.paths)
    if not files:
        sys.stderr.write("smell_scan: no readable source files in given path(s)\n")
        return 2
    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path, args))
    findings.sort(key=Finding.sort_key)
    if args.top > 0:
        ranked = sorted(
            findings,
            key=lambda f: (
                SEVERITY_RANK.get(f.severity, UNKNOWN_SEVERITY_RANK), f.file, f.line,
            ),
        )
        keep = {id(f) for f in ranked[: args.top]}
        findings = [f for f in findings if id(f) in keep]
    if args.human:
        emit_human(findings, len(files))
    else:
        emit_ndjson(findings, len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
