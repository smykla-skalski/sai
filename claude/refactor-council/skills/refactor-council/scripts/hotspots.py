#!/usr/bin/env python3
"""Rank refactoring hotspots from git history (behavioral code analysis).

Purpose:
    Implement Adam Tornhill's hotspot heuristic: the code most worth refactoring
    is where high complexity meets high change frequency. This script mines the
    git log for per-file change frequency (churn), pairs it with a size proxy for
    complexity, and ranks the result. It also surfaces change/temporal coupling
    (files that repeatedly change together).

Checks:
    HS-hotspot   - per-file hotspot score = churn x loc, ranked.
    HS-coupling  - file pairs that change together above a support/degree threshold.

Usage:
    hotspots.py [PATH ...] [--since 12.month] [--top 20] [--min-churn 2]
                [--max-files-per-commit 30] [--coupling-min 0.4]
                [--coupling-support 3] [--human]

    PATH        Optional path prefixes to scope the scan (default: whole repo).
    --since     git log --since value (default: 12.month).
    --top       Max hotspots / coupling pairs to emit (default: 20).
    --min-churn Ignore files changed fewer than this many times (default: 2).
    --max-files-per-commit
                Commits touching more files than this are excluded from coupling
                (bulk renames / formatting passes skew co-change). Default: 30.
    --coupling-min
                Minimum coupling degree (co-changes / min(churn_a, churn_b)) to
                report a pair (default: 0.4).
    --coupling-support
                Minimum number of shared commits to report a pair (default: 3).
    --human     Print a human-readable table to stderr instead of NDJSON.

Output:
    NDJSON on stdout: one FindingRecord per line, then one SummaryRecord.
    With --human: a ranked table on stderr, nothing on stdout.

Exit codes:
    0  ran successfully (hotspots reported or none found).
    2  usage error, git unavailable, or not inside a git work tree.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, NoReturn

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

GIT_EXECUTABLE: Final[str] = shutil.which("git") or "git"
GIT_TIMEOUT_S: Final[int] = 60
DEFAULT_SINCE: Final[str] = "12.month"
DEFAULT_TOP: Final[int] = 20
DEFAULT_MIN_CHURN: Final[int] = 2
DEFAULT_MAX_FILES_PER_COMMIT: Final[int] = 30
DEFAULT_COUPLING_MIN: Final[float] = 0.4
DEFAULT_COUPLING_SUPPORT: Final[int] = 3
MAX_FILE_BYTES: Final[int] = 40_000_000

MIN_PAIR_FILES: Final[int] = 2
SEVERITY_HIGH_RATIO: Final[float] = 0.34
SEVERITY_MEDIUM_RATIO: Final[float] = 0.67
STRONG_COUPLING_DEGREE: Final[float] = 0.7

CHECK_HOTSPOT: Final[str] = "HS-hotspot"
CHECK_COUPLING: Final[str] = "HS-coupling"

# Files we never treat as refactoring targets even if they churn.
IGNORED_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        ".lock", ".sum", ".min.js", ".min.css", ".map", ".svg", ".png", ".jpg",
        ".jpeg", ".gif", ".ico", ".pdf", ".gz", ".zip", ".woff", ".woff2", ".ttf",
    },
)
IGNORED_NAMES: Final[frozenset[str]] = frozenset(
    {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum",
        "Cargo.lock", "poetry.lock",
    },
)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@dataclass
class FileStat:
    """Change/size statistics for a single tracked file."""

    path: str
    churn: int = 0
    loc: int = 0

    @property
    def score(self) -> int:
        """Hotspot score: change frequency multiplied by size proxy."""
        return self.churn * self.loc


@dataclass
class History:
    """Aggregated per-file churn and per-pair co-change counts."""

    files: dict[str, FileStat] = field(default_factory=dict)
    pair_commits: dict[tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int),
    )


# --------------------------------------------------------------------------- #
# Git
# --------------------------------------------------------------------------- #


def run_git(args: list[str]) -> str:
    """Run a git subcommand with a fixed argument list and return stdout."""
    try:
        result = subprocess.run(
            [GIT_EXECUTABLE, *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError:
        fail("git executable not found on PATH")
    except subprocess.TimeoutExpired:
        fail(f"git {' '.join(args)} timed out after {GIT_TIMEOUT_S}s")
    if result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def repo_root() -> Path:
    """Return the git work-tree root (git paths are relative to it)."""
    try:
        result = subprocess.run(
            [GIT_EXECUTABLE, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        fail("git is required and must run inside a git work tree")
    root = result.stdout.strip()
    if result.returncode != 0 or not root:
        fail("not inside a git work tree (hotspot analysis needs git history)")
    return Path(root)


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #


def is_ignored(path: str) -> bool:
    """Return True for lockfiles, binaries, and generated assets."""
    name = path.rsplit("/", 1)[-1]
    if name in IGNORED_NAMES:
        return True
    lower = path.lower()
    return any(lower.endswith(suffix) for suffix in IGNORED_SUFFIXES)


def in_scope(path: str, scopes: tuple[str, ...]) -> bool:
    """Return True if path is under one of the requested scope prefixes."""
    if not scopes:
        return True
    return any(path == s or path.startswith(s.rstrip("/") + "/") for s in scopes)


def count_loc(path: str, root: Path) -> int:
    """Count current lines in a file, resolved against the repo root."""
    file_path = root / path
    if not file_path.is_file():
        return 0
    try:
        if file_path.stat().st_size > MAX_FILE_BYTES:
            return 0
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def split_commits(raw: str) -> list[list[str]]:
    """Split `git log` name-only output into per-commit file lists."""
    commits: list[list[str]] = []
    current: list[str] = []
    for line in raw.splitlines():
        if line.startswith("\x01"):
            commits.append(current)
            current = []
        elif line.strip():
            current.append(line.strip())
    commits.append(current)
    return commits


def fold_commit(
    history: History,
    files: list[str],
    scopes: tuple[str, ...],
    max_files_per_commit: int,
) -> None:
    """Fold one commit's file list into churn and co-change counts."""
    scoped = [f for f in files if not is_ignored(f) and in_scope(f, scopes)]
    for f in scoped:
        stat = history.files.get(f)
        if stat is None:
            stat = FileStat(path=f)
            history.files[f] = stat
        stat.churn += 1
    if not MIN_PAIR_FILES <= len(scoped) <= max_files_per_commit:
        return
    ordered = sorted(set(scoped))
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            history.pair_commits[(ordered[i], ordered[j])] += 1


def collect_history(
    scopes: tuple[str, ...],
    since: str,
    max_files_per_commit: int,
    root: Path,
) -> History:
    """Build per-file churn and per-pair co-change counts from the git log."""
    raw = run_git(
        ["log", f"--since={since}", "--no-merges", "--name-only", "--format=%x01%H"],
    )
    history = History()
    for files in split_commits(raw):
        fold_commit(history, files, scopes, max_files_per_commit)
    for stat in history.files.values():
        stat.loc = count_loc(stat.path, root)
    return history


def rank_hotspots(history: History, min_churn: int, top: int) -> list[FileStat]:
    """Return the top files ranked by hotspot score (churn x loc)."""
    candidates = [
        s for s in history.files.values() if s.churn >= min_churn and s.loc > 0
    ]
    candidates.sort(key=lambda s: (-s.score, -s.churn, s.path))
    return candidates[:top]


def rank_coupling(
    history: History,
    support: int,
    degree_min: float,
    top: int,
) -> list[tuple[str, str, int, float]]:
    """Return the top file pairs by change-coupling degree."""
    out: list[tuple[str, str, int, float]] = []
    for (a, b), shared in history.pair_commits.items():
        if shared < support:
            continue
        denom = min(history.files[a].churn, history.files[b].churn)
        if denom == 0:
            continue
        degree = shared / denom
        if degree < degree_min:
            continue
        out.append((a, b, shared, round(degree, 2)))
    out.sort(key=lambda t: (-t[3], -t[2], t[0], t[1]))
    return out[:top]


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def severity_for_rank(rank: int, total: int) -> str:
    """Map a 0-based rank within the hotspot list to a severity band."""
    if total <= 1:
        return "high"
    ratio = rank / total
    if ratio < SEVERITY_HIGH_RATIO:
        return "high"
    if ratio < SEVERITY_MEDIUM_RATIO:
        return "medium"
    return "low"


def emit(record: dict[str, object]) -> None:
    """Write one compact NDJSON record to stdout."""
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")


def emit_ndjson(
    hotspots: list[FileStat],
    coupling: list[tuple[str, str, int, float]],
) -> None:
    """Emit hotspot and coupling findings followed by a summary record."""
    for rank, stat in enumerate(hotspots):
        emit(
            {
                "kind": "finding",
                "file": stat.path,
                "line": 1,
                "check": CHECK_HOTSPOT,
                "severity": severity_for_rank(rank, len(hotspots)),
                "message": (
                    f"Hotspot: changed {stat.churn}x, {stat.loc} loc "
                    f"(score {stat.score})"
                ),
                "evidence": f"churn={stat.churn} loc={stat.loc} rank={rank + 1}",
            },
        )
    for a, b, shared, degree in coupling:
        emit(
            {
                "kind": "finding",
                "file": a,
                "line": 1,
                "check": CHECK_COUPLING,
                "severity": "medium" if degree >= STRONG_COUPLING_DEGREE else "low",
                "message": (
                    f"Change coupling with '{b}': {shared} shared commits "
                    f"(degree {degree})"
                ),
                "evidence": f"pair={a}|{b} shared={shared} degree={degree}",
            },
        )
    emit(
        {
            "kind": "summary",
            "total": len(hotspots) + len(coupling),
            "hotspots": len(hotspots),
            "coupling_pairs": len(coupling),
        },
    )


def emit_human(
    hotspots: list[FileStat],
    coupling: list[tuple[str, str, int, float]],
) -> None:
    """Print a readable hotspot/coupling table to stderr."""
    out = sys.stderr
    out.write("\nHotspots (churn x loc):\n")
    if not hotspots:
        out.write("  (none above thresholds)\n")
    for rank, stat in enumerate(hotspots, start=1):
        out.write(
            f"  {rank:>3}. {stat.score:>9}  churn={stat.churn:<4} "
            f"loc={stat.loc:<6} {stat.path}\n",
        )
    out.write("\nChange coupling (files that change together):\n")
    if not coupling:
        out.write("  (none above thresholds)\n")
    for a, b, shared, degree in coupling:
        out.write(f"  degree={degree:<4} shared={shared:<3} {a}  <->  {b}\n")
    out.write("\n")


# --------------------------------------------------------------------------- #
# Errors / CLI
# --------------------------------------------------------------------------- #


def fail(message: str) -> NoReturn:
    """Print a diagnostic to stderr and exit with the usage-error code."""
    sys.stderr.write(f"hotspots: {message}\n")
    raise SystemExit(2)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rank refactoring hotspots from git history.",
    )
    parser.add_argument(
        "paths", nargs="*", help="Path prefixes to scope (default: whole repo).",
    )
    parser.add_argument("--since", default=DEFAULT_SINCE)
    parser.add_argument("--top", type=int, default=DEFAULT_TOP)
    parser.add_argument("--min-churn", type=int, default=DEFAULT_MIN_CHURN)
    parser.add_argument(
        "--max-files-per-commit", type=int, default=DEFAULT_MAX_FILES_PER_COMMIT,
    )
    parser.add_argument("--coupling-min", type=float, default=DEFAULT_COUPLING_MIN)
    parser.add_argument(
        "--coupling-support", type=int, default=DEFAULT_COUPLING_SUPPORT,
    )
    parser.add_argument("--human", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Collect history, rank hotspots and coupling, then emit results."""
    args = parse_args(argv)
    if args.top <= 0:
        fail("--top must be positive")
    root = repo_root()
    history = collect_history(
        tuple(args.paths), args.since, args.max_files_per_commit, root,
    )
    hotspots = rank_hotspots(history, args.min_churn, args.top)
    coupling = rank_coupling(
        history, args.coupling_support, args.coupling_min, args.top,
    )
    if args.human:
        emit_human(hotspots, coupling)
    else:
        emit_ndjson(hotspots, coupling)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
