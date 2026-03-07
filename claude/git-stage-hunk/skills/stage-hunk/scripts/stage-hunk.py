#!/usr/bin/env python3
"""Non-interactive hunk staging for selective git add without TTY.

Usage:
    ./stage-hunk.py --check-deps
    ./stage-hunk.py --list [--table] [--fallback]
    ./stage-hunk.py --list --file PATH [--table] [--fallback]
    ./stage-hunk.py --list --split [--table] [--fallback]
    ./stage-hunk.py --split H3 [--fallback]
    ./stage-hunk.py --hunk H1,H2 [--dry-run] [--table] [--fallback]
    ./stage-hunk.py --hunk H3.1,H3.2 [--dry-run] [--table] [--fallback]
    ./stage-hunk.py --hunk H3:5-10 [--dry-run] [--table] [--fallback]
    ./stage-hunk.py --pattern REGEX [--dry-run] [--table]
    ./stage-hunk.py --file PATH [--dry-run] [--table] [--fallback]
    ./stage-hunk.py --range FILE:START-END [--dry-run] [--table]
    ./stage-hunk.py --verify [--table]

Modes:
    --check-deps         Check required dependencies, output JSON status
    --list               List all unstaged hunks with IDs and previews
    --list --file PATH   Filter listing to specific file(s) (comma-separated)
    --list --split       List all hunks with sub-hunk breakdown
    --split H3           Show sub-hunks for one specific hunk
    --hunk H1,H2,...     Stage specific hunks by global sequential ID
    --hunk H3.1,H3.2    Stage sub-hunks by dot-notation ID
    --hunk H3:5-10       Stage hunk-relative lines within a hunk
    --pattern REGEX      Stage hunks matching regex (requires patchutils)
    --file PATH          Stage all hunks for file(s) (comma-separated)
    --range FILE:S-E     Stage hunks overlapping line range (requires patchutils)
    --verify             Show staged vs unstaged summary

Flags:
    --table              Output as markdown table instead of NDJSON
    --dry-run            Preview staging without applying
    --fallback           Force fallback mode (no patchutils)

Output: NDJSON (one JSON object per line), final line always a summary.
        With --table, output is a pre-formatted markdown table.

Exit codes:
    0  Success
    1  Runtime error
    2  Usage error
    3  Missing dependency (patchutils) -- only from --check-deps

Dependencies: git, python3
Optional:     patchutils (lsdiff, filterdiff, grepdiff)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Import from split_hunk (same directory)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_hunk import (
    count_changes,
    hunk_in_parent,
    hunk_preview,
    make_hunk_patch,
    make_patch_header,
    parse_diff_hunks,
)

# -- Constants ---------------------------------------------------------------

EXIT_OK: Final[int] = 0
EXIT_RUNTIME: Final[int] = 1
EXIT_USAGE: Final[int] = 2
EXIT_MISSING_DEP: Final[int] = 3
PREVIEW_TRUNCATE: Final[int] = 50
HUNK_ID_PLAIN_RE: Final[re.Pattern[str]] = re.compile(r"^H\d+$")
HUNK_ID_SUB_RE: Final[re.Pattern[str]] = re.compile(r"^H\d+\.\d+$")
HUNK_ID_LINE_RE: Final[re.Pattern[str]] = re.compile(r"^H\d+:\d+-\d+$")
DIFF_GIT_RE: Final[re.Pattern[str]] = re.compile(r"^diff --git a/(.*) b/")

# -- Data model --------------------------------------------------------------


@dataclass
class HunkEntry:
    """A hunk in the global index."""

    id: str
    file: str
    hunk_num: int
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: int
    removed: int
    preview: str


@dataclass
class StageResult:
    """Result of staging a single hunk."""

    id: str
    file: str
    action: str
    status: str
    detail: str = ""


@dataclass
class ParsedArgs:
    """Validated CLI arguments."""

    mode: str
    split_target: str = ""
    hunk_ids: str = ""
    pattern: str = ""
    file_paths: str = ""
    file_filter: str = ""
    range_spec: str = ""
    table: bool = False
    dry_run: bool = False
    fallback: bool = False


# -- Subprocess helpers -------------------------------------------------------


def run_git(
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=check,
    )


def get_diff() -> str:
    """Get the full unstaged diff."""
    return run_git("diff", check=False).stdout


def get_fine_diff() -> str:
    """Get a zero-context diff for fine-grained hunk splitting."""
    return run_git(
        "diff", "--inter-hunk-context=0", "--unified=0", check=False,
    ).stdout


def has_patchutils() -> bool:
    """Check if patchutils (lsdiff + filterdiff) are available."""
    return (
        shutil.which("lsdiff") is not None
        and shutil.which("filterdiff") is not None
    )


def _run_patchutils_cmd(cmd: list[str], input_text: str) -> str:
    """Run a patchutils command with diff text on stdin."""
    return subprocess.run(  # noqa: S603
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def run_lsdiff(diff_text: str) -> list[str]:
    """List files in a diff using lsdiff --strip=1."""
    output = _run_patchutils_cmd(["lsdiff", "--strip=1"], diff_text)
    return [f for f in output.splitlines() if f]


def run_filterdiff(
    diff_text: str,
    file_path: str,
    *,
    hunks: str = "",
    lines: str = "",
) -> str:
    """Extract hunks for a file using filterdiff."""
    cmd = ["filterdiff", "-i", f"a/{file_path}"]
    if hunks:
        cmd.extend(["--hunks", hunks])
    if lines:
        cmd.append(f"--lines={lines}")
    return _run_patchutils_cmd(cmd, diff_text)


def run_grepdiff(diff_text: str, pattern: str) -> str:
    """Find hunks matching a regex using grepdiff."""
    return _run_patchutils_cmd(
        ["grepdiff", "-E", pattern, "--output-matching=hunk"],
        diff_text,
    )


# -- JSON/table output helpers -----------------------------------------------


def emit(obj: str) -> None:
    """Emit one NDJSON line to stdout."""
    print(obj)


def die(msg: str, code: int = EXIT_RUNTIME) -> None:
    """Print JSON error to stderr and exit."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(code)


def table_list_header() -> None:
    """Print the list mode table header."""
    print("| ID | File | Lines | +/- | Preview |")
    print("|:---|:-----|:------|:----|:--------|")


def table_list_row(entry: HunkEntry) -> str:
    """Format a list mode table row."""
    end = entry.new_start + entry.new_count - 1
    pm = f"+{entry.added}/-{entry.removed}"
    preview = entry.preview[:PREVIEW_TRUNCATE]
    return f"| {entry.id} | {entry.file} | {entry.new_start}-{end} | {pm} | {preview} |"


def table_stage_header() -> None:
    """Print the stage mode table header."""
    print("| ID | File | Status |")
    print("|:---|:-----|:-------|")


def table_stage_row(result: StageResult) -> str:
    """Format a stage mode table row."""
    label = {"ok": "ok", "dry_run": "dry_run", "error": "FAILED"}.get(
        result.status, result.status,
    )
    return f"| {result.id} | {result.file} | {label} |"


def table_verify_header() -> None:
    """Print the verify mode table header."""
    print("| File | Staged | Unstaged |")
    print("|:-----|:-------|:---------|")


# -- Fallback diff extraction -------------------------------------------------


def _extract_file_diff_fallback(diff_text: str, target_file: str) -> str:
    """Extract the diff section for a single file without patchutils."""
    result: list[str] = []
    found = False

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if found:
                break
            m = DIFF_GIT_RE.match(line)
            if m and m.group(1) == target_file:
                found = True
        if found:
            result.append(line)

    return "".join(result)


def _list_files_from_diff(diff_text: str) -> list[str]:
    """Extract sorted file list from diff text without patchutils."""
    files: set[str] = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            m = DIFF_GIT_RE.match(line)
            if m:
                files.add(m.group(1))
    return sorted(files)


def _is_binary_file(diff_text: str, file_path: str) -> bool:
    """Check if a file is binary in the diff."""
    return any(
        "Binary files" in line and file_path in line
        for line in diff_text.splitlines()
    )


# -- Hunk index builder -------------------------------------------------------


def _get_file_diff(
    diff_text: str,
    file_path: str,
    *,
    use_patchutils: bool,
) -> str:
    """Get the diff for a single file."""
    if use_patchutils:
        return run_filterdiff(diff_text, file_path)
    return _extract_file_diff_fallback(diff_text, file_path)


def build_hunk_index(
    diff_text: str,
    *,
    use_patchutils: bool,
) -> list[HunkEntry]:
    """Build a global hunk index with sequential IDs.

    IDs are assigned by alphabetical file order, then by position within
    each file.
    """
    files = (
        sorted(run_lsdiff(diff_text))
        if use_patchutils
        else _list_files_from_diff(diff_text)
    )

    entries: list[HunkEntry] = []
    hunk_id = 0

    for file_path in files:
        if _is_binary_file(diff_text, file_path):
            continue

        file_diff = _get_file_diff(
            diff_text, file_path, use_patchutils=use_patchutils,
        )
        if not file_diff:
            continue

        for hunk_num, hunk in enumerate(
            parse_diff_hunks(file_diff, file_path), 1,
        ):
            hunk_id += 1
            added, removed = count_changes(hunk.body)
            entries.append(
                HunkEntry(
                    id=f"H{hunk_id}",
                    file=file_path,
                    hunk_num=hunk_num,
                    old_start=hunk.old_start,
                    old_count=hunk.old_count,
                    new_start=hunk.new_start,
                    new_count=hunk.new_count,
                    added=added,
                    removed=removed,
                    preview=hunk_preview(hunk.body),
                ),
            )

    return entries


# -- File filter ---------------------------------------------------------------


def filter_by_files(
    index: list[HunkEntry],
    file_filter: str,
) -> list[HunkEntry]:
    """Filter hunk index to entries matching comma-separated file paths."""
    filter_files = {f.strip() for f in file_filter.split(",")}
    return [e for e in index if e.file in filter_files]


# -- Staging logic -------------------------------------------------------------


def extract_hunk_patch(
    diff_text: str,
    file_path: str,
    hunk_num: int,
    *,
    use_patchutils: bool,
) -> str:
    """Extract a single hunk patch suitable for git apply."""
    if use_patchutils:
        return run_filterdiff(diff_text, file_path, hunks=str(hunk_num))

    file_diff = _extract_file_diff_fallback(diff_text, file_path)
    if not file_diff:
        return ""

    file_hunks = parse_diff_hunks(file_diff, file_path)
    if hunk_num < 1 or hunk_num > len(file_hunks):
        return ""

    return make_hunk_patch(file_path, file_hunks[hunk_num - 1])


def apply_patch(patch: str, extra_flags: str = "") -> tuple[bool, str]:
    """Apply a patch to the index. Returns (success, stderr)."""
    if not patch:
        return False, "empty patch"

    cmd = ["git", "apply", "--cached"]
    if extra_flags:
        cmd.append(extra_flags)

    result = subprocess.run(  # noqa: S603
        cmd, input=patch, capture_output=True, text=True, check=False,
    )
    return result.returncode == 0, result.stderr


def _stage_file_entries_dry_run(
    file_entries: list[HunkEntry],
) -> tuple[int, list[StageResult]]:
    """Dry-run staging for a file's entries."""
    results = [
        StageResult(
            id=entry.id, file=entry.file,
            action="would_stage", status="dry_run",
        )
        for entry in file_entries
    ]
    return len(file_entries), results


def _stage_file_entries_bulk(
    diff_text: str,
    file_path: str,
    file_entries: list[HunkEntry],
) -> tuple[bool, int, list[StageResult]]:
    """Try bulk staging via filterdiff. Returns (success, ok_count, results)."""
    hunk_nums = ",".join(str(e.hunk_num) for e in file_entries)
    bulk_patch = run_filterdiff(diff_text, file_path, hunks=hunk_nums)
    if not bulk_patch:
        return False, 0, []

    success, _stderr = apply_patch(bulk_patch)
    if not success:
        return False, 0, []

    results = [
        StageResult(
            id=entry.id, file=entry.file,
            action="staged", status="ok",
        )
        for entry in file_entries
    ]
    return True, len(file_entries), results


def _stage_file_entries_individual(
    diff_text: str,
    file_entries: list[HunkEntry],
    *,
    use_patchutils: bool,
) -> tuple[int, int, list[StageResult]]:
    """Stage entries one at a time. Returns (ok, fail, results)."""
    ok_count = 0
    fail_count = 0
    results: list[StageResult] = []

    for entry in file_entries:
        hunk_patch = extract_hunk_patch(
            diff_text, entry.file, entry.hunk_num,
            use_patchutils=use_patchutils,
        )
        success, stderr = apply_patch(hunk_patch)
        if success:
            results.append(
                StageResult(
                    id=entry.id, file=entry.file,
                    action="staged", status="ok",
                ),
            )
            ok_count += 1
        else:
            if "index.lock" in stderr:
                emit(json.dumps({"error": "index_locked", "detail": stderr}))
            results.append(
                StageResult(
                    id=entry.id, file=entry.file,
                    action="stage_failed", status="error", detail=stderr,
                ),
            )
            fail_count += 1

    return ok_count, fail_count, results


def stage_hunks(
    entries: list[HunkEntry],
    diff_text: str,
    *,
    use_patchutils: bool,
    dry_run: bool,
) -> tuple[int, int, list[StageResult]]:
    """Stage a list of hunk entries. Returns (ok, fail, results)."""
    ok_count = 0
    fail_count = 0
    all_results: list[StageResult] = []

    files_grouped: dict[str, list[HunkEntry]] = {}
    for entry in entries:
        files_grouped.setdefault(entry.file, []).append(entry)

    for file_path in sorted(files_grouped):
        file_entries = files_grouped[file_path]

        if dry_run:
            ok, results = _stage_file_entries_dry_run(file_entries)
            ok_count += ok
            all_results.extend(results)
            continue

        # Try bulk apply (patchutils only)
        bulk_ok = False
        if use_patchutils:
            bulk_ok, ok, results = _stage_file_entries_bulk(
                diff_text, file_path, file_entries,
            )
            if bulk_ok:
                ok_count += ok
                all_results.extend(results)

        if not bulk_ok:
            ok, fail, results = _stage_file_entries_individual(
                diff_text, file_entries, use_patchutils=use_patchutils,
            )
            ok_count += ok
            fail_count += fail
            all_results.extend(results)

    return ok_count, fail_count, all_results


@dataclass
class _StageOutcome:
    """Aggregated staging outcome for output emission."""

    results: list[StageResult]
    ok_count: int
    fail_count: int
    total_hunks: int


def emit_stage_results(
    outcome: _StageOutcome,
    *,
    table: bool,
    dry_run: bool,
    fallback: bool,
) -> None:
    """Emit staging results as NDJSON or table."""
    if table:
        if outcome.results:
            table_stage_header()
            for r in outcome.results:
                print(table_stage_row(r))
            print()
            print(f"{outcome.ok_count} staged, {outcome.fail_count} failed")
    else:
        for r in outcome.results:
            obj: dict[str, object] = {
                "id": r.id, "file": r.file,
                "action": r.action, "status": r.status,
            }
            if r.detail:
                obj["detail"] = r.detail
            emit(json.dumps(obj))
        emit(json.dumps({
            "summary": True, "total_hunks": outcome.total_hunks,
            "staged": outcome.ok_count, "failed": outcome.fail_count,
            "dry_run": dry_run, "fallback": fallback,
        }))


# -- Map matched hunks to global IDs ------------------------------------------


def _map_to_global_ids(
    matched_index: list[HunkEntry],
    global_index: list[HunkEntry],
) -> list[HunkEntry]:
    """Map matched hunks back to global index entries by file + old_start."""
    result: list[HunkEntry] = []
    for matched in matched_index:
        for entry in global_index:
            if entry.file == matched.file and entry.old_start == matched.old_start:
                result.append(entry)
                break
    return result


# -- Entry lookup --------------------------------------------------------------


def _find_entry(index: list[HunkEntry], hunk_id: str) -> HunkEntry | None:
    """Find a hunk entry by exact ID match."""
    for entry in index:
        if entry.id == hunk_id:
            return entry
    return None


# -- Mode handlers -------------------------------------------------------------


def mode_check_deps() -> None:
    """Check required dependencies, output JSON status."""
    if shutil.which("git"):
        emit('{"dep":"git","found":true}')
    else:
        emit(
            '{"dep":"git","found":false,'
            '"install":"Install git from https://git-scm.com"}',
        )

    if shutil.which("python3"):
        emit('{"dep":"python3","found":true}')
    else:
        emit('{"dep":"python3","found":false,"install":"Install Python 3"}')

    if has_patchutils():
        emit('{"dep":"patchutils","found":true}')
    else:
        emit(
            '{"dep":"patchutils","found":false,'
            '"install":"brew install patchutils (macOS) '
            'or apt install patchutils (Debian/Ubuntu)"}',
        )
        sys.exit(EXIT_MISSING_DEP)


def mode_list(
    index: list[HunkEntry],
    total_hunks: int,
    *,
    table: bool,
    fallback: bool,
) -> None:
    """List all unstaged hunks with IDs and previews."""
    if table:
        table_list_header()
        files_seen: set[str] = set()
        for entry in index:
            print(table_list_row(entry))
            files_seen.add(entry.file)
        print()
        print(f"{len(index)} hunks across {len(files_seen)} files")
    else:
        for entry in index:
            emit(json.dumps({
                "id": entry.id, "file": entry.file,
                "hunk_num": entry.hunk_num,
                "old_start": entry.old_start, "old_count": entry.old_count,
                "new_start": entry.new_start, "new_count": entry.new_count,
                "added": entry.added, "removed": entry.removed,
                "preview": entry.preview,
            }))
        emit(json.dumps({
            "summary": True, "total_hunks": total_hunks,
            "mode": "list", "fallback": fallback,
        }))


def mode_split(
    index: list[HunkEntry],
    target: str,
    total_hunks: int,
) -> None:
    """Show sub-hunks for one specific hunk."""
    parent = _find_entry(index, target)
    if not parent:
        emit(json.dumps({
            "error": "invalid_hunk_id", "id": target,
            "valid_range": f"H1-H{total_hunks}",
        }))
        sys.exit(EXIT_RUNTIME)

    fine_diff = get_fine_diff()
    fine_hunks = parse_diff_hunks(fine_diff, parent.file)
    matching = [
        h for h in fine_hunks
        if hunk_in_parent(h, parent.old_start, parent.old_count)
    ]

    if len(matching) <= 1:
        emit(json.dumps({
            "parent": parent.id, "splittable": False,
            "reason": "single_hunk",
            "suggestion": f"use {parent.id}:START-END for line-level selection",
        }))
        return

    for i, h in enumerate(matching, 1):
        added, removed = count_changes(h.body)
        emit(json.dumps({
            "id": f"{parent.id}.{i}", "parent": parent.id,
            "file": parent.file,
            "old_start": h.old_start, "old_count": h.old_count,
            "new_start": h.new_start, "new_count": h.new_count,
            "added": added, "removed": removed,
            "preview": hunk_preview(h.body),
        }))

    emit(json.dumps({
        "summary": True, "parent": parent.id,
        "splittable": True, "sub_hunks": len(matching),
    }))


def _emit_list_split_entry_table(
    entry: HunkEntry,
    matching: list[object],
    files_seen: set[str],
) -> None:
    """Emit one entry for list-split mode in table format."""
    from split_hunk import DiffHunk  # noqa: PLC0415

    is_splittable = len(matching) > 1

    if is_splittable:
        print(table_list_row(entry))
    else:
        row_entry = HunkEntry(
            id=entry.id, file=entry.file, hunk_num=entry.hunk_num,
            old_start=entry.old_start, old_count=entry.old_count,
            new_start=entry.new_start, new_count=entry.new_count,
            added=entry.added, removed=entry.removed,
            preview="(not splittable)",
        )
        print(table_list_row(row_entry))
    files_seen.add(entry.file)

    if is_splittable:
        for i, h in enumerate(matching, 1):
            if not isinstance(h, DiffHunk):
                continue
            added, removed = count_changes(h.body)
            sub = HunkEntry(
                id=f"  {entry.id}.{i}", file=entry.file, hunk_num=i,
                old_start=h.old_start, old_count=h.old_count,
                new_start=h.new_start, new_count=h.new_count,
                added=added, removed=removed,
                preview=hunk_preview(h.body),
            )
            print(table_list_row(sub))


def _emit_list_split_entry_ndjson(
    entry: HunkEntry,
    matching: list[object],
) -> None:
    """Emit one entry for list-split mode in NDJSON format."""
    from split_hunk import DiffHunk  # noqa: PLC0415

    is_splittable = len(matching) > 1
    obj: dict[str, object] = {
        "id": entry.id, "file": entry.file,
        "hunk_num": entry.hunk_num,
        "old_start": entry.old_start, "old_count": entry.old_count,
        "new_start": entry.new_start, "new_count": entry.new_count,
        "added": entry.added, "removed": entry.removed,
        "preview": entry.preview,
        "splittable": is_splittable,
        "sub_hunks": len(matching) if is_splittable else 0,
    }
    emit(json.dumps(obj))

    if is_splittable:
        for i, h in enumerate(matching, 1):
            if not isinstance(h, DiffHunk):
                continue
            added, removed = count_changes(h.body)
            emit(json.dumps({
                "id": f"{entry.id}.{i}", "parent": entry.id,
                "file": entry.file,
                "old_start": h.old_start, "old_count": h.old_count,
                "new_start": h.new_start, "new_count": h.new_count,
                "added": added, "removed": removed,
                "preview": hunk_preview(h.body),
            }))


def mode_list_split(
    index: list[HunkEntry],
    total_hunks: int,
    *,
    table: bool,
    fallback: bool,
) -> None:
    """List all hunks with sub-hunk breakdown."""
    fine_diff = get_fine_diff()
    splittable_count = 0
    total_sub_hunks = 0
    files_seen: set[str] = set()

    if table:
        table_list_header()

    for entry in index:
        fine_hunks = parse_diff_hunks(fine_diff, entry.file)
        matching = [
            h for h in fine_hunks
            if hunk_in_parent(h, entry.old_start, entry.old_count)
        ]

        if len(matching) > 1:
            splittable_count += 1
            total_sub_hunks += len(matching)

        if table:
            _emit_list_split_entry_table(entry, matching, files_seen)
        else:
            _emit_list_split_entry_ndjson(entry, matching)

    if table:
        print()
        print(
            f"{total_hunks} hunks across {len(files_seen)} files, "
            f"{splittable_count} splittable ({total_sub_hunks} sub-hunks)",
        )
    else:
        emit(json.dumps({
            "summary": True, "total_hunks": total_hunks,
            "splittable_hunks": splittable_count,
            "total_sub_hunks": total_sub_hunks,
            "mode": "list-split", "fallback": fallback,
        }))


def _count_hunks_in_text(text: str) -> int:
    """Count @@ hunk headers in diff text."""
    return sum(1 for line in text.splitlines() if line.startswith("@@ "))


def mode_verify(
    diff_text: str,
    *,
    table: bool,
    fallback: bool,
) -> None:
    """Show staged vs unstaged summary."""
    staged_result = run_git("diff", "--cached", "--name-only", check=False)
    unstaged_result = run_git("diff", "--name-only", check=False)

    staged_files = sorted(f for f in staged_result.stdout.splitlines() if f)
    unstaged_files = sorted(f for f in unstaged_result.stdout.splitlines() if f)

    staged_diff = run_git("diff", "--cached", check=False).stdout
    staged_hunks = _count_hunks_in_text(staged_diff) if staged_diff else 0
    unstaged_hunks = _count_hunks_in_text(diff_text)

    if not table:
        emit(json.dumps({
            "staged_files": len(staged_files),
            "unstaged_files": len(unstaged_files),
            "staged_hunks": staged_hunks,
            "unstaged_hunks": unstaged_hunks,
        }))
    else:
        table_verify_header()

    all_files = sorted(set(staged_files) | set(unstaged_files))
    total_s = 0
    total_u = 0

    for f in all_files:
        s_hunks = _count_file_hunks(staged_diff, f, fallback=fallback)
        u_hunks = _count_hunks_in_text(
            _extract_file_diff_fallback(diff_text, f),
        )

        if table:
            print(f"| {f} | {s_hunks} | {u_hunks} |")
            total_s += s_hunks
            total_u += u_hunks
        else:
            emit(json.dumps({
                "file": f, "staged_hunks": s_hunks,
                "unstaged_hunks": u_hunks,
            }))

    if table:
        print()
        print(f"{total_s} staged, {total_u} unstaged across {len(all_files)} files")
    else:
        emit(json.dumps({"summary": True, "mode": "verify"}))


def _count_file_hunks(
    diff_text: str,
    file_path: str,
    *,
    fallback: bool,
) -> int:
    """Count hunks for a file in a diff."""
    if not diff_text:
        return 0
    if not fallback:
        filtered = run_filterdiff(diff_text, file_path)
        return _count_hunks_in_text(filtered)
    return _count_hunks_in_text(
        _extract_file_diff_fallback(diff_text, file_path),
    )


# -- Hunk mode sub-handlers ---------------------------------------------------


def _stage_plain_hunks(
    plain_ids: list[str],
    ctx: _RunContext,
    *,
    dry_run: bool,
) -> tuple[int, int, list[StageResult]]:
    """Stage plain hunk IDs (H1, H2, etc.)."""
    matched: list[HunkEntry] = []
    for rid in plain_ids:
        entry = _find_entry(ctx.index, rid)
        if entry:
            matched.append(entry)
        else:
            emit(json.dumps({
                "warning": "invalid_hunk_id", "id": rid,
                "valid_range": f"H1-H{ctx.total_hunks}",
            }))

    if not matched:
        return 0, 0, []

    return stage_hunks(
        matched, ctx.diff_text,
        use_patchutils=ctx.use_patchutils, dry_run=dry_run,
    )


def _stage_subhunk_ref(
    ref: str,
    index: list[HunkEntry],
    *,
    dry_run: bool,
) -> tuple[int, int, StageResult | None]:
    """Stage a single sub-hunk ref (H3.2). Returns (ok, fail, result)."""
    parent_id, sub_idx_str = ref.split(".")
    sub_index = int(sub_idx_str)

    parent = _find_entry(index, parent_id)
    if not parent:
        emit(json.dumps({
            "warning": "invalid_hunk_id", "id": ref,
            "detail": f"parent {parent_id} not found",
        }))
        return 0, 1, None

    fine_diff = get_fine_diff()
    fine_hunks = parse_diff_hunks(fine_diff, parent.file)
    matching = [
        h for h in fine_hunks
        if hunk_in_parent(h, parent.old_start, parent.old_count)
    ]

    if sub_index < 1 or sub_index > len(matching):
        return 0, 1, StageResult(
            id=ref, file=parent.file,
            action="stage_failed", status="error",
            detail="sub-hunk extraction failed",
        )

    hunk = matching[sub_index - 1]
    patch = make_hunk_patch(parent.file, hunk)

    if dry_run:
        return 1, 0, StageResult(
            id=ref, file=parent.file,
            action="would_stage", status="dry_run",
        )

    success, stderr = apply_patch(patch, "--unidiff-zero")
    if success:
        return 1, 0, StageResult(
            id=ref, file=parent.file, action="staged", status="ok",
        )
    return 0, 1, StageResult(
        id=ref, file=parent.file,
        action="stage_failed", status="error", detail=stderr,
    )


def _build_line_select_patch(
    diff_text: str,
    parent: HunkEntry,
    lines_str: str,
) -> str:
    """Build a partial patch from a line range selection."""
    from split_hunk import (  # noqa: PLC0415
        _build_partial_body,
        _recalculate_counts,
    )

    file_hunks = parse_diff_hunks(diff_text, parent.file)
    if parent.hunk_num < 1 or parent.hunk_num > len(file_hunks):
        return ""

    hunk = file_hunks[parent.hunk_num - 1]
    body = hunk.body

    parts = lines_str.split("-")
    start, end = int(parts[0]), int(parts[1])

    if start < 1 or end > len(body) or start > end:
        return ""

    if start == 1 and end == len(body):
        return make_hunk_patch(parent.file, hunk)

    new_body, has_changes = _build_partial_body(body, start, end)
    if not has_changes:
        return ""

    old_count, new_count = _recalculate_counts(new_body)

    patch = make_patch_header(parent.file)
    patch += (
        f"@@ -{hunk.old_start},{old_count} "
        f"+{hunk.new_start},{new_count} @@\n"
    )
    for line in new_body:
        patch += line + "\n"
    return patch


def _stage_linesel_ref(
    ref: str,
    index: list[HunkEntry],
    diff_text: str,
    *,
    dry_run: bool,
) -> tuple[int, int, StageResult | None]:
    """Stage a single line-select ref (H3:5-10). Returns (ok, fail, result)."""
    hunk_id, lines_str = ref.split(":")

    parent = _find_entry(index, hunk_id)
    if not parent:
        emit(json.dumps({
            "warning": "invalid_hunk_id", "id": ref,
            "detail": f"hunk {hunk_id} not found",
        }))
        return 0, 1, None

    patch = _build_line_select_patch(diff_text, parent, lines_str)
    if not patch:
        return 0, 1, StageResult(
            id=ref, file=parent.file,
            action="stage_failed", status="error",
            detail="line-select patch construction failed",
        )

    if dry_run:
        return 1, 0, StageResult(
            id=ref, file=parent.file,
            action="would_stage", status="dry_run",
        )

    success, stderr = apply_patch(patch)
    if success:
        return 1, 0, StageResult(
            id=ref, file=parent.file, action="staged", status="ok",
        )
    return 0, 1, StageResult(
        id=ref, file=parent.file,
        action="stage_failed", status="error", detail=stderr,
    )


def _classify_hunk_ids(
    requested_ids: list[str],
    total_hunks: int,
) -> tuple[list[str], list[str], list[str]]:
    """Classify hunk IDs into plain, subhunk, linesel buckets."""
    plain_ids: list[str] = []
    subhunk_refs: list[str] = []
    linesel_refs: list[str] = []
    bad_ids: list[str] = []

    for rid in requested_ids:
        if HUNK_ID_SUB_RE.match(rid):
            subhunk_refs.append(rid)
        elif HUNK_ID_LINE_RE.match(rid):
            linesel_refs.append(rid)
        elif HUNK_ID_PLAIN_RE.match(rid):
            plain_ids.append(rid)
        else:
            bad_ids.append(rid)

    if bad_ids:
        emit(json.dumps({
            "warning": "invalid_hunk_ids",
            "ids": ",".join(bad_ids),
            "valid_range": f"H1-H{total_hunks}",
        }))

    return plain_ids, subhunk_refs, linesel_refs


def mode_hunk(cfg: ParsedArgs, ctx: _RunContext) -> None:
    """Stage specific hunks by global sequential ID."""
    if not cfg.hunk_ids:
        die("no hunk IDs specified", EXIT_USAGE)

    requested = [rid.strip() for rid in cfg.hunk_ids.split(",")]
    plain_ids, subhunk_refs, linesel_refs = _classify_hunk_ids(
        requested, ctx.total_hunks,
    )

    all_results: list[StageResult] = []
    total_ok = 0
    total_fail = 0

    # Batch 1: Plain hunk IDs
    if plain_ids:
        ok, fail, results = _stage_plain_hunks(
            plain_ids, ctx, dry_run=cfg.dry_run,
        )
        total_ok += ok
        total_fail += fail
        all_results.extend(results)

    # Batch 2: Sub-hunk IDs
    for ref in subhunk_refs:
        ok, fail, result = _stage_subhunk_ref(
            ref, ctx.index, dry_run=cfg.dry_run,
        )
        total_ok += ok
        total_fail += fail
        if result:
            all_results.append(result)

    # Batch 3: Line-select IDs
    for ref in linesel_refs:
        ok, fail, result = _stage_linesel_ref(
            ref, ctx.index, ctx.diff_text, dry_run=cfg.dry_run,
        )
        total_ok += ok
        total_fail += fail
        if result:
            all_results.append(result)

    total_requested = len(plain_ids) + len(subhunk_refs) + len(linesel_refs)
    if total_requested == 0:
        if cfg.table:
            print("No valid hunk IDs.")
        else:
            emit(json.dumps({
                "summary": True, "total_hunks": ctx.total_hunks,
                "staged": 0, "failed": 0,
                "dry_run": cfg.dry_run, "error": "no valid hunk IDs",
            }))
        sys.exit(EXIT_RUNTIME)

    emit_stage_results(
        _StageOutcome(all_results, total_ok, total_fail, ctx.total_hunks),
        table=cfg.table, dry_run=cfg.dry_run, fallback=cfg.fallback,
    )
    if total_fail > 0:
        sys.exit(EXIT_RUNTIME)


def mode_file(cfg: ParsedArgs, ctx: _RunContext) -> None:
    """Stage all hunks for specified file(s)."""
    if not cfg.file_paths:
        die("no file paths specified", EXIT_USAGE)

    requested_files = [f.strip() for f in cfg.file_paths.split(",")]
    matched: list[HunkEntry] = []
    bad_files: list[str] = []

    for rf in requested_files:
        file_entries = [e for e in ctx.index if e.file == rf]
        if file_entries:
            matched.extend(file_entries)
        else:
            bad_files.append(rf)

    if bad_files:
        emit(json.dumps({
            "warning": "files_not_in_diff",
            "files": ",".join(bad_files),
        }))

    if not matched:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0,
            "dry_run": cfg.dry_run, "error": "no matching files in diff",
        }))
        sys.exit(EXIT_RUNTIME)

    ok, fail, results = stage_hunks(
        matched, ctx.diff_text,
        use_patchutils=ctx.use_patchutils, dry_run=cfg.dry_run,
    )
    emit_stage_results(
        _StageOutcome(results, ok, fail, ctx.total_hunks),
        table=cfg.table, dry_run=cfg.dry_run, fallback=cfg.fallback,
    )
    if fail > 0:
        sys.exit(EXIT_RUNTIME)


def mode_pattern(cfg: ParsedArgs, ctx: _RunContext) -> None:
    """Stage hunks matching regex (requires patchutils)."""
    if not cfg.pattern:
        die("no pattern specified", EXIT_USAGE)

    matched_diff = run_grepdiff(ctx.diff_text, cfg.pattern)
    if not matched_diff:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0,
            "dry_run": cfg.dry_run, "error": "no hunks match pattern",
        }))
        return

    matched_index = build_hunk_index(matched_diff, use_patchutils=True)
    if not matched_index:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0, "dry_run": cfg.dry_run,
            "error": "no parseable hunks match pattern",
        }))
        return

    final_entries = _map_to_global_ids(matched_index, ctx.index)
    if not final_entries:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0, "dry_run": cfg.dry_run,
            "error": "matched hunks could not be mapped to global IDs",
        }))
        return

    ok, fail, results = stage_hunks(
        final_entries, ctx.diff_text,
        use_patchutils=True, dry_run=cfg.dry_run,
    )
    emit_stage_results(
        _StageOutcome(results, ok, fail, ctx.total_hunks),
        table=cfg.table, dry_run=cfg.dry_run, fallback=False,
    )
    if fail > 0:
        sys.exit(EXIT_RUNTIME)


def _parse_range_spec(
    range_spec: str,
) -> tuple[str, str, str]:
    """Parse FILE:START-END into (file, start, end)."""
    colon_idx = range_spec.rfind(":")
    if colon_idx < 0:
        die("invalid range spec: missing file", EXIT_USAGE)

    range_file = range_spec[:colon_idx]
    range_lines = range_spec[colon_idx + 1:]

    parts = range_lines.split("-")
    if len(parts) != 2:  # noqa: PLR2004
        die("invalid range spec: expected START-END", EXIT_USAGE)

    if not range_file:
        die("invalid range spec: missing file", EXIT_USAGE)
    if not parts[0]:
        die("invalid range spec: missing start line", EXIT_USAGE)
    if not parts[1]:
        die("invalid range spec: missing end line", EXIT_USAGE)

    return range_file, parts[0], parts[1]


def mode_range(cfg: ParsedArgs, ctx: _RunContext) -> None:
    """Stage hunks overlapping line range (requires patchutils)."""
    if not cfg.range_spec:
        die("no range specified", EXIT_USAGE)

    range_file, range_start, range_end = _parse_range_spec(cfg.range_spec)

    matched_diff = run_filterdiff(
        ctx.diff_text, range_file,
        lines=f"{range_start}-{range_end}",
    )

    if not matched_diff:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0, "dry_run": cfg.dry_run,
            "error": (
                f"no hunks overlap range {range_start}-{range_end}"
                f" in {range_file}"
            ),
        }))
        return

    matched_index = build_hunk_index(matched_diff, use_patchutils=True)
    final_entries = _map_to_global_ids(matched_index, ctx.index)

    if not final_entries:
        emit(json.dumps({
            "summary": True, "total_hunks": ctx.total_hunks,
            "staged": 0, "failed": 0, "dry_run": cfg.dry_run,
            "error": "matched hunks could not be mapped to global IDs",
        }))
        return

    ok, fail, results = stage_hunks(
        final_entries, ctx.diff_text,
        use_patchutils=True, dry_run=cfg.dry_run,
    )
    emit_stage_results(
        _StageOutcome(results, ok, fail, ctx.total_hunks),
        table=cfg.table, dry_run=cfg.dry_run, fallback=False,
    )
    if fail > 0:
        sys.exit(EXIT_RUNTIME)


# -- Run context ---------------------------------------------------------------


@dataclass
class _RunContext:
    """Shared state for mode dispatch."""

    index: list[HunkEntry]
    diff_text: str
    total_hunks: int
    use_patchutils: bool


# -- CLI / main ----------------------------------------------------------------


def _resolve_split_mode(raw: argparse.Namespace) -> tuple[str, str]:
    """Resolve --split flag into (mode, split_target)."""
    if raw.split is not True and isinstance(raw.split, str):
        return "split", raw.split
    if raw.list_mode:
        return "list-split", ""
    die(
        "--split requires a hunk ID (--split H3) "
        "or must be combined with --list",
        EXIT_USAGE,
    )
    return "", ""  # unreachable, die exits


def _detect_mode(raw: argparse.Namespace, file_paths: str) -> str:
    """Detect the primary mode from raw args."""
    checks = [
        (raw.list_mode, "list"),
        (raw.hunk, "hunk"),
        (raw.pattern, "pattern"),
        (bool(file_paths), "file"),
        (raw.range_spec, "range"),
        (raw.verify, "verify"),
    ]
    return next((mode for flag, mode in checks if flag), "")


def _resolve_mode(raw: argparse.Namespace) -> ParsedArgs:
    """Resolve raw argparse output into validated ParsedArgs."""
    file_filter = ""
    file_paths = raw.file

    if raw.list_mode and raw.file:
        file_filter = raw.file
        file_paths = ""

    mode = ""
    split_target = ""

    if raw.split is not None:
        mode, split_target = _resolve_split_mode(raw)
    else:
        mode = _detect_mode(raw, file_paths)

    if not mode:
        die(
            "no mode specified (use --check-deps, --list, --hunk, "
            "--pattern, --file, --range, --split, or --verify)",
            EXIT_USAGE,
        )

    return ParsedArgs(
        mode=mode,
        split_target=split_target,
        hunk_ids=raw.hunk,
        pattern=raw.pattern,
        file_paths=file_paths,
        file_filter=file_filter,
        range_spec=raw.range_spec,
        table=raw.table,
        dry_run=raw.dry_run,
        fallback=raw.fallback,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Non-interactive hunk staging for selective git add",
    )
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_mode")
    parser.add_argument("--split", nargs="?", const=True, default=None)
    parser.add_argument("--hunk", default="")
    parser.add_argument("--pattern", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--range", default="", dest="range_spec")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--table", action="store_true")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--fallback", action="store_true")
    return parser


def _dispatch_mode(cfg: ParsedArgs, ctx: _RunContext) -> None:
    """Dispatch to the appropriate mode handler."""
    handlers: dict[str, object] = {
        "list": lambda: mode_list(
            ctx.index, ctx.total_hunks,
            table=cfg.table, fallback=cfg.fallback,
        ),
        "split": lambda: mode_split(
            ctx.index, cfg.split_target, ctx.total_hunks,
        ),
        "list-split": lambda: mode_list_split(
            ctx.index, ctx.total_hunks,
            table=cfg.table, fallback=cfg.fallback,
        ),
        "verify": lambda: mode_verify(
            ctx.diff_text, table=cfg.table, fallback=cfg.fallback,
        ),
        "hunk": lambda: mode_hunk(cfg, ctx),
        "file": lambda: mode_file(cfg, ctx),
        "pattern": lambda: mode_pattern(cfg, ctx),
        "range": lambda: mode_range(cfg, ctx),
    }
    handler = handlers.get(cfg.mode)
    if handler and callable(handler):
        handler()


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    raw = _build_parser().parse_args(argv)

    if raw.check_deps:
        mode_check_deps()
        sys.exit(EXIT_OK)

    use_patchutils = has_patchutils() and not raw.fallback
    cfg = _resolve_mode(raw)
    cfg.fallback = not use_patchutils

    if cfg.fallback and cfg.pattern:
        die(
            "--pattern mode requires patchutils (grepdiff). "
            "Install with: brew install patchutils",
        )
    if cfg.fallback and cfg.range_spec:
        die(
            "--range mode requires patchutils (filterdiff). "
            "Install with: brew install patchutils",
        )

    result = run_git("rev-parse", "--git-dir", check=False)
    if result.returncode != 0:
        die("not inside a git repository")

    diff_text = get_diff()
    if not diff_text:
        emit('{"error":"no_unstaged_changes","detail":"git diff is empty"}')
        sys.exit(EXIT_OK)

    hunk_index = build_hunk_index(diff_text, use_patchutils=use_patchutils)
    if not hunk_index:
        emit(
            '{"error":"no_hunks",'
            '"detail":"diff exists but no parseable hunks found '
            '(binary files only?)"}',
        )
        sys.exit(EXIT_OK)

    total_hunks = len(hunk_index)

    if cfg.file_filter:
        filtered = filter_by_files(hunk_index, cfg.file_filter)
        if not filtered:
            if cfg.table:
                print("No unstaged hunks match the file filter.")
            else:
                emit(
                    '{"error":"no_hunks_for_file",'
                    '"detail":"no unstaged hunks match the file filter"}',
                )
                emit(json.dumps({
                    "summary": True, "total_hunks": total_hunks,
                    "mode": "list", "filtered": 0,
                }))
            sys.exit(EXIT_OK)
        hunk_index = filtered
        total_hunks = len(hunk_index)

    ctx = _RunContext(
        index=hunk_index,
        diff_text=diff_text,
        total_hunks=total_hunks,
        use_patchutils=use_patchutils,
    )
    _dispatch_mode(cfg, ctx)


if __name__ == "__main__":
    main()
