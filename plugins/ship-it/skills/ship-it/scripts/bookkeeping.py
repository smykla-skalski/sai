#!/usr/bin/env python3
"""Resolve opt-in bookkeeping and atomically transition a ship-it checkpoint.

Usage:
  bookkeeping.py policy --repository PATH [--enable FEATURE,...]
  bookkeeping.py transition --checkpoint FILE --phase PHASE --status STATUS
      --next-action TEXT [--revision SHA]

Output is one compact JSON result on stdout. Input or validation errors are
reported on stderr and exit 2; successful policy resolution or transition
exits 0.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

FEATURES: Final[tuple[str, ...]] = ("claims", "evidence", "telemetry")
POLICY_PATH: Final[Path] = Path(".sai/ship-it-bookkeeping.json")
VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {"active", "blocked", "completed", "cancelled", "failed"},
)
VALID_PHASES: Final[frozenset[str]] = frozenset(
    {
        "resolve",
        "orchestrate",
        "explore",
        "branch",
        "implement",
        "publish",
        "review",
        "test",
        "pr",
        "wait",
        "complete",
    },
)
TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "cancelled", "failed"},
)
REQUIRED_CHECKPOINT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schemaVersion",
        "checkpointId",
        "task",
        "repository",
        "workflow",
        "delivery",
        "evidence",
        "claim",
        "bookkeeping",
        "risk",
        "releasePolicy",
        "hostedReviewDecision",
        "convergence",
        "ciTriage",
        "orchestration",
        "outcome",
        "createdAt",
        "updatedAt",
    },
)
REQUIRED_WORKFLOW_FIELDS: Final[frozenset[str]] = frozenset(
    {"phase", "status", "revision", "blocker", "unresolvedQuestions", "nextAction"},
)


class BookkeepingError(ValueError):
    """A deterministic input or state validation error."""


def parse_enabled(value: str) -> set[str]:
    """Parse and validate an explicit comma-separated feature list."""
    enabled = {item.strip() for item in value.split(",") if item.strip()}
    unknown = enabled.difference(FEATURES)
    if unknown:
        names = ", ".join(sorted(unknown))
        message = f"unknown bookkeeping feature: {names}"
        raise BookkeepingError(message)
    return enabled


def load_object(path: Path) -> dict[str, Any]:
    """Load a JSON object or raise a deterministic validation error."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        message = f"cannot read JSON object {path}: {error}"
        raise BookkeepingError(message) from error
    if not isinstance(value, dict):
        message = f"expected JSON object: {path}"
        raise BookkeepingError(message)
    return value


def resolve_policy(repository: Path, explicit: set[str]) -> dict[str, Any]:
    """Resolve optional bookkeeping features from repo policy and user input."""
    values = dict.fromkeys(FEATURES, False)
    source = "bundled default"
    policy_file = repository / POLICY_PATH
    if policy_file.is_file():
        raw = load_object(policy_file)
        unknown = set(raw).difference(FEATURES)
        if unknown:
            names = ", ".join(sorted(unknown))
            message = f"unknown policy field: {names}"
            raise BookkeepingError(message)
        for feature in FEATURES:
            if feature in raw:
                if not isinstance(raw[feature], bool):
                    message = f"policy field {feature} must be boolean"
                    raise BookkeepingError(message)
                values[feature] = raw[feature]
        source = POLICY_PATH.as_posix()
    if explicit:
        for feature in explicit:
            values[feature] = True
        source = "explicit user request"
    return {**values, "policySource": source}


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    """Replace a JSON file atomically while retaining its previous version."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                value,
                stream,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_workflow(workflow: dict[str, Any]) -> None:
    """Validate the workflow object and its status coupling."""
    missing_workflow = REQUIRED_WORKFLOW_FIELDS.difference(workflow)
    if missing_workflow:
        names = ", ".join(sorted(missing_workflow))
        message = f"checkpoint.workflow missing required fields: {names}"
        raise BookkeepingError(message)

    phase = workflow["phase"]
    status = workflow["status"]
    blocker = workflow["blocker"]
    next_action = workflow["nextAction"]
    if phase not in VALID_PHASES:
        message = f"invalid workflow phase: {phase}"
        raise BookkeepingError(message)
    if status not in VALID_STATUSES:
        message = f"invalid workflow status: {status}"
        raise BookkeepingError(message)
    if not isinstance(next_action, str) or not next_action.strip():
        message = "checkpoint.workflow.nextAction must be non-empty"
        raise BookkeepingError(message)
    if status == "blocked" and (not isinstance(blocker, str) or not blocker.strip()):
        message = "blocked workflow requires a non-empty blocker"
        raise BookkeepingError(message)
    if status != "blocked" and blocker is not None:
        message = "non-blocked workflow requires a null blocker"
        raise BookkeepingError(message)


def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate fields and invariants affected by a workflow transition."""
    missing = REQUIRED_CHECKPOINT_FIELDS.difference(checkpoint)
    if missing:
        names = ", ".join(sorted(missing))
        message = f"checkpoint missing required fields: {names}"
        raise BookkeepingError(message)

    workflow = checkpoint.get("workflow")
    if not isinstance(workflow, dict):
        message = "checkpoint.workflow must be an object"
        raise BookkeepingError(message)
    validate_workflow(workflow)

    phase = workflow["phase"]
    status = workflow["status"]
    if phase == "complete":
        terminal_outcome = status in TERMINAL_STATUSES and isinstance(
            checkpoint["outcome"],
            dict,
        )
        if not terminal_outcome:
            message = "complete workflow requires terminal status and outcome"
            raise BookkeepingError(message)
    elif status in TERMINAL_STATUSES or checkpoint["outcome"] is not None:
        message = "terminal status and outcome require phase complete"
        raise BookkeepingError(message)


def transition(args: argparse.Namespace) -> dict[str, Any]:
    """Apply one validated workflow transition to a checkpoint."""
    checkpoint_path = Path(args.checkpoint).resolve()
    checkpoint = load_object(checkpoint_path)
    validate_checkpoint(checkpoint)
    workflow = checkpoint["workflow"]
    if args.phase not in VALID_PHASES:
        message = f"invalid workflow phase: {args.phase}"
        raise BookkeepingError(message)
    if args.status not in VALID_STATUSES:
        message = f"invalid workflow status: {args.status}"
        raise BookkeepingError(message)
    if args.status == "blocked" and not args.blocker:
        message = "--blocker is required for blocked status"
        raise BookkeepingError(message)
    if args.status != "blocked" and args.blocker:
        message = "--blocker is valid only for blocked status"
        raise BookkeepingError(message)
    workflow["phase"] = args.phase
    workflow["status"] = args.status
    workflow["blocker"] = args.blocker
    workflow["nextAction"] = args.next_action
    if args.revision is not None:
        workflow["revision"] = args.revision
    checkpoint["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    validate_checkpoint(checkpoint)
    atomic_write(checkpoint_path, checkpoint)
    return {
        "checkpoint": str(checkpoint_path),
        "phase": args.phase,
        "status": args.status,
        "transition": "applied",
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    policy = commands.add_parser("policy", help="resolve bookkeeping policy")
    policy.add_argument("--repository", required=True)
    policy.add_argument("--enable", default="")

    update = commands.add_parser(
        "transition",
        help="atomically update checkpoint workflow",
    )
    update.add_argument("--checkpoint", required=True)
    update.add_argument("--phase", required=True)
    update.add_argument("--status", required=True)
    update.add_argument("--blocker")
    update.add_argument("--next-action", required=True)
    update.add_argument("--revision")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the selected bookkeeping command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "policy":
            result = resolve_policy(
                Path(args.repository).resolve(),
                parse_enabled(args.enable),
            )
        else:
            result = transition(args)
    except BookkeepingError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
