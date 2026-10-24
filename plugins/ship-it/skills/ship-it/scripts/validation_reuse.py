#!/usr/bin/env python3
"""Capture relevant gate inputs and verify completed validation provenance.

Used by bookkeeping.py assess/reserve/finish under its checkpoint lock.
Input errors fail closed; no commands from an input manifest are executed.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final


class ConvergenceError(ValueError):
    """Invalid or unauthorized validation work."""


class InputUnavailableError(ConvergenceError):
    """A declared input dimension cannot establish committed coverage."""

    def __init__(self, dimension: str, message: str) -> None:
        """Retain the affected dimension for durable invalidation."""
        super().__init__(message)
        self.dimension = dimension


def require(condition: object, message: str) -> None:
    """Fail without mutating durable state when an invariant is unsatisfied."""
    if not condition:
        raise ConvergenceError(message)


GATES: Final[dict[str, str]] = {
    "review": "adversarial-review",
    "test": "adversarial-test",
    "quality": "local-checks",
}
MAX_NAMED_FILES: Final[int] = 100
DIMENSIONS: Final[tuple[str, ...]] = (
    "repository",
    "scope",
    "source",
    "dependencies",
    "command",
    "environment",
    "policy",
    "policyFacts",
    "acceptanceCriteria",
)


def digest(value: object) -> str:
    """Hash a canonical, deterministic JSON value."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()


def git(repository: Path, *arguments: str) -> bytes:
    """Read one of five fixed Git metadata commands with a timeout."""
    try:
        if arguments == ("rev-parse", "HEAD"):
            result = subprocess.run(
                ["/usr/bin/env", "git", "rev-parse", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                timeout=30,
            )
        elif arguments == ("rev-parse", "--git-common-dir"):
            result = subprocess.run(
                ["/usr/bin/env", "git", "rev-parse", "--git-common-dir"],
                cwd=repository,
                check=True,
                capture_output=True,
                timeout=30,
            )
        elif arguments == ("status", "--porcelain", "--untracked-files=all"):
            result = subprocess.run(
                [
                    "/usr/bin/env",
                    "git",
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                ],
                cwd=repository,
                check=True,
                capture_output=True,
                timeout=30,
            )
        elif arguments == ("rev-list", "HEAD"):
            result = subprocess.run(
                ["/usr/bin/env", "git", "rev-list", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                timeout=30,
            )
        elif arguments == ("ls-tree", "-r", "-z", "HEAD"):
            result = subprocess.run(
                ["/usr/bin/env", "git", "ls-tree", "-r", "-z", "HEAD"],
                cwd=repository,
                check=True,
                capture_output=True,
                timeout=30,
            )
        else:
            msg = "unsupported Git input read"
            raise ConvergenceError(msg)
    except (OSError, subprocess.SubprocessError) as error:
        msg = "cannot verify validation input repository"
        raise ConvergenceError(msg) from error
    else:
        return result.stdout


def git_stdin(repository: Path, topic: str, stdin: bytes) -> bytes:
    """Read history or tree differences for revisions supplied on stdin.

    Caller-controlled revisions never become command arguments.
    """
    try:
        if topic == "history":
            result = subprocess.run(
                ["/usr/bin/env", "git", "rev-list", "--topo-order", "--stdin"],
                cwd=repository,
                check=True,
                capture_output=True,
                input=stdin,
                timeout=30,
            )
        elif topic == "diff":
            result = subprocess.run(
                [
                    "/usr/bin/env",
                    "git",
                    "diff-tree",
                    "--stdin",
                    "--no-commit-id",
                    "-r",
                    "-z",
                    "--no-renames",
                    "--name-only",
                ],
                cwd=repository,
                check=True,
                capture_output=True,
                input=stdin,
                timeout=30,
            )
        else:
            msg = "unsupported Git input read"
            raise ConvergenceError(msg)
    except (OSError, subprocess.SubprocessError) as error:
        msg = "cannot verify validation input repository"
        raise ConvergenceError(msg) from error
    else:
        return result.stdout


def is_ancestor(repository: str, ancestor: object, descendant: object) -> bool:
    """Report whether a full commit ID is in the history of the checked-out HEAD."""
    if not isinstance(ancestor, str) or not isinstance(descendant, str):
        return False
    root = Path(repository)
    try:
        head = git(root, "rev-parse", "HEAD").decode().strip()
        history = git(root, "rev-list", "HEAD").decode().split()
    except ConvergenceError:
        return False
    return head == descendant and ancestor in history


def changed_paths(repository: Path, base: str) -> set[str]:
    """List files the change touches against its merge base, renames split."""
    dimension = "scope"
    try:
        head = git_stdin(repository, "history", b"HEAD\n").decode().split()
        shared = set(
            git_stdin(repository, "history", f"{base}\n".encode()).decode().split(),
        )
        pair = f"{next(commit for commit in head if commit in shared)} {head[0]}\n"
        output = git_stdin(repository, "diff", pair.encode())
    except (ConvergenceError, StopIteration, IndexError) as error:
        msg = "cannot read the change diff against the relevance base"
        raise InputUnavailableError(dimension, msg) from error
    return {
        path.decode(errors="surrogateescape") for path in output.split(b"\0") if path
    }


def under(roots: list[str], path: str) -> bool:
    """Report whether a committed path lies inside any declared root."""
    return any(root in (".", path) or path.startswith(root + "/") for root in roots)


def relevance_scope(spec: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the optional narrowing of source files to the diff and reads."""
    value = spec.get("relevance")
    if value is None:
        return None
    require(
        isinstance(value, dict) and set(value) == {"base", "reads"},
        "relevance requires exactly base and reads",
    )
    base = value["base"]
    require(
        isinstance(base, str)
        and bool(base)
        and not base.startswith(("-", "^"))
        and base.isprintable()
        and not any(character.isspace() for character in base),
        "relevance base must be one revision name",
    )
    return {"base": base, "reads": paths(value["reads"], "reads")}


def paths(value: object, name: str) -> list[str]:
    """Validate explicit repository-relative file or directory scopes."""
    if not isinstance(value, list):
        msg = f"{name} must be a path array"
        raise ConvergenceError(msg)
    for item in value:
        require(
            isinstance(item, str)
            and bool(item)
            and not PurePosixPath(item).is_absolute()
            and ".." not in PurePosixPath(item).parts
            and str(PurePosixPath(item)) == item,
            f"{name} requires normalized relative paths",
        )
    return sorted(set(value))


def capture(spec: dict[str, Any], revision: str, criteria: list[str]) -> dict[str, Any]:
    """Capture committed file identities, invocation and declared runtime inputs."""
    require(isinstance(spec.get("repository"), str), "inputs require repository")
    require(
        set(spec) - {"relevance"}
        == {
            "repository",
            "source",
            "dependencies",
            "policy",
            "command",
            "environment",
            "policyFacts",
        },
        "input manifest has missing or unknown fields",
    )
    relevance = relevance_scope(spec)
    repository = Path(spec["repository"]).resolve()
    require(
        git(repository, "rev-parse", "HEAD").decode().strip() == revision,
        "input repository HEAD must match current revision",
    )
    require(
        not git(repository, "status", "--porcelain", "--untracked-files=all"),
        "validation inputs require a clean committed worktree",
    )
    scope = {
        name: paths(spec.get(name), name)
        for name in ("source", "dependencies", "policy")
    }
    require(
        scope["source"] and scope["policy"],
        "source and policy scopes must be non-empty",
    )
    command = spec.get("command")
    require(
        isinstance(command, list)
        and command
        and all(isinstance(item, str) and item for item in command),
        "command must be a non-empty argument array",
    )
    environment = spec.get("environment")
    if not isinstance(environment, dict):
        msg = "environment must be an object"
        raise ConvergenceError(msg)
    variables = environment.get("variables")
    if not (
        isinstance(variables, list)
        and all(isinstance(name, str) and name for name in variables)
        and isinstance(environment.get("facts"), dict)
    ):
        msg = "environment requires variable names and runtime facts"
        raise ConvergenceError(msg)
    require(isinstance(spec.get("policyFacts"), dict), "inputs require policyFacts")
    entries = {}
    for entry in git(repository, "ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            entries[path.decode(errors="surrogateescape")] = metadata.decode()
    snapshot: dict[str, Any] = {
        "repository": str(
            (
                repository
                / git(repository, "rev-parse", "--git-common-dir").decode().strip()
            ).resolve(),
        ),
        "scope": scope,
        "command": command,
        "environment": {
            "variables": {
                name: digest(os.environ.get(name)) for name in sorted(set(variables))
            },
            "facts": environment["facts"],
        },
        "policyFacts": spec["policyFacts"],
        "acceptanceCriteria": criteria,
    }
    for name, selected in scope.items():
        for root in selected:
            if not any(
                root in (".", path) or path.startswith(root + "/") for path in entries
            ):
                msg = f"declared {name} path has no committed files: {root}"
                raise InputUnavailableError(name, msg)
        snapshot[name] = {
            path: content
            for path, content in sorted(entries.items())
            if under(selected, path)
        }
        require(
            not any(value.startswith("120000 ") for value in snapshot[name].values()),
            "symlink inputs require explicit external content evidence; cannot reuse",
        )
    if relevance is not None:
        snapshot["source"] = narrow_source(
            repository,
            relevance,
            scope["source"],
            entries,
        )
        snapshot["scope"] = {**scope, "relevance": {"reads": relevance["reads"]}}
        require(
            not any(
                value.startswith("120000 ") for value in snapshot["source"].values()
            ),
            "symlink inputs require explicit external content evidence; cannot reuse",
        )
    require(snapshot["source"], "source scope must contain committed files")
    require(
        git(repository, "rev-parse", "HEAD").decode().strip() == revision,
        "input repository changed during capture",
    )
    return snapshot


def narrow_source(
    repository: Path,
    relevance: dict[str, Any],
    roots: list[str],
    entries: dict[str, str],
) -> dict[str, str]:
    """Keep diff files inside the source roots plus every declared read.

    A deleted diff file stays as an explicit marker so a later re-add or an
    identical deletion elsewhere cannot look unchanged.
    """
    dimension = "source"
    reads = relevance["reads"]
    for root in reads:
        if not any(under([root], path) for path in entries):
            msg = f"declared reads path has no committed files: {root}"
            raise InputUnavailableError(dimension, msg)
    touched = {
        path
        for path in changed_paths(repository, relevance["base"])
        if under(roots, path)
    }
    if not touched:
        msg = "relevance base yields no changed file inside the source scope"
        raise InputUnavailableError(dimension, msg)
    selected = {
        path: content
        for path, content in sorted(entries.items())
        if path in touched or under(reads, path)
    }
    selected.update(dict.fromkeys(sorted(touched - set(entries)), "absent"))
    return selected


def changed_files(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, str]]:
    """Name each file whose identity differs between two input snapshots."""
    changes = []
    for dimension in ("source", "dependencies", "policy"):
        before, after = old.get(dimension), new.get(dimension)
        if not isinstance(before, dict) or not isinstance(after, dict):
            continue
        for path in sorted(set(before) | set(after)):
            if before.get(path) == after.get(path):
                continue
            if path not in before:
                change = "added"
            elif path not in after:
                change = "removed"
            else:
                change = "modified"
            changes.append({"dimension": dimension, "path": path, "change": change})
    return changes


def artifact(path: object) -> dict[str, str]:
    """Bind an output artifact to immutable content, failing closed on missing data."""
    if not (isinstance(path, str) and Path(path).is_absolute()):
        msg = "result requires absolute output path"
        raise ConvergenceError(msg)
    try:
        content = Path(path).read_bytes()
    except OSError as error:
        msg = "validation output is unavailable"
        raise ConvergenceError(msg) from error
    require(bool(content), "validation output must be non-empty")
    return {"path": path, "sha256": hashlib.sha256(content).hexdigest()}


def verified(operation: dict[str, Any]) -> bool:
    """Verify completion and the original artifact without upgrading its verdict."""
    if operation.get("status") != "completed" or not operation.get("outputArtifact"):
        return False
    try:
        return (
            artifact(operation["outputArtifact"].get("path"))
            == operation["outputArtifact"]
        )
    except ConvergenceError:
        return False


def assess(
    checkpoint: dict[str, Any],
    kind: str,
    revision: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Persist an observable validity decision for the latest gate result."""
    require(kind in GATES, "reuse supports review, test and quality only")
    require(
        revision == checkpoint["workflow"]["revision"],
        "assess requires current workflow revision",
    )
    previous = next(
        (
            operation
            for operation in reversed(checkpoint["convergence"]["reservations"])
            if operation["kind"] == kind
        ),
        None,
    )
    reasons = ["no-previous-result"]
    changes: list[dict[str, str]] = []
    if previous:
        old = previous.get("inputSnapshot")
        if isinstance(old, dict):
            changes = changed_files(old, snapshot)
        reasons = (
            [name for name in DIMENSIONS if old.get(name) != snapshot.get(name)]
            if isinstance(old, dict)
            else ["unverifiable-inputs"]
        )
        if not verified(previous):
            reasons.append(
                "unverifiable-output"
                if previous["status"] == "completed"
                else "incomplete-result",
            )
    decision = {
        "kind": kind,
        "revision": revision,
        "inputs": digest(snapshot),
        "previousOperation": previous["id"] if previous else None,
        "previousRevision": previous["revision"] if previous else None,
        "status": "invalid" if reasons else "reusable",
        "reasons": reasons,
    }
    if changes:
        decision["changedFileCount"] = len(changes)
        decision["changedFiles"] = changes[:MAX_NAMED_FILES]
    store_decision(checkpoint, decision)
    return decision


def store_decision(checkpoint: dict[str, Any], decision: dict[str, Any]) -> None:
    """Record derived invalidity independently from optional dispatch allowances."""
    decisions = checkpoint["convergence"].setdefault("validityDecisions", [])
    if not decisions or decisions[-1] != decision:
        decisions.append(decision)
    if decision["status"] == "invalid":
        for verdict in checkpoint["gateVerdicts"]:
            if (
                verdict.get("gate") == GATES[decision["kind"]]
                and verdict.get("status") == "passed"
            ):
                verdict.update(status="stale", invalidation=decision)


def unavailable_decision(
    checkpoint: dict[str, Any],
    kind: str,
    revision: str,
    error: ConvergenceError,
) -> None:
    """Invalidate requested gate coverage when committed input capture refuses."""
    if kind not in GATES or revision != checkpoint["workflow"]["revision"]:
        return
    previous = next(
        (
            receipt
            for receipt in reversed(checkpoint["convergence"]["reservations"])
            if receipt["kind"] == kind
        ),
        None,
    )
    reasons = ["unverifiable-inputs"]
    if isinstance(error, InputUnavailableError):
        reasons.insert(0, error.dimension)
    store_decision(
        checkpoint,
        {
            "kind": kind,
            "revision": revision,
            "inputs": previous["inputs"] if previous else None,
            "previousOperation": previous["id"] if previous else None,
            "previousRevision": previous["revision"] if previous else None,
            "status": "invalid",
            "reasons": reasons,
        },
    )


def review_provenance_valid(
    checkpoint: dict[str, Any],
    verdict: dict[str, Any],
    revision: str,
) -> bool:
    """Recheck reusable review evidence at the test prerequisite boundary."""
    provenance = verdict.get("provenance")
    if not isinstance(provenance, dict):
        return False
    operation = next(
        (
            receipt
            for receipt in checkpoint["convergence"]["reservations"]
            if receipt["id"] == provenance.get("operation")
            and receipt["kind"] == "review"
        ),
        None,
    )
    if operation is None:
        return False
    try:
        snapshot = capture(
            operation["inputManifest"],
            revision,
            checkpoint["task"].get("acceptanceCriteria", []),
        )
    except ConvergenceError as error:
        unavailable_decision(checkpoint, "review", revision, error)
        return False
    decision = assess(checkpoint, "review", revision, snapshot)
    return (
        decision["status"] == "reusable"
        and decision["previousOperation"] == operation["id"]
        and operation["result"]["verdict"] == "passed"
        and provenance.get("inputs") == operation["inputs"]
        and provenance.get("originalRevision") == operation["revision"]
        and provenance.get("outputArtifact") == operation["outputArtifact"]
    )


def attest(
    checkpoint: dict[str, Any],
    operation: dict[str, Any],
    revision: str,
) -> None:
    """Carry a verified passing result to this head with original provenance."""
    if operation["result"]["verdict"] != "passed":
        return
    gate = GATES[operation["kind"]]
    verdict = {
        "gate": gate,
        "status": "passed",
        "revision": revision,
        "provider": "ship-it-validation-reuse",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "provenance": {
            "operation": operation["id"],
            "originalRevision": operation["revision"],
            "inputs": operation["inputs"],
            "outputArtifact": operation["outputArtifact"],
        },
    }
    if not any(
        result.get("gate") == gate
        and result.get("revision") == revision
        and result.get("status") == "passed"
        and result.get("provenance") == verdict["provenance"]
        for result in checkpoint["gateVerdicts"]
    ):
        checkpoint["gateVerdicts"].append(verdict)
