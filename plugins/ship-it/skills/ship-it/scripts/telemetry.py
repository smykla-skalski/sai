#!/usr/bin/env python3
"""Emit privacy-safe ship-it workflow telemetry as NDJSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


SCHEMA_VERSION: Final[int] = 1
ROLES: Final[tuple[str, ...]] = (
    "primary",
    "subagent",
    "validator",
    "guardian",
    "synthetic",
    "probe",
)
PHASES: Final[tuple[str, ...]] = (
    "resolve",
    "orchestrate",
    "explore",
    "branch",
    "implement",
    "review",
    "test",
    "pr",
    "wait",
    "fix",
    "merge",
    "complete",
)
OUTCOMES: Final[tuple[str, ...]] = (
    "accepted",
    "rejected",
    "blocked",
    "cancelled",
    "failed",
)
COUNTERS: Final[tuple[str, ...]] = (
    "turns",
    "tool_calls",
    "permission_decisions",
    "compactions",
    "input_tokens",
    "output_tokens",
    "elapsed_ms",
    "retries",
    "findings",
    "checks",
    "human_interventions",
    "failed_commands",
    "approval_wait_ms",
)
SAFE_ID: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
SAFE_TASK_ID: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
RUN_ID: Final[re.Pattern[str]] = re.compile(r"^run_[0-9a-f]{24}$")


class UsageError(Exception):
    pass


def data_dir() -> Path:
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return root / "sai" / "ship-it" / "telemetry"


def validate_identifier(label: str, value: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise UsageError(f"{label} must be 1-128 safe identifier characters")
    return value


def validate_task_id(value: str) -> str:
    if not SAFE_TASK_ID.fullmatch(value):
        raise UsageError("task id must be 1-128 opaque identifier characters")
    return value


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def private_json(path: Path, value: dict) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def load_run(run_id: str) -> dict:
    if not RUN_ID.fullmatch(run_id):
        raise UsageError("run id has an invalid format")
    path = data_dir() / "runs" / f"{run_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise UsageError(f"unknown run id {run_id!r}") from None
    except (OSError, json.JSONDecodeError):
        raise UsageError(f"cannot read run state for {run_id!r}") from None
    if not isinstance(value, dict) or value.get("run_id") != run_id:
        raise UsageError(f"invalid run state for {run_id!r}")
    try:
        validate_task_id(value["task_id"])
        validate_identifier("harness", value["harness"])
        validate_identifier("provider", value["provider"])
        validate_identifier("model", value["model"])
        if value["role"] not in ROLES:
            raise UsageError("role in run state is invalid")
    except (KeyError, TypeError):
        raise UsageError(f"invalid run state for {run_id!r}") from None
    return value


def metric_values(args: argparse.Namespace) -> dict[str, int | None]:
    values: dict[str, int | None] = {}
    for name in COUNTERS:
        value = getattr(args, name, None)
        if value is not None and value < 0:
            raise UsageError(f"{name.replace('_', '-')} cannot be negative")
        values[name] = value
    return values


def emit(state: dict, args: argparse.Namespace, event: str, outcome: str | None) -> dict:
    root = data_dir()
    private_directory(root)
    path = root / "events.ndjson"
    record = {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"evt_{secrets.token_hex(12)}",
        "emitted_at": timestamp(),
        "run_id": state["run_id"],
        "task_id": state["task_id"],
        "event": event,
        "harness": validate_identifier("harness", getattr(args, "harness", None) or state["harness"]),
        "provider": validate_identifier("provider", getattr(args, "provider", None) or state["provider"]),
        "model": validate_identifier("model", getattr(args, "model", None) or state["model"]),
        "role": getattr(args, "role", None) or state["role"],
        "phase": args.phase,
        "metrics": metric_values(args),
        "outcome": outcome,
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, encoded)
    finally:
        os.close(descriptor)
    return {"event": record, "path": str(path)}


def begin(args: argparse.Namespace) -> dict:
    state = {
        "run_id": f"run_{secrets.token_hex(12)}",
        "task_id": validate_task_id(args.task_id),
        "harness": validate_identifier("harness", args.harness),
        "provider": validate_identifier("provider", args.provider),
        "model": validate_identifier("model", args.model),
        "role": args.role,
    }
    runs = data_dir() / "runs"
    private_directory(runs)
    private_json(runs / f"{state['run_id']}.json", state)
    args.phase = "resolve"
    result = emit(state, args, "run_started", None)
    result["run_id"] = state["run_id"]
    return result


def record(args: argparse.Namespace) -> dict:
    return emit(load_run(args.run_id), args, "phase_completed", None)


def finish(args: argparse.Namespace) -> dict:
    args.phase = "complete"
    return emit(load_run(args.run_id), args, "run_finished", args.outcome)


def add_identity(parser: argparse.ArgumentParser, required: bool) -> None:
    parser.add_argument("--harness", required=required)
    parser.add_argument("--provider", required=required)
    parser.add_argument("--model", required=required)
    parser.add_argument("--role", choices=ROLES, required=required)


def add_metrics(parser: argparse.ArgumentParser) -> None:
    for name in COUNTERS:
        parser.add_argument(f"--{name.replace('_', '-')}", type=int)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    begin_parser = commands.add_parser("begin", help="start a run and emit run_started")
    begin_parser.add_argument("--task-id", required=True)
    add_identity(begin_parser, required=True)
    add_metrics(begin_parser)
    begin_parser.set_defaults(handler=begin)

    record_parser = commands.add_parser("record", help="emit a completed phase snapshot")
    record_parser.add_argument("--run-id", required=True)
    record_parser.add_argument("--phase", choices=PHASES, required=True)
    add_identity(record_parser, required=False)
    add_metrics(record_parser)
    record_parser.set_defaults(handler=record)

    finish_parser = commands.add_parser("finish", help="finish a run with its outcome")
    finish_parser.add_argument("--run-id", required=True)
    finish_parser.add_argument("--outcome", choices=OUTCOMES, required=True)
    add_identity(finish_parser, required=False)
    add_metrics(finish_parser)
    finish_parser.set_defaults(handler=finish)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        print(json.dumps(args.handler(args), sort_keys=True, separators=(",", ":")))
        return 0
    except UsageError as error:
        print(f"telemetry: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
