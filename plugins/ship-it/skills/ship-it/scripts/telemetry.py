#!/usr/bin/env python3
"""Emit and report privacy-safe ship-it workflow telemetry.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import os
import re
import secrets
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import token_cost

if TYPE_CHECKING:
    from collections.abc import Iterator


SCHEMA_VERSION: Final[int] = 4
SUPPORTED_SCHEMA_VERSIONS: Final[frozenset[int]] = frozenset({1, 2, 3, 4})
LOCK_TIMEOUT_SECONDS: Final[float] = 2.0
LOCK_RETRY_SECONDS: Final[float] = 0.02
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
SAFE_TASK_ID: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$",
)
RUN_ID: Final[re.Pattern[str]] = re.compile(r"^run_[0-9a-f]{24}$")


class UsageError(Exception):
    """Reject unsafe input or unreadable telemetry state."""


def data_dir() -> Path:
    """Return the telemetry root under XDG_DATA_HOME or ~/.local/share."""
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return root / "sai" / "ship-it" / "telemetry"


def _lock(descriptor: int, timeout_message: str) -> None:
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise OSError(timeout_message) from None
            time.sleep(LOCK_RETRY_SECONDS)


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive flock on path; raise OSError when it stays busy."""
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as lock:
        _lock(lock.fileno(), "telemetry lock timed out")
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def validate_identifier(label: str, value: str) -> str:
    """Return value when it is a safe identifier that is not a URL."""
    if not SAFE_ID.fullmatch(value) or "://" in value:
        msg = f"{label} must be 1-128 safe identifier characters"
        raise UsageError(msg)
    return value


def validate_task_id(value: str) -> str:
    """Return value when it is a safe opaque task id."""
    if not SAFE_TASK_ID.fullmatch(value):
        msg = "task id must be 1-128 opaque identifier characters"
        raise UsageError(msg)
    return value


def validate_opaque_identifier(label: str, value: str) -> str:
    """Return value when it is a safe opaque identifier, which excludes / and :."""
    if not SAFE_TASK_ID.fullmatch(value):
        msg = f"{label} must be 1-128 opaque identifier characters"
        raise UsageError(msg)
    return value


def timestamp() -> str:
    """Return the current UTC time as ISO 8601 with milliseconds and a Z suffix."""
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def private_directory(path: Path) -> None:
    """Create path if needed and restrict it to the owner."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def private_json(path: Path, value: dict) -> None:
    """Write value as compact JSON to a new owner-only file; fail if it exists."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Replace path with compact owner-only JSON through a synced temporary file."""
    private_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
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
    """Return the index file of task_id, named by its hash to keep the id private."""
    digest = hashlib.sha256(task_id.encode()).hexdigest()
    return data_dir() / "tasks" / f"{digest}.json"


def indexed_run(task_id: str) -> dict[str, Any] | None:
    """Return the run state the task index points to, or None without an index."""
    path = task_index_path(task_id)
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        msg = "cannot read task run index"
        raise UsageError(msg) from error
    if not isinstance(index, dict) or index.get("task_id") != task_id:
        msg = "invalid task run index"
        raise UsageError(msg)
    return load_run(index.get("run_id", ""))


def discover_run(task_id: str) -> dict[str, Any] | None:
    """Return the newest readable run state of task_id, or None."""
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
    """Return the validated state of run_id; raise UsageError if it is unusable."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        msg = "run id has an invalid format"
        raise UsageError(msg)
    path = data_dir() / "runs" / f"{run_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        msg = f"unknown run id {run_id!r}"
        raise UsageError(msg) from None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        msg = f"cannot read run state for {run_id!r}"
        raise UsageError(msg) from None
    if not isinstance(value, dict) or value.get("run_id") != run_id:
        msg = f"invalid run state for {run_id!r}"
        raise UsageError(msg)
    try:
        validate_task_id(value["task_id"])
        validate_identifier("harness", value["harness"])
        validate_identifier("provider", value["provider"])
        validate_identifier("model", value["model"])
        if value["role"] not in ROLES:
            msg = "role in run state is invalid"
            raise UsageError(msg)
    except (KeyError, TypeError):
        msg = f"invalid run state for {run_id!r}"
        raise UsageError(msg) from None
    return value


def metric_values(args: argparse.Namespace) -> dict[str, int | None]:
    """Return every counter from args, None when absent; reject negatives."""
    values: dict[str, int | None] = {}
    for name in COUNTERS:
        value = getattr(args, name, None)
        if value is not None and value < 0:
            msg = f"{name.replace('_', '-')} cannot be negative"
            raise UsageError(msg)
        values[name] = value
    return values


def _write_all(descriptor: int, encoded: bytes) -> None:
    remaining = memoryview(encoded)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            msg = "event append made no progress"
            raise OSError(msg)
        remaining = remaining[written:]


def append_event(path: Path, encoded: bytes) -> None:
    """Append encoded to the log under a lock; truncate a partial write."""
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        _lock(descriptor, "event log lock timed out")
        start = os.lseek(descriptor, 0, os.SEEK_END)
        try:
            _write_all(descriptor, encoded)
        except OSError:
            os.ftruncate(descriptor, start)
            raise
    finally:
        os.close(descriptor)


def event_in_log(path: Path, event_id: str) -> bool:
    """Return whether the compact log at path holds event_id."""
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return False
    except OSError as error:
        msg = "cannot read telemetry event log"
        raise UsageError(msg) from error
    return f'"event_id":"{event_id}"'.encode() in content


def load_event(path: Path) -> dict[str, Any]:
    """Return the stored event object at path; raise UsageError if unusable."""
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        msg = "cannot read existing telemetry event"
        raise UsageError(msg) from error
    except json.JSONDecodeError as error:
        msg = "existing telemetry event is invalid"
        raise UsageError(msg) from error
    if not isinstance(event, dict):
        msg = "existing telemetry event is not an object"
        raise UsageError(msg)
    return event


def persist_event(record: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Store record once and make sure the log holds it.

    Return whether the event already existed and the stored copy, which wins
    over record on a duplicate.
    """
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
    """Return a stable id for an observation, or a random id without one."""
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


def _identity(args: argparse.Namespace, state: dict[str, Any], label: str) -> str:
    return validate_identifier(label, getattr(args, label, None) or state[label])


def emit(
    state: dict[str, Any],
    args: argparse.Namespace,
    event: str,
    outcome: str | None,
) -> dict[str, Any]:
    """Persist one event and return it with its duplicate flag and log path."""
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
        "harness": _identity(args, state, "harness"),
        "provider": _identity(args, state, "provider"),
        "model": _identity(args, state, "model"),
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
    """Start or resume the run of a task and emit run_started.

    A resumed run keeps its stored identity, and a run that finished blocked
    becomes active again.
    """
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
                    ),
                )["version"],
            }
            private_json(runs / f"{state['run_id']}.json", state)
        else:
            for name in ("harness", "provider", "model", "role"):
                setattr(args, name, state[name])
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
    """Emit a phase_completed snapshot for an existing run."""
    return emit(load_run(args.run_id), args, "phase_completed", None)


def observe(args: argparse.Namespace) -> dict[str, Any]:
    """Emit an idempotent phase, wait or interruption observation.

    Wait events require a wait kind and other events reject one; non-primary
    phase events require a worker id.
    """
    wait_event = args.event in ("wait_started", "wait_completed")
    if wait_event != (args.wait_kind is not None):
        requirement = "requires" if wait_event else "does not accept"
        msg = f"{args.event} {requirement} --wait-kind"
        raise UsageError(msg)
    state = load_run(args.run_id)
    effective_role = args.role or state["role"]
    phase_event = args.event in ("phase_started", "phase_completed")
    if phase_event and effective_role != "primary" and args.worker_id is None:
        msg = "non-primary phase observations require --worker-id"
        raise UsageError(msg)
    return emit(state, args, args.event, None)


def finish(args: argparse.Namespace) -> dict[str, Any]:
    """Emit run_finished and record the outcome.

    Only a run that finished blocked may finish again with another outcome.
    """
    args.phase = "complete"
    args.observation_id = "run"
    args.worker_id = None
    args.wait_kind = None
    run_path = data_dir() / "runs" / f"{args.run_id}.json"
    with exclusive_lock(run_path.with_suffix(".lock")):
        state = load_run(args.run_id)
        if state.get("status") == "finished" and state.get("outcome") not in (
            "blocked",
            args.outcome,
        ):
            msg = "run already finished with a different outcome"
            raise UsageError(msg)
        result = emit(state, args, "run_finished", args.outcome)
        state["status"] = "finished"
        state["outcome"] = args.outcome
        atomic_json(run_path, state)
    return result


def parse_timestamp(value: object) -> datetime:
    """Return the timezone-aware datetime of an event timestamp."""
    if not isinstance(value, str):
        msg = "telemetry event timestamp is invalid"
        raise UsageError(msg)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        msg = "telemetry event timestamp is invalid"
        raise UsageError(msg) from error
    if parsed.tzinfo is None:
        msg = "telemetry event timestamp must include a timezone"
        raise UsageError(msg)
    return parsed


def milliseconds(start: datetime, end: datetime) -> int:
    """Return the whole milliseconds from start to end, never negative."""
    return max(0, round((end - start).total_seconds() * 1000))


def merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Return the sorted union of intervals, joining overlapping ones."""
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def interval_total(intervals: list[tuple[datetime, datetime]]) -> int:
    """Return the milliseconds that the union of intervals covers."""
    return sum(milliseconds(start, end) for start, end in merge_intervals(intervals))


def overlap_total(
    left: list[tuple[datetime, datetime]],
    right: list[tuple[datetime, datetime]],
) -> int:
    """Return the milliseconds that both interval sets cover."""
    overlaps: list[tuple[datetime, datetime]] = []
    for left_start, left_end in merge_intervals(left):
        for right_start, right_end in merge_intervals(right):
            start, end = max(left_start, right_start), min(left_end, right_end)
            if start < end:
                overlaps.append((start, end))
    return interval_total(overlaps)


def _logged_events() -> Iterator[dict[str, Any]]:
    path = data_dir() / "events.ndjson"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    except (OSError, UnicodeDecodeError) as error:
        msg = "cannot read telemetry event log"
        raise UsageError(msg) from error
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            msg = "telemetry event log contains invalid JSON"
            raise UsageError(msg) from error
        if not isinstance(event, dict):
            msg = "telemetry event log contains a non-object"
            raise UsageError(msg)
        yield event


def _stored_events() -> Iterator[dict[str, Any]]:
    event_dir = data_dir() / "events"
    if event_dir.is_dir():
        for event_path in event_dir.glob("evt_*.json"):
            yield load_event(event_path)


def _run_event_id(event: dict[str, Any], run_id: str) -> str | None:
    event_id = event.get("event_id")
    if event.get("run_id") != run_id or not isinstance(event_id, str):
        return None
    version = event.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        msg = f"unsupported telemetry schema version: {version!r}"
        raise UsageError(msg)
    return event_id


def _event_order(event: dict[str, Any]) -> tuple[datetime, str]:
    return parse_timestamp(event.get("emitted_at")), event["event_id"]


def read_events(run_id: str) -> list[dict[str, Any]]:
    """Return the unique events of run_id, oldest first.

    The log is read before the per-event files, and the first copy of an event
    id wins.
    """
    events: dict[str, dict[str, Any]] = {}
    for event in itertools.chain(_logged_events(), _stored_events()):
        event_id = _run_event_id(event, run_id)
        if event_id is not None:
            events.setdefault(event_id, event)
    if not events:
        msg = f"no telemetry events found for run {run_id!r}"
        raise UsageError(msg)
    return sorted(events.values(), key=_event_order)


def latest_counter(events: list[dict[str, Any]], name: str) -> int | None:
    """Return the highest integer value of counter name across events, or None."""
    values = [
        metrics[name]
        for event in events
        if isinstance((metrics := event.get("metrics")), dict)
        and type(metrics.get(name)) is int
    ]
    return max(values) if values else None


def repeated_count(events: list[dict[str, Any]], counter: str) -> int | None:
    """Return how many runs of a gate came after the first, or None if unknown."""
    value = latest_counter(events, counter)
    return None if value is None else max(0, value - 1)


@dataclass
class _Timeline:
    """Pair the timed observations of one run, fed in timestamp order."""

    run_started: datetime | None = None
    run_finished: datetime | None = None
    interruptions: int = 0
    has_timing_observation: bool = False
    incomplete: int = 0
    starts: dict[tuple[str, str, str | None], dict[str, Any]] = field(
        default_factory=dict,
    )
    primary_by_phase: dict[str, list[tuple[datetime, datetime]]] = field(
        default_factory=lambda: {phase: [] for phase in PHASES},
    )
    worker_intervals: dict[str, list[tuple[datetime, datetime]]] = field(
        default_factory=dict,
    )
    waits: dict[str, list[tuple[datetime, datetime]]] = field(
        default_factory=lambda: {kind: [] for kind in WAIT_KINDS},
    )

    def add(self, event: dict[str, Any]) -> None:
        occurred = parse_timestamp(event.get("emitted_at"))
        event_name = event.get("event")
        if event_name == "run_started" and self.run_started is None:
            self.run_started = occurred
        elif event_name == "run_finished":
            self.run_finished = occurred
        elif event_name == "user_interruption":
            self.interruptions += 1
        observation_id = event.get("observation_id")
        if isinstance(observation_id, str):
            self._observe(event, observation_id, occurred)

    def _observe(
        self,
        event: dict[str, Any],
        observation_id: str,
        occurred: datetime,
    ) -> None:
        event_name = event.get("event")
        if event_name in ("phase_started", "wait_started"):
            self.has_timing_observation = True
            kind = "phase" if event_name == "phase_started" else "wait"
            key = (kind, observation_id, event.get("worker_id"))
            self.starts.setdefault(key, event)
        elif event_name in ("phase_completed", "wait_completed"):
            kind = "phase" if event_name == "phase_completed" else "wait"
            key = (kind, observation_id, event.get("worker_id"))
            started = self.starts.pop(key, None)
            if started is None or not self._complete(kind, started, event, occurred):
                self.incomplete += 1

    def _complete(
        self,
        kind: str,
        started: dict[str, Any],
        event: dict[str, Any],
        occurred: datetime,
    ) -> bool:
        start = parse_timestamp(started.get("emitted_at"))
        if occurred < start:
            return False
        if kind == "wait":
            return self._record_wait(started, event, (start, occurred))
        return self._record_phase(started, event, (start, occurred))

    def _record_wait(
        self,
        started: dict[str, Any],
        event: dict[str, Any],
        interval: tuple[datetime, datetime],
    ) -> bool:
        wait_kind = started.get("wait_kind")
        if wait_kind != event.get("wait_kind") or wait_kind not in self.waits:
            return False
        self.waits[wait_kind].append(interval)
        return True

    def _record_phase(
        self,
        started: dict[str, Any],
        event: dict[str, Any],
        interval: tuple[datetime, datetime],
    ) -> bool:
        phase = started.get("phase")
        if phase != event.get("phase") or phase not in self.primary_by_phase:
            return False
        worker_id = started.get("worker_id")
        if worker_id != event.get("worker_id"):
            return False
        if isinstance(worker_id, str):
            self.worker_intervals.setdefault(worker_id, []).append(interval)
        else:
            self.primary_by_phase[phase].append(interval)
        return True

    def delivery_elapsed_ms(self) -> int | None:
        if self.run_started is None or self.run_finished is None:
            return None
        return milliseconds(self.run_started, self.run_finished)

    def active_work_ms(self) -> int | None:
        primary = [
            interval
            for intervals in self.primary_by_phase.values()
            for interval in intervals
        ]
        if not primary:
            return None
        waits = [
            interval for intervals in self.waits.values() for interval in intervals
        ]
        return max(0, interval_total(primary) - overlap_total(primary, waits))


def _durations(
    intervals_by_name: dict[str, list[tuple[datetime, datetime]]],
) -> dict[str, int | None]:
    return {
        name: interval_total(intervals) if intervals else None
        for name, intervals in intervals_by_name.items()
    }


def _interruption_count(events: list[dict[str, Any]], observed: int) -> int | None:
    values = [observed] if observed else []
    metric = latest_counter(events, "user_interruptions")
    if metric is not None:
        values.append(metric)
    return max(values) if values else None


def build_report(run_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize time-ordered events of one run into a report.

    Primary phase time excludes observed waits; worker time is reported apart.
    A metric is None when no event observed it.
    """
    timeline = _Timeline()
    for event in events:
        timeline.add(event)
    incomplete = timeline.incomplete + len(timeline.starts)
    return {
        "run_id": run_id,
        "delivery_elapsed_ms": timeline.delivery_elapsed_ms(),
        "active_work_ms": timeline.active_work_ms(),
        "phase_durations_ms": _durations(timeline.primary_by_phase),
        "observed_wait_ms": _durations(timeline.waits),
        "worker_durations_ms": (
            {
                worker: interval_total(intervals)
                for worker, intervals in sorted(timeline.worker_intervals.items())
            }
            if timeline.worker_intervals
            else None
        ),
        "repeated_gate_counts": {
            "review": repeated_count(events, "review_cycles"),
            "test": repeated_count(events, "test_runs"),
            "quality": repeated_count(events, "full_quality_gate_runs"),
        },
        "user_interruptions": _interruption_count(events, timeline.interruptions),
        "observations_complete": timeline.has_timing_observation and incomplete == 0,
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
    """Return the report of the run selected by run id or task id."""
    if args.task_id is not None:
        task_id = validate_task_id(args.task_id)
        state = indexed_run(task_id) or discover_run(task_id)
        if state is None:
            msg = f"no run found for task id {task_id!r}"
            raise UsageError(msg)
        run_id = state["run_id"]
    else:
        run_id = args.run_id
        state = load_run(run_id)
    result = build_report(run_id, read_events(run_id))
    result["skill_version"] = state.get("skill_version")
    return result


def add_identity(parser: argparse.ArgumentParser, *, required: bool) -> None:
    """Add the harness, provider, model and role options to parser."""
    parser.add_argument("--harness", required=required)
    parser.add_argument("--provider", required=required)
    parser.add_argument("--model", required=required)
    parser.add_argument("--role", choices=ROLES, required=required)


def add_metrics(parser: argparse.ArgumentParser) -> None:
    """Add one optional integer option per counter to parser."""
    for name in COUNTERS:
        parser.add_argument(f"--{name.replace('_', '-')}", type=int)


def parser() -> argparse.ArgumentParser:
    """Return the command-line parser; each subcommand sets its handler."""
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    begin_parser = commands.add_parser("begin", help="start a run and emit run_started")
    begin_parser.add_argument("--task-id", required=True)
    add_identity(begin_parser, required=True)
    add_metrics(begin_parser)
    begin_parser.set_defaults(handler=begin)

    record_parser = commands.add_parser(
        "record",
        help="emit a completed phase snapshot",
    )
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
        "usage",
        help="record one non-overlapping host usage delta",
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
    """Run one subcommand and print its result; return 2 on rejected input."""
    try:
        args = parser().parse_args(argv)
        result = args.handler(args)
        if args.command == "report" and args.markdown:
            version = result["skill_version"] or "unknown"
            validate_opaque_identifier("plugin version", version)
            print(token_cost.markdown(result, version))
        else:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    except (UsageError, token_cost.UsageError) as error:
        print(f"telemetry: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"telemetry: cannot persist event: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
