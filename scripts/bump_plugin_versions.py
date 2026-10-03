#!/usr/bin/env python3
"""Bump the patch version of every plugin with staged changes.

Runs from the git pre-commit hook in '.githooks/pre-commit'. For each plugin
whose files are staged, it bumps the patch version in every manifest of that
plugin, writes the new version to the index and the working tree, and keeps all
manifests of the plugin on the same version.

Plugin layouts:
    claude/<name>/.claude-plugin/plugin.json
    plugins/<name>/plugin.json
    plugins/<name>/.claude-plugin/plugin.json
    plugins/<name>/.codex-plugin/plugin.json
A plugin owns its directory plus any directory its manifests point to through
the "skills" field (for example 'codex/<name>' for Codex plugins).

Rules:
    - Only staged files count; README.md changes alone never trigger a bump
    - A plugin whose highest staged version is already above every version in
      the base commit is not bumped again; its other manifests are synced to
      that version. Otherwise the target is the highest base version + 1 patch
    - The base commit is HEAD, or HEAD^ for 'git commit --amend'
    - New plugins (no manifest in the base) and deleted plugins are left alone
    - A broken manifest only blocks commits that touch its plugin
    - Merges, cherry-picks, reverts, and the initial commit are skipped

Git calls use a fixed argv; paths and contents go through stdin so repository
data never lands on a command line. git is resolved from PATH on purpose: git
prepends its own exec path to PATH when it runs hooks.

Usage:
    python3 scripts/bump_plugin_versions.py

Exit codes:
    0  success (manifests may have been bumped and staged)
    1  a manifest is invalid or the commit mode cannot be handled

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

PROG: Final[str] = "bump-plugin-versions"
GIT_TIMEOUT_SECONDS: Final[int] = 30
BATCH_HEADER_FIELDS: Final[int] = 3
MANIFEST_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<root>(?:claude|plugins)/[^/]+)/(?:\.claude-plugin/|\.codex-plugin/)?"
    r"plugin\.json$",
)
VERSION_RE: Final[re.Pattern[str]] = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    r'("version"\s*:\s*")([^"\\]*)(")',
)
IGNORED_BASENAMES: Final[frozenset[str]] = frozenset({"README.md"})
IN_PROGRESS_MARKERS: Final[tuple[str, ...]] = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
)
PATHSPEC_INDEX_PREFIX: Final[str] = "next-index"
AMEND_FLAG: Final[str] = "--amend"
AMEND_MIN_PREFIX: Final[int] = len("--am")


class BumpError(Exception):
    """Raised when the hook cannot bump versions safely."""


@dataclass(frozen=True)
class Entry:
    """One blob entry of the index or of a commit."""

    mode: str
    sha: str


def _check(result: subprocess.CompletedProcess[bytes], what: str) -> bytes:
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        msg = f"git {what} failed: {stderr or f'exit {result.returncode}'}"
        raise BumpError(msg)
    return result.stdout


def _decode_path(raw: bytes) -> str:
    return raw.decode("utf-8", "surrogateescape")


def git_toplevel() -> Path:
    """Return the working tree root."""
    result = subprocess.run(
        ["/usr/bin/env", "git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return Path(_check(result, "rev-parse --show-toplevel").decode().strip())


def git_dir() -> Path:
    """Return the per-worktree git directory."""
    result = subprocess.run(
        ["/usr/bin/env", "git", "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return Path(_check(result, "rev-parse --absolute-git-dir").decode().strip())


def base_exists(*, amend: bool) -> bool:
    """Return True when the commit to compare against exists."""
    if amend:
        result = subprocess.run(
            ["/usr/bin/env", "git", "rev-parse", "--verify", "--quiet", "HEAD^"],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    else:
        result = subprocess.run(
            ["/usr/bin/env", "git", "rev-parse", "--verify", "--quiet", "HEAD"],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    return result.returncode == 0


def head_author_date() -> str:
    """Return the author date of HEAD in raw format."""
    result = subprocess.run(
        ["/usr/bin/env", "git", "show", "-s", "--format=%ad", "--date=raw", "HEAD"],
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return result.stdout.decode("utf-8", "replace").strip()


def parent_argv() -> list[str]:
    """Return the argv words of the process that ran this hook, or []."""
    try:
        result = subprocess.run(
            ["/usr/bin/env", "ps", "-A", "-o", "pid=,args="],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except OSError:
        return []
    parent = str(os.getppid())
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        pid, _, args = line.strip().partition(" ")
        if pid == parent:
            return args.split()
    return []


def is_amend() -> bool:
    """Return True when the commit being made amends HEAD.

    pre-commit gets no amend signal, so two independent hints must agree: the
    parent git process was given --amend, and git kept HEAD's author date for
    the new commit (it sets GIT_AUTHOR_DATE to it when amending).
    """
    words = parent_argv()
    if "commit" not in words:
        return False
    after = words[words.index("commit") + 1 :]
    if not any(len(w) >= AMEND_MIN_PREFIX and AMEND_FLAG.startswith(w) for w in after):
        return False
    author_date = os.environ.get("GIT_AUTHOR_DATE", "").removeprefix("@")
    return bool(author_date) and author_date == head_author_date()


def staged_paths(*, amend: bool) -> list[str]:
    """Return paths whose staged content differs from the base commit."""
    if amend:
        result = subprocess.run(
            [
                "/usr/bin/env",
                "git",
                "diff",
                "--cached",
                "--name-only",
                "--no-renames",
                "-z",
                "HEAD^",
            ],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    else:
        result = subprocess.run(
            [
                "/usr/bin/env",
                "git",
                "diff",
                "--cached",
                "--name-only",
                "--no-renames",
                "-z",
                "HEAD",
            ],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    out = _check(result, "diff --cached")
    return sorted(_decode_path(p) for p in out.split(b"\0") if p)


def index_entries() -> dict[str, Entry]:
    """Return stage-0 index entries keyed by path."""
    result = subprocess.run(
        ["/usr/bin/env", "git", "ls-files", "--stage", "-z"],
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    entries: dict[str, Entry] = {}
    for record in _check(result, "ls-files --stage").split(b"\0"):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        mode, sha, stage = meta.decode().split(" ")
        if stage == "0":
            entries[_decode_path(raw_path)] = Entry(mode, sha)
    return entries


def base_entries(*, amend: bool) -> dict[str, Entry]:
    """Return blob entries of the base commit keyed by path."""
    if amend:
        result = subprocess.run(
            ["/usr/bin/env", "git", "ls-tree", "-r", "-z", "HEAD^"],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    else:
        result = subprocess.run(
            ["/usr/bin/env", "git", "ls-tree", "-r", "-z", "HEAD"],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    entries: dict[str, Entry] = {}
    for record in _check(result, "ls-tree").split(b"\0"):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        mode, kind, sha = meta.decode().split(" ")
        if kind == "blob":
            entries[_decode_path(raw_path)] = Entry(mode, sha)
    return entries


def read_blobs(shas: list[str]) -> dict[str, bytes]:
    """Return blob contents keyed by object id."""
    unique = sorted(set(shas))
    if not unique:
        return {}
    result = subprocess.run(
        ["/usr/bin/env", "git", "cat-file", "--batch"],
        input="".join(f"{sha}\n" for sha in unique).encode(),
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    out = _check(result, "cat-file --batch")
    blobs: dict[str, bytes] = {}
    pos = 0
    for sha in unique:
        header_end = out.index(b"\n", pos)
        header = out[pos:header_end].decode().split(" ")
        if len(header) != BATCH_HEADER_FIELDS or header[1] != "blob":
            msg = f"cannot read object {sha}"
            raise BumpError(msg)
        size = int(header[2])
        start = header_end + 1
        blobs[sha] = out[start : start + size]
        pos = start + size + 1
    return blobs


def write_blob(content: bytes) -> str:
    """Store content in the object database and return its id."""
    result = subprocess.run(
        ["/usr/bin/env", "git", "hash-object", "-w", "--stdin"],
        input=content,
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return _check(result, "hash-object").decode().strip()


def stage_blobs(updates: dict[str, Entry]) -> None:
    """Point index entries at new blobs."""
    lines = "".join(f"{e.mode} {e.sha}\t{path}\n" for path, e in updates.items())
    result = subprocess.run(
        ["/usr/bin/env", "git", "update-index", "--index-info"],
        input=lines.encode("utf-8", "surrogateescape"),
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    _check(result, "update-index --index-info")


def parse_version(value: object, path: str) -> tuple[int, int, int]:
    """Parse a MAJOR.MINOR.PATCH version string."""
    match = VERSION_RE.match(value) if isinstance(value, str) else None
    if match is None:
        msg = f"'{path}' has version {value!r}, expected MAJOR.MINOR.PATCH"
        raise BumpError(msg)
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def format_version(version: tuple[int, int, int]) -> str:
    """Render a version tuple as MAJOR.MINOR.PATCH."""
    return ".".join(str(part) for part in version)


def load_manifest(content: bytes, path: str) -> dict[str, object]:
    """Parse manifest JSON and require a top-level object."""
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"'{path}' is not valid JSON: {exc}"
        raise BumpError(msg) from exc
    if not isinstance(data, dict):
        msg = f"'{path}' must contain a JSON object"
        raise BumpError(msg)
    return data


def replace_version(text: str, old: str, new: str, path: str) -> str:
    """Rewrite the top-level version in place, keeping the file's formatting."""
    for match in VERSION_FIELD_RE.finditer(text):
        if match.group(2) != old:
            continue
        candidate = f"{text[: match.start(2)]}{new}{text[match.end(2) :]}"
        try:
            data = json.loads(candidate.removeprefix("\ufeff"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("version") == new:
            return candidate
    msg = f"cannot locate the top-level version field in '{path}'"
    raise BumpError(msg)


@dataclass
class Plugin:
    """A plugin directory, its manifests, and the directories it owns."""

    root: str
    manifests: list[str] = field(default_factory=list)
    owned: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    def owns(self, path: str) -> bool:
        """Return True when path belongs to this plugin."""
        return any(path == d or path.startswith(f"{d}/") for d in self.owned)


def skills_dirs(root: str, data: dict[str, object]) -> list[str]:
    """Resolve the manifest "skills" field to repo-relative directories."""
    value = data.get("skills")
    raw = [value] if isinstance(value, str) else value
    if not isinstance(raw, list):
        return []
    dirs: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item:
            continue
        resolved = posixpath.normpath(posixpath.join(root, item))
        if resolved in {".", ".."} or resolved.startswith("../"):
            continue
        dirs.append(resolved)
    return dirs


def discover_plugins(
    index: dict[str, Entry],
    blobs: dict[str, bytes],
) -> dict[str, Plugin]:
    """Group index manifests into plugins keyed by plugin directory."""
    plugins: dict[str, Plugin] = {}
    for path in sorted(index):
        match = MANIFEST_RE.match(path)
        if match is None:
            continue
        root = match.group("root")
        plugin = plugins.setdefault(root, Plugin(root=root, owned={root}))
        plugin.manifests.append(path)
        try:
            data = load_manifest(blobs[index[path].sha], path)
        except BumpError as exc:
            plugin.errors.append(str(exc))
            continue
        plugin.owned.update(skills_dirs(root, data))
    return plugins


def triggers_bump(path: str) -> bool:
    """Return True when a staged path counts as a functional change."""
    return posixpath.basename(path) not in IGNORED_BASENAMES


@dataclass(frozen=True)
class Change:
    """A manifest rewrite: path, old version, new version."""

    path: str
    old: str
    new: str


def plan_plugin(
    plugin: Plugin,
    index: dict[str, Entry],
    base: dict[str, Entry],
    blobs: dict[str, bytes],
) -> tuple[str, list[Change]]:
    """Return the target version and manifest rewrites for one plugin."""
    if plugin.errors:
        raise BumpError("; ".join(plugin.errors))
    staged: dict[str, tuple[int, int, int]] = {}
    for path in plugin.manifests:
        data = load_manifest(blobs[index[path].sha], path)
        staged[path] = parse_version(data.get("version"), path)

    previous: list[tuple[int, int, int]] = []
    for path in plugin.manifests:
        if path not in base:
            continue
        try:
            data = load_manifest(blobs[base[path].sha], path)
            previous.append(parse_version(data.get("version"), path))
        except BumpError:
            continue

    highest = max(staged.values())
    if previous and highest <= max(previous):
        released = max(previous)
        highest = (released[0], released[1], released[2] + 1)

    target = format_version(highest)
    changes = [
        Change(path, format_version(version), target)
        for path, version in staged.items()
        if format_version(version) != target
    ]
    return target, changes


def sync_worktree(top: Path, change: Change, staged_text: str, new_text: str) -> None:
    """Mirror an index rewrite into the working tree file."""
    target = top / change.path
    try:
        current = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print(f"{PROG}: warning: '{change.path}' not updated on disk", file=sys.stderr)
        return
    if current == staged_text:
        target.write_text(new_text, encoding="utf-8")
        return
    try:
        target.write_text(
            replace_version(current, change.old, change.new, change.path),
            encoding="utf-8",
        )
    except BumpError:
        print(
            f"{PROG}: warning: '{change.path}' has unstaged edits; "
            f"set its version to {change.new} by hand",
            file=sys.stderr,
        )


def apply_changes(
    top: Path,
    changes: list[Change],
    index: dict[str, Entry],
    blobs: dict[str, bytes],
) -> None:
    """Write rewritten manifests to the index and the working tree."""
    updates: dict[str, Entry] = {}
    rewritten: list[tuple[Change, str, str]] = []
    for change in changes:
        entry = index[change.path]
        staged_text = blobs[entry.sha].decode("utf-8")
        new_text = replace_version(staged_text, change.old, change.new, change.path)
        updates[change.path] = Entry(entry.mode, write_blob(new_text.encode("utf-8")))
        rewritten.append((change, staged_text, new_text))
    stage_blobs(updates)
    for change, staged_text, new_text in rewritten:
        sync_worktree(top, change, staged_text, new_text)


def commit_in_progress() -> bool:
    """Return True for merge, cherry-pick, and revert commits."""
    gdir = git_dir()
    return any((gdir / marker).exists() for marker in IN_PROGRESS_MARKERS)


def run() -> int:
    """Bump versions for staged plugins and return the exit code."""
    if commit_in_progress():
        return 0
    amend = is_amend()
    if not base_exists(amend=amend):
        return 0
    paths = [p for p in staged_paths(amend=amend) if triggers_bump(p)]
    if not paths:
        return 0

    index = index_entries()
    base = base_entries(amend=amend)
    manifest_shas = [e.sha for p, e in index.items() if MANIFEST_RE.match(p)]
    manifest_shas += [e.sha for p, e in base.items() if MANIFEST_RE.match(p)]
    blobs = read_blobs(manifest_shas)

    changes: list[Change] = []
    for plugin in discover_plugins(index, blobs).values():
        if not any(plugin.owns(p) for p in paths):
            continue
        target, plugin_changes = plan_plugin(plugin, index, base, blobs)
        for change in plugin_changes:
            print(
                f"{PROG}: {change.path}: {change.old} -> {target}",
                file=sys.stderr,
            )
        changes.extend(plugin_changes)
    if not changes:
        return 0

    index_file = posixpath.basename(os.environ.get("GIT_INDEX_FILE", ""))
    if index_file.startswith(PATHSPEC_INDEX_PREFIX):
        msg = (
            "cannot stage version bumps for 'git commit <paths>'; "
            "stage the files with 'git add' and run 'git commit' without paths"
        )
        raise BumpError(msg)

    apply_changes(git_toplevel(), changes, index, blobs)
    return 0


def main() -> int:
    """Entry point."""
    try:
        return run()
    except (BumpError, subprocess.TimeoutExpired) as exc:
        print(f"{PROG}: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
