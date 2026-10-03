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
    - Base versions come from manifests at the same path plus manifests with
      the same "name" that the commit moves or deletes, so moving
      'claude/<name>' into 'plugins/<name>' still bumps past both
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

import ctypes
import ctypes.util
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
VERSION_RE: Final[re.Pattern[str]] = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$",
)
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
MIN_LONG_PREFIX: Final[int] = 2
CTL_KERN: Final[int] = 1
KERN_PROCARGS2: Final[int] = 49
ARGC_BYTES: Final[int] = 4
GIT_OPTIONS_WITH_VALUE: Final[frozenset[str]] = frozenset({"-c", "-C"})
COMMIT_SHORT_OPTIONS_WITH_VALUE: Final[frozenset[str]] = frozenset("mFCct")
COMMIT_SHORT_OPTIONS_ATTACHED_VALUE: Final[frozenset[str]] = frozenset("Su")
COMMIT_LONG_OPTIONS_WITH_VALUE: Final[tuple[str, ...]] = (
    "author",
    "cleanup",
    "date",
    "file",
    "fixup",
    "message",
    "pathspec-from-file",
    "reedit-message",
    "reuse-message",
    "squash",
    "template",
    "trailer",
)


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


def _proc_argv(pid: int) -> list[str] | None:
    cmdline = Path(f"/proc/{pid}/cmdline")
    try:
        raw = cmdline.read_bytes()
    except OSError:
        return None
    return [_decode_path(arg) for arg in raw.removesuffix(b"\0").split(b"\0")]


def _darwin_argv(pid: int) -> list[str] | None:
    libc_path = ctypes.util.find_library("c")
    if libc_path is None:
        return None
    libc = ctypes.CDLL(libc_path, use_errno=True)
    mib = (ctypes.c_int * 3)(CTL_KERN, KERN_PROCARGS2, pid)
    size = ctypes.c_size_t(0)
    if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0:
        return None
    buf = ctypes.create_string_buffer(size.value)
    if libc.sysctl(mib, 3, buf, ctypes.byref(size), None, 0) != 0:
        return None
    raw = buf.raw[: size.value]
    argc = int.from_bytes(raw[:ARGC_BYTES], sys.byteorder)
    exec_end = raw.find(b"\0", ARGC_BYTES)
    if exec_end < 0:
        return None
    pos = exec_end
    while pos < len(raw) and raw[pos] == 0:
        pos += 1
    args = raw[pos:].split(b"\0")[:argc]
    return [_decode_path(arg) for arg in args] if len(args) == argc else None


def parent_argv() -> list[str] | None:
    """Return the exact argv of the process that ran this hook, or None."""
    pid = os.getppid()
    argv = _proc_argv(pid)
    if argv is None and sys.platform == "darwin":
        argv = _darwin_argv(pid)
    return argv


def _long_option(word: str, names: tuple[str, ...]) -> bool:
    name = word[2:]
    return len(name) >= MIN_LONG_PREFIX and any(n.startswith(name) for n in names)


def _commit_args(argv: list[str]) -> list[str]:
    pos = 1
    while pos < len(argv) and argv[pos] != "commit":
        pos += 2 if argv[pos] in GIT_OPTIONS_WITH_VALUE else 1
    return argv[pos + 1 :]


def _option_effect(word: str) -> tuple[bool | None, int]:
    """Return (amend setting or None, number of following values consumed)."""
    if word.startswith("--"):
        if "=" in word:
            return None, 0
        if _long_option(word, ("amend",)):
            return True, 0
        if _long_option(word, ("no-amend",)):
            return False, 0
        return None, int(_long_option(word, COMMIT_LONG_OPTIONS_WITH_VALUE))
    if word.startswith("-"):
        for index, flag in enumerate(word[1:], start=1):
            if flag in COMMIT_SHORT_OPTIONS_WITH_VALUE:
                return None, int(index == len(word) - 1)
            if flag in COMMIT_SHORT_OPTIONS_ATTACHED_VALUE:
                break
    return None, 0


def amend_requested(argv: list[str]) -> bool:
    """Return True when an argv runs 'commit' with --amend in effect."""
    args = _commit_args(argv)
    amend = False
    pos = 0
    while pos < len(args) and args[pos] != "--":
        setting, consumed = _option_effect(args[pos])
        if setting is not None:
            amend = setting
        pos += 1 + consumed
    return amend


def is_amend() -> bool | None:
    """Return True when the commit being made amends HEAD, None if unknown.

    pre-commit gets no amend signal, so this reads the exact argv of the parent
    process (/proc on Linux, sysctl on macOS) and parses the commit options.
    """
    argv = parent_argv()
    return None if argv is None else amend_requested(argv)


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
    names: set[str] = set()
    for path in plugin.manifests:
        data = load_manifest(blobs[index[path].sha], path)
        staged[path] = parse_version(data.get("version"), path)
        if isinstance(name := data.get("name"), str):
            names.add(name)

    previous: list[tuple[int, int, int]] = []
    for path, entry in base.items():
        if not MANIFEST_RE.match(path):
            continue
        same_path = path in staged
        moved_away = path not in index
        if not same_path and not moved_away:
            continue
        try:
            data = load_manifest(blobs[entry.sha], path)
            if same_path or data.get("name") in names:
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
        current = target.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        print(f"{PROG}: warning: '{change.path}' not updated on disk", file=sys.stderr)
        return
    if current == staged_text:
        target.write_bytes(new_text.encode("utf-8"))
        return
    try:
        rewritten = replace_version(current, change.old, change.new, change.path)
    except BumpError:
        print(
            f"{PROG}: warning: '{change.path}' has unstaged edits; "
            f"set its version to {change.new} by hand",
            file=sys.stderr,
        )
        return
    target.write_bytes(rewritten.encode("utf-8"))


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
    detected = is_amend()
    amend = bool(detected)
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
            "cannot stage version bumps when git commits from a temporary "
            "index ('git commit <paths>' or '--only'); stage the files with "
            "'git add' and run 'git commit' without paths or '--only'"
        )
        raise BumpError(msg)

    if detected is None:
        print(
            f"{PROG}: warning: cannot read the git command line on this "
            "platform; if this is 'git commit --amend', check the bumped "
            "versions are not one patch too high",
            file=sys.stderr,
        )
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
