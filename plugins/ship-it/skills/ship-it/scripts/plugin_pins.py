#!/usr/bin/env python3
"""Retain complete ship-it bundles independently of provider plugin caches.

Commands acquire/release run leases and collect unused snapshots. Output is JSON;
exit 0 means success, 2 means invalid input or a failed snapshot. Unix only.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

fcntl: ModuleType | None
try:
    import fcntl
except ImportError:
    fcntl = None

MAX_CLEANUP: Final[int] = 100
LEASE_LENGTH: Final[int] = 32
PROCESS_FIELDS: Final[int] = 2


def process_identity(pid: int) -> str:
    """Return the process start identity; fail closed on probe errors."""
    if pid <= 1:
        msg = "owner PID must identify a live agent process"
        raise ValueError(msg)
    try:
        os.kill(pid, 0)
    except ProcessLookupError as error:
        msg = f"owner process {pid} is not running"
        raise ValueError(msg) from error
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,lstart="],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env={**os.environ, "TZ": "UTC", "LC_ALL": "C"},
    )
    identities = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) == PROCESS_FIELDS and fields[0].isdigit():
            identities[int(fields[0])] = fields[1]
    identity = identities.get(pid, "")
    if result.returncode or not identity:
        try:
            os.kill(pid, 0)
        except ProcessLookupError as error:
            msg = f"owner process {pid} is not running"
            raise ValueError(msg) from error
        msg = f"cannot determine start identity for owner process {pid}"
        raise OSError(msg)
    return identity


def inventory(root: Path) -> dict[str, dict]:
    """Hash complete regular-file content and directory modes."""
    entries = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode) or not (
            stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)
        ):
            msg = f"unsupported bundle entry: {relative}"
            raise ValueError(msg)
        entries[relative] = {
            "mode": stat.S_IMODE(info.st_mode) & ~0o222,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None,
        }
    return entries


def encoded(value: object) -> bytes:
    """Serialize stable JSON for content addressing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def atomic_json(path: Path, value: object) -> None:
    """Publish a complete JSON record by rename."""
    temporary = path.with_name(f".{path.name}-{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def remove_snapshot(path: Path) -> None:
    """Make unleased snapshot directories removable before collection."""
    path.chmod(path.stat().st_mode | stat.S_IWUSR)
    for entry in path.rglob("*"):
        if entry.is_dir():
            entry.chmod(entry.stat().st_mode | stat.S_IWUSR)
    shutil.rmtree(path)


class Pins:
    """Manage immutable bundle snapshots and independent consumer leases."""

    def __init__(self, root: Path) -> None:
        """Use an explicit snapshot store."""
        self.root = root.resolve()

    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        """Serialize acquisition, release and collection."""
        if fcntl is None or not Path("/bin/ps").is_file():
            msg = "bundle retention requires Unix flock and /bin/ps"
            raise OSError(msg)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            for name in ("bundles", "leases"):
                (self.root / name).mkdir(exist_ok=True)
            yield

    def acquire(self, source: Path, owner_pid: int) -> dict:
        """Snapshot and lease a bundle before exposing its path."""
        identity = process_identity(owner_pid)
        source = source.resolve(strict=True)
        if self.root == source or source in self.root.parents:
            msg = "pin store must be outside the source bundle"
            raise ValueError(msg)
        with self.locked():
            before = inventory(source)
            manifest_bytes = (source / "plugin.json").read_bytes()
            if (
                hashlib.sha256(manifest_bytes).hexdigest()
                != before["plugin.json"]["sha256"]
            ):
                msg = "source manifest changed during snapshot; retry acquisition"
                raise ValueError(msg)
            manifest = json.loads(manifest_bytes)
            if (
                not isinstance(manifest, dict)
                or manifest.get("name") != "ship-it"
                or not manifest.get("version")
            ):
                msg = "source must be a complete ship-it plugin bundle"
                raise ValueError(msg)
            if not (source / "skills/ship-it/SKILL.md").is_file():
                msg = "source bundle is missing the ship-it skill"
                raise ValueError(msg)
            digest = hashlib.sha256(encoded(before)).hexdigest()
            destination = self.root / "bundles" / digest
            if not destination.exists():
                staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.root))
                try:
                    shutil.copytree(source, staging / "plugin", symlinks=True)
                    if (
                        inventory(staging / "plugin") != before
                        or inventory(source) != before
                    ):
                        msg = "source bundle changed during snapshot; retry acquisition"
                        raise ValueError(msg)
                    atomic_json(
                        staging / "provenance.json",
                        {
                            "schemaVersion": 1,
                            "digest": digest,
                            "source": str(source),
                            "manifest": manifest,
                            "inventory": before,
                        },
                    )
                    for entry in (staging / "plugin").rglob("*"):
                        entry.chmod(entry.stat().st_mode & ~0o222)
                    (staging / "plugin").chmod(
                        (staging / "plugin").stat().st_mode & ~0o222,
                    )
                    staging.rename(destination)
                finally:
                    if staging.exists():
                        remove_snapshot(staging)
            provenance = json.loads((destination / "provenance.json").read_text())
            if (
                provenance["digest"] != digest
                or inventory(destination / "plugin") != before
            ):
                msg = "stored bundle failed integrity validation"
                raise ValueError(msg)
            lease = uuid.uuid4().hex
            atomic_json(
                self.root / "leases" / f"{lease}.json",
                {
                    "bundle": digest,
                    "ownerPid": owner_pid,
                    "ownerIdentity": identity,
                },
            )
            return {
                "lease": lease,
                "bundle": str(destination / "plugin"),
                "skillRoot": str(destination / "plugin/skills/ship-it"),
                "digest": digest,
                "version": manifest["version"],
            }

    def release(self, lease: str) -> dict:
        """Release one consumer token idempotently."""
        if len(lease) != LEASE_LENGTH or any(
            c not in "0123456789abcdef" for c in lease
        ):
            msg = "invalid lease ID"
            raise ValueError(msg)
        with self.locked():
            path = self.root / "leases" / f"{lease}.json"
            existed = path.exists()
            path.unlink(missing_ok=True)
            return {"released": existed}

    def collect(self, limit: int) -> dict:
        """Remove a bounded number of bundles without active consumers."""
        if not 1 <= limit <= MAX_CLEANUP:
            msg = "cleanup limit must be between 1 and 100 bundles"
            raise ValueError(msg)
        with self.locked():
            active = set()
            owners: dict[int, str | None] = {}
            for path in sorted((self.root / "leases").glob("*.json")):
                lease = json.loads(path.read_text())
                pid = lease["ownerPid"]
                if pid not in owners:
                    try:
                        owners[pid] = process_identity(pid)
                    except ValueError:
                        owners[pid] = None
                alive = owners[pid] == lease["ownerIdentity"]
                if alive:
                    active.add(lease["bundle"])
                else:
                    path.unlink()
            removed: list[str] = []
            for bundle in sorted((self.root / "bundles").iterdir()):
                if len(removed) >= limit:
                    break
                if bundle.name not in active:
                    remove_snapshot(bundle)
                    removed.append(bundle.name)
            abandoned = []
            for staging in sorted(self.root.glob(".staging-*"))[:limit]:
                remove_snapshot(staging)
                abandoned.append(staging.name)
            return {
                "removed": removed,
                "activeBundles": len(active),
                "abandonedSnapshots": abandoned,
            }


def main() -> int:
    """Run the bundle lifetime CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--store",
        type=Path,
        default=Path(
            os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")),
        )
        / "sai/ship-it/plugin-pins",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("supported")
    acquire = commands.add_parser("acquire")
    acquire.add_argument("--source", type=Path, required=True)
    acquire.add_argument("--owner-pid", type=int, required=True)
    release = commands.add_parser("release")
    release.add_argument("--lease", required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    if args.command == "supported":
        supported = fcntl is not None and Path("/bin/ps").is_file()
        print(json.dumps({"supported": supported}))
        return 0
    try:
        pins = Pins(args.store)
        if args.command == "acquire":
            result = pins.acquire(args.source, args.owner_pid)
        elif args.command == "release":
            result = pins.release(args.lease)
        else:
            result = pins.collect(args.limit)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    else:
        print(json.dumps(result, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
