#!/usr/bin/env python3
"""Emit and report privacy-safe ship-it workflow telemetry.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import token_cost

if TYPE_CHECKING:
    from collections.abc import Iterator


SCHEMA_VERSION: Final[int] = 4
SUPPORTED_SCHEMA_VERSIONS: Final[frozenset[int]] = frozenset({1, 2, 3, 4})
LOCK_TIMEOUT_SECONDS: Final[float] = 2.0
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
    "publish",
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
OBSERVATION_EVENTS: Final[tuple[str, ...]] = (
    "phase_started",
    "phase_completed",
    "wait_started",
    "wait_completed",
    "user_interruption",
)
WAIT_KINDS: Final[tuple[str, ...]] = (
    "approval",
    "hosted_service",
    "resource_queue",
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
    "ci_failures",
    "ci_recurrences",
    "ci_resolutions",
    "review_cycles",
    "test_runs",
    "full_quality_gate_runs",
    "user_interruptions",
)
SAFE_ID: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
SAFE_TASK_ID: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
RUN_ID: Final[re.Pattern[str]] = re.compile(r"^run_[0-9a-f]{24}$")


class UsageError(Exception):
    pass


def data_dir() -> Path:
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return root / "sai" / "ship-it" / "telemetry"


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as lock:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OSError("telemetry lock timed out") from None
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def validate_identifier(label: str, value: str) -> str:
    if not SAFE_ID.fullmatch(value) or "://" in value:
        raise UsageError(f"{label} must be 1-128 safe identifier characters")
    return value


def validate_task_id(value: str) -> str:
    if not SAFE_TASK_ID.fullmatch(value):
        raise UsageError("task id must be 1-128 opaque identifier characters")
    return value


def validate_opaque_identifier(label: str, value: str) -> str:
    if not SAFE_TASK_ID.fullmatch(value):
        raise UsageError(f"{label} must be 1-128 opaque identifier characters")
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


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    private_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def task_index_path(task_id: str) -> Path:
    digest = hashlib.sha256(task_id.encode()).hexdigest()
    return data_dir() / "tasks" / f"{digest}.json"


def indexed_run(task_id: str) -> dict[str, Any] | None:
    path = task_index_path(task_id)
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UsageError("cannot read task run index") from error
    if not isinstance(index, dict) or index.get("task_id") != task_id:
        raise UsageError("invalid task run index")
    return load_run(index.get("run_id", ""))


def discover_run(task_id: str) -> dict[str, Any] | None:
    runs = data_dir() / "runs"
    if not runs.is_dir():
        return None
    candidates: list[tuple[int, dict[str, Any]]] = []
    for path in runs.glob("run_*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("task_id") == task_id:
            candidates.append((path.stat().st_mtime_ns, value))
    if not candidates:
        return None
    candidate = max(candidates, key=lambda item: item[0])[1]
    return load_run(candidate.get("run_id", ""))


def load_run(run_id: str) -> dict[str, Any]:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise UsageError("run id has an invalid format")
    path = data_dir() / "runs" / f"{run_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise UsageError(f"unknown run id {run_id!r}") from None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
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


def append_event(path: Path, encoded: bytes) -> None:
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OSError("event log lock timed out") from None
                time.sleep(0.02)
        start = os.lseek(descriptor, 0, os.SEEK_END)
        remaining = memoryview(encoded)
        try:
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("event append made no progress")
                remaining = remaining[written:]
        except OSError:
            os.ftruncate(descriptor, start)
            raise
    finally:
        os.close(descriptor)


def event_in_log(path: Path, event_id: str) -> bool:
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return False
    except OSError as error:
        raise UsageError("cannot read telemetry event log") from error
    return f'"event_id":"{event_id}"'.encode() in content


def load_event(path: Path) -> dict[str, Any]:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise UsageError("cannot read existing telemetry event") from error
    except json.JSONDecodeError as error:
        raise UsageError("existing telemetry event is invalid") from error
    if not isinstance(event, dict):
        raise UsageError("existing telemetry event is not an object")
    return event


def persist_event(record: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    root = data_dir()
    events = root / "events"
    private_directory(events)
    event_path = events / f"{record['event_id']}.json"
    log_path = root / "events.ndjson"
    with exclusive_lock(event_path.with_suffix(".lock")):
        duplicate = event_path.exists()
        if duplicate:
            stored = load_event(event_path)
            needs_append = not event_in_log(log_path, stored["event_id"])
        else:
            private_json(event_path, record)
            stored = record
            needs_append = True
        if needs_append:
            encoded = (
                json.dumps(stored, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode()
            append_event(log_path, encoded)
    return duplicate, stored


def event_identifier(
    state: dict[str, Any],
    event: str,
    args: argparse.Namespace,
    outcome: str | None,
) -> str:
    observation_id = getattr(args, "observation_id", None)
    if observation_id is None:
        return f"evt_{secrets.token_hex(12)}"
    worker_id = getattr(args, "worker_id", None) or ""
    parts = [state["run_id"], event, args.phase, observation_id]
    if worker_id:
        parts.append(worker_id)
    if outcome is not None:
        parts.append(outcome)
    material = "\0".join(parts)
    return f"evt_{hashlib.sha256(material.encode()).hexdigest()[:24]}"


def emit(
    state: dict[str, Any],
    args: argparse.Namespace,
    event: str,
    outcome: str | None,
) -> dict[str, Any]:
    root = data_dir()
    private_directory(root)
    path = root / "events.ndjson"
    observation_id = getattr(args, "observation_id", None)
    worker_id = getattr(args, "worker_id", None)
    wait_kind = getattr(args, "wait_kind", None)
    if observation_id is not None:
        validate_opaque_identifier("observation id", observation_id)
    if worker_id is not None:
        validate_opaque_identifier("worker id", worker_id)
    record = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_identifier(state, event, args, outcome),
        "emitted_at": timestamp(),
        "run_id": state["run_id"],
        "task_id": state["task_id"],
        "event": event,
        "harness": validate_identifier("harness", getattr(args, "harness", None) or state["harness"]),
        "provider": validate_identifier("provider", getattr(args, "provider", None) or state["provider"]),
        "model": validate_identifier("model", getattr(args, "model", None) or state["model"]),
        "role": getattr(args, "role", None) or state["role"],
        "phase": args.phase,
        "observation_id": observation_id,
        "worker_id": worker_id,
        "wait_kind": wait_kind,
        "metrics": metric_values(args),
        "outcome": outcome,
        "usage": getattr(args, "usage", None),
    }
    duplicate, record = persist_event(record)
    return {"duplicate": duplicate, "event": record, "path": str(path)}


def begin(args: argparse.Namespace) -> dict[str, Any]:
    task_id = validate_task_id(args.task_id)
    runs = data_dir() / "runs"
    private_directory(runs)
    tasks = data_dir() / "tasks"
    private_directory(tasks)
    with exclusive_lock(runs / ".index.lock"):
        state = indexed_run(task_id) or discover_run(task_id)
        reactivate = (
            state is not None
            and state.get("status") == "finished"
            and state.get("outcome") == "blocked"
        )
        if state is None:
            state = {
                "run_id": f"run_{secrets.token_hex(12)}",
                "task_id": task_id,
                "harness": validate_identifier("harness", args.harness),
                "provider": validate_identifier("provider", args.provider),
                "model": validate_identifier("model", args.model),
                "role": args.role,
                "status": "active",
                "skill_version": json.loads(
                    (Path(__file__).resolve().parents[3] / "plugin.json").read_text(
                        encoding="utf-8",
                    )
                )["version"],
            }
            private_json(runs / f"{state['run_id']}.json", state)
        else:
            for field in ("harness", "provider", "model", "role"):
                setattr(args, field, state[field])
            if reactivate:
                state["status"] = "active"
                state.pop("outcome", None)
                atomic_json(runs / f"{state['run_id']}.json", state)
        atomic_json(
            task_index_path(task_id),
            {"run_id": state["run_id"], "task_id": task_id},
        )
    args.phase = "resolve"
    args.observation_id = "run"
    args.worker_id = None
    args.wait_kind = None
    result = emit(state, args, "run_started", None)
    result["run_id"] = state["run_id"]
    return result


def record(args: argparse.Namespace) -> dict:
    return emit(load_run(args.run_id), args, "phase_completed", None)


def observe(args: argparse.Namespace) -> dict[str, Any]:
    wait_event = args.event in ("wait_started", "wait_completed")
    if wait_event != (args.wait_kind is not None):
        requirement = "requires" if wait_event else "does not accept"
        raise UsageError(f"{args.event} {requirement} --wait-kind")
    state = load_run(args.run_id)
    effective_role = args.role or state["role"]
    phase_event = args.event in ("phase_started", "phase_completed")
    if phase_event and effective_role != "primary" and args.worker_id is None:
        raise UsageError("non-primary phase observations require --worker-id")
    return emit(state, args, args.event, None)


def finish(args: argparse.Namespace) -> dict[str, Any]:
    args.phase = "complete"
    args.observation_id = "run"
    args.worker_id = None
    args.wait_kind = None
    run_path = data_dir() / "runs" / f"{args.run_id}.json"
    with exclusive_lock(run_path.with_suffix(".lock")):
        state = load_run(args.run_id)
        if state.get("status") == "finished" and state.get("outcome") != args.outcome:
            raise UsageError("run already finished with a different outcome")
        result = emit(state, args, "run_finished", args.outcome)
        state["status"] = "finished"
        state["outcome"] = args.outcome
        atomic_json(run_path, state)
    return result


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise UsageError("telemetry event timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise UsageError("telemetry event timestamp is invalid") from error
    if parsed.tzinfo is None:
        raise UsageError("telemetry event timestamp must include a timezone")
    return parsed


def milliseconds(start: datetime, end: datetime) -> int:
    return max(0, round((end - start).total_seconds() * 1000))


def merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def interval_total(intervals: list[tuple[datetime, datetime]]) -> int:
    return sum(milliseconds(start, end) for start, end in merge_intervals(intervals))


def overlap_total(
    left: list[tuple[datetime, datetime]],
    right: list[tuple[datetime, datetime]],
) -> int:
    overlaps: list[tuple[datetime, datetime]] = []
    for left_start, left_end in merge_intervals(left):
        for right_start, right_end in merge_intervals(right):
            start, end = max(left_start, right_start), min(left_end, right_end)
            if start < end:
                overlaps.append((start, end))
    return interval_total(overlaps)


def read_events(run_id: str) -> list[dict[str, Any]]:
    path = data_dir() / "events.ndjson"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    except (OSError, UnicodeDecodeError) as error:
        raise UsageError("cannot read telemetry event log") from error
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise UsageError("telemetry event log contains invalid JSON") from error
        if not isinstance(event, dict):
            raise UsageError("telemetry event log contains a non-object")
        event_id = event.get("event_id")
        if event.get("run_id") != run_id or not isinstance(event_id, str):
            continue
        version = event.get("schema_version")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise UsageError(f"unsupported telemetry schema version: {version!r}")
        if event_id in seen:
            continue
        seen.add(event_id)
        events.append(event)
    event_dir = data_dir() / "events"
    if event_dir.is_dir():
        for event_path in event_dir.glob("evt_*.json"):
            event = load_event(event_path)
            event_id = event.get("event_id")
            if event.get("run_id") != run_id or not isinstance(event_id, str):
                continue
            version = event.get("schema_version")
            if version not in SUPPORTED_SCHEMA_VERSIONS:
                raise UsageError(f"unsupported telemetry schema version: {version!r}")
            if event_id not in seen:
                seen.add(event_id)
                events.append(event)
    if not events:
        raise UsageError(f"no telemetry events found for run {run_id!r}")
    return sorted(events, key=lambda event: (parse_timestamp(event.get("emitted_at")), event["event_id"]))


def latest_counter(events: list[dict[str, Any]], name: str) -> int | None:
    values = [
        metrics[name]
        for event in events
        if isinstance((metrics := event.get("metrics")), dict)
        and type(metrics.get(name)) is int
    ]
    return max(values) if values else None


def repeated_count(events: list[dict[str, Any]], counter: str) -> int | None:
    value = latest_counter(events, counter)
    return None if value is None else max(0, value - 1)


def build_report(run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    starts: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    primary_by_phase: dict[str, list[tuple[datetime, datetime]]] = {
        phase: [] for phase in PHASES
    }
    worker_intervals: dict[str, list[tuple[datetime, datetime]]] = {}
    waits: dict[str, list[tuple[datetime, datetime]]] = {
        kind: [] for kind in WAIT_KINDS
    }
    incomplete = 0
    interruptions = 0
    has_timing_observation = False
    run_started: datetime | None = None
    run_finished: datetime | None = None

    for event in events:
        occurred = parse_timestamp(event.get("emitted_at"))
        event_name = event.get("event")
        if event_name == "run_started" and run_started is None:
            run_started = occurred
        elif event_name == "run_finished":
            run_finished = occurred
        elif event_name == "user_interruption":
            interruptions += 1

        observation_id = event.get("observation_id")
        if not isinstance(observation_id, str):
            continue
        if event_name in ("phase_started", "wait_started"):
            has_timing_observation = True
            kind = "phase" if event_name == "phase_started" else "wait"
            starts.setdefault((kind, observation_id, event.get("worker_id")), event)
            continue
        if event_name not in ("phase_completed", "wait_completed"):
            continue
        kind = "phase" if event_name == "phase_completed" else "wait"
        started = starts.pop(
            (kind, observation_id, event.get("worker_id")),
            None,
        )
        if started is None:
            incomplete += 1
            continue
        start = parse_timestamp(started.get("emitted_at"))
        if occurred < start:
            incomplete += 1
            continue
        interval = (start, occurred)
        if kind == "wait":
            wait_kind = started.get("wait_kind")
            if wait_kind != event.get("wait_kind") or wait_kind not in waits:
                incomplete += 1
                continue
            waits[wait_kind].append(interval)
            continue
        phase = started.get("phase")
        if phase != event.get("phase") or phase not in primary_by_phase:
            incomplete += 1
            continue
        worker_id = started.get("worker_id")
        if worker_id != event.get("worker_id"):
            incomplete += 1
            continue
        if isinstance(worker_id, str):
            worker_intervals.setdefault(worker_id, []).append(interval)
        else:
            primary_by_phase[phase].append(interval)

    incomplete += len(starts)
    primary_intervals = [
        interval
        for phase_intervals in primary_by_phase.values()
        for interval in phase_intervals
    ]
    all_waits = [interval for wait_intervals in waits.values() for interval in wait_intervals]
    primary_total = interval_total(primary_intervals) if primary_intervals else None
    active_work = (
        None
        if primary_total is None
        else max(0, primary_total - overlap_total(primary_intervals, all_waits))
    )
    metric_interruptions = latest_counter(events, "user_interruptions")
    interruption_values = [interruptions] if interruptions else []
    if metric_interruptions is not None:
        interruption_values.append(metric_interruptions)
    interruption_count = max(interruption_values) if interruption_values else None
    return {
        "run_id": run_id,
        "delivery_elapsed_ms": (
            milliseconds(run_started, run_finished)
            if run_started is not None and run_finished is not None
            else None
        ),
        "active_work_ms": active_work,
        "phase_durations_ms": {
            phase: interval_total(intervals) if intervals else None
            for phase, intervals in primary_by_phase.items()
        },
        "observed_wait_ms": {
            kind: interval_total(intervals) if intervals else None
            for kind, intervals in waits.items()
        },
        "worker_durations_ms": (
            {
                worker: interval_total(intervals)
                for worker, intervals in sorted(worker_intervals.items())
            }
            if worker_intervals
            else None
        ),
        "repeated_gate_counts": {
            "review": repeated_count(events, "review_cycles"),
            "test": repeated_count(events, "test_runs"),
            "quality": repeated_count(events, "full_quality_gate_runs"),
        },
        "user_interruptions": interruption_count,
        "observations_complete": has_timing_observation and incomplete == 0,
        "incomplete_observation_count": incomplete,
        "event_count": len(events),
        "token_cost": token_cost.summarize(events),
    }


def usage(args: argparse.Namespace) -> dict[str, Any]:
    """Persist one disjoint host usage observation."""
    args.usage = token_cost.validate_usage(args)
    args.wait_kind = None
    state = load_run(args.run_id)
    if (args.role or state["role"]) != "primary" and args.worker_id is None:
        message = "non-primary usage requires --worker-id"
        raise UsageError(message)
    return emit(state, args, "usage_recorded", None)


def report(args: argparse.Namespace) -> dict[str, Any]:
    if args.task_id is not None:
        task_id = validate_task_id(args.task_id)
        state = indexed_run(task_id) or discover_run(task_id)
        if state is None:
            raise UsageError(f"no run found for task id {task_id!r}")
        run_id = state["run_id"]
    else:
        run_id = args.run_id
        state = load_run(run_id)
    result = build_report(run_id, read_events(run_id))
    result["skill_version"] = state.get("skill_version")
    return result


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

    observe_parser = commands.add_parser(
        "observe",
        help="record an idempotent phase, wait, or interruption observation",
    )
    observe_parser.add_argument("--run-id", required=True)
    observe_parser.add_argument("--event", choices=OBSERVATION_EVENTS, required=True)
    observe_parser.add_argument("--phase", choices=PHASES, required=True)
    observe_parser.add_argument("--observation-id", required=True)
    observe_parser.add_argument("--worker-id")
    observe_parser.add_argument("--wait-kind", choices=WAIT_KINDS)
    add_identity(observe_parser, required=False)
    add_metrics(observe_parser)
    observe_parser.set_defaults(handler=observe)

    finish_parser = commands.add_parser("finish", help="finish a run with its outcome")
    finish_parser.add_argument("--run-id", required=True)
    finish_parser.add_argument("--outcome", choices=OUTCOMES, required=True)
    add_identity(finish_parser, required=False)
    add_metrics(finish_parser)
    finish_parser.set_defaults(handler=finish)

    usage_parser = commands.add_parser(
        "usage", help="record one non-overlapping host usage delta",
    )
    usage_parser.add_argument("--run-id", required=True)
    usage_parser.add_argument("--phase", choices=PHASES, required=True)
    usage_parser.add_argument("--observation-id", required=True)
    usage_parser.add_argument("--worker-id")
    add_identity(usage_parser, required=False)
    for category in token_cost.CATEGORIES:
        usage_parser.add_argument(f"--{category.replace('_', '-')}-tokens", type=int)
        usage_parser.add_argument(f"--{category.replace('_', '-')}-price", type=str)
    usage_parser.set_defaults(handler=usage)

    report_parser = commands.add_parser("report", help="report one local run")
    report_source = report_parser.add_mutually_exclusive_group(required=True)
    report_source.add_argument("--run-id")
    report_source.add_argument("--task-id")
    report_parser.add_argument("--markdown", action="store_true")
    report_parser.set_defaults(handler=report)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        result = args.handler(args)
        if args.command == "report" and args.markdown:
            version = result["skill_version"] or "unknown"
            validate_opaque_identifier("plugin version", version)
            print(token_cost.markdown(result, version))
        else:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (UsageError, token_cost.UsageError) as error:
        print(f"telemetry: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"telemetry: cannot persist event: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
