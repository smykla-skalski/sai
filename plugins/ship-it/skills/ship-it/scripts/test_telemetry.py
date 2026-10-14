#!/usr/bin/env python3
"""Behavior tests for the ship-it telemetry recorder."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("telemetry.py")
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT.parent))
import telemetry


def run(data_home: Path, *arguments: str, success: bool = True) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "XDG_DATA_HOME": str(data_home)}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        env=environment,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is success, result.stderr
    return result


def test_lifecycle_resumes_and_deduplicates() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        started = json.loads(run(
            root,
            "begin",
            "--task-id", "github-159",
            "--harness", "codex",
            "--provider", "openai",
            "--model", "gpt-5",
            "--role", "primary",
            "--turns", "1",
        ).stdout)
        resumed = json.loads(run(
            root,
            "begin",
            "--task-id", "github-159",
            "--harness", "sail",
            "--provider", "other",
            "--model", "other",
            "--role", "primary",
        ).stdout)
        run_id = started["run_id"]
        assert resumed["run_id"] == run_id and resumed["duplicate"] is True
        phase_start = (
            "observe", "--run-id", run_id, "--event", "phase_started",
            "--phase", "implement", "--observation-id", "implement-1",
        )
        assert json.loads(run(root, *phase_start).stdout)["duplicate"] is False
        assert json.loads(run(root, *phase_start).stdout)["duplicate"] is True
        run(
            root,
            "observe", "--run-id", run_id, "--event", "wait_started",
            "--phase", "implement", "--observation-id", "approval-1",
            "--wait-kind", "approval",
        )
        run(
            root,
            "observe", "--run-id", run_id, "--event", "wait_completed",
            "--phase", "implement", "--observation-id", "approval-1",
            "--wait-kind", "approval",
        )
        run(
            root,
            "observe", "--run-id", run_id, "--event", "phase_completed",
            "--phase", "implement", "--observation-id", "implement-1",
            "--tool-calls", "4", "--review-cycles", "1",
        )
        finished = (
            "finish", "--run-id", run_id, "--outcome", "accepted",
            "--elapsed-ms", "93",
        )
        assert json.loads(run(root, *finished).stdout)["duplicate"] is False
        assert json.loads(run(root, *finished).stdout)["duplicate"] is True

        event_path = root / "sai" / "ship-it" / "telemetry" / "events.ndjson"
        events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        assert [event["event"] for event in events] == [
            "run_started", "phase_started", "wait_started", "wait_completed",
            "phase_completed", "run_finished",
        ]
        assert all(event["schema_version"] == 3 for event in events)
        assert events[0]["task_id"] == "github-159"
        assert events[1]["phase"] == "implement"
        assert events[4]["metrics"]["tool_calls"] == 4
        assert events[5]["outcome"] == "accepted" and events[5]["metrics"]["input_tokens"] is None
        assert set(events[0]["metrics"]) == {
            "turns", "tool_calls", "permission_decisions", "compactions",
            "input_tokens", "output_tokens", "elapsed_ms", "retries",
            "findings", "checks", "human_interventions", "failed_commands",
            "approval_wait_ms", "ci_failures", "ci_recurrences",
            "ci_resolutions", "review_cycles", "test_runs",
            "full_quality_gate_runs", "user_interruptions",
        }
        report = json.loads(run(root, "report", "--task-id", "github-159").stdout)
        assert report["event_count"] == 6
        assert report["observed_wait_ms"]["approval"] is not None
        assert report["observed_wait_ms"]["hosted_service"] is None
        assert event_path.stat().st_mode & 0o777 == 0o600
        assert event_path.parent.stat().st_mode & 0o777 == 0o700


def test_unknown_values_and_validation() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        started = json.loads(run(
            root,
            "begin",
            "--task-id", "eval-42",
            "--harness", "unknown",
            "--provider", "unknown",
            "--model", "unknown",
            "--role", "probe",
        ).stdout)
        event = started["event"]
        assert event["provider"] == "unknown" and all(value is None for value in event["metrics"].values())
        for arguments in (
            ("record", "--run-id", started["run_id"], "--phase", "invalid"),
            ("record", "--run-id", started["run_id"], "--phase", "test", "--turns", "-1"),
            ("begin", "--task-id", "prompt text is unsafe", "--harness", "codex", "--provider", "openai", "--model", "gpt", "--role", "primary"),
            ("begin", "--task-id", "https://private/repo", "--harness", "codex", "--provider", "openai", "--model", "gpt", "--role", "primary"),
            ("begin", "--task-id", "eval-43", "--harness", "codex", "--provider", "https://user:secret@private.example", "--model", "gpt", "--role", "primary"),
            ("record", "--run-id", started["run_id"], "--phase", "test", "--model", "https://user:secret@private.example/model"),
            ("observe", "--run-id", started["run_id"], "--event", "wait_started", "--phase", "test", "--observation-id", "wait-1"),
            ("observe", "--run-id", started["run_id"], "--event", "phase_started", "--phase", "test", "--observation-id", "phase-1", "--wait-kind", "approval"),
            ("observe", "--run-id", started["run_id"], "--event", "phase_started", "--phase", "test", "--observation-id", "unsafe value"),
            ("observe", "--run-id", started["run_id"], "--event", "phase_started", "--phase", "test", "--observation-id", "safe", "--worker-id", "https://private"),
            ("observe", "--run-id", started["run_id"], "--event", "phase_started", "--phase", "review", "--observation-id", "review-1", "--role", "validator"),
            ("finish", "--run-id", "missing", "--outcome", "accepted"),
            ("finish", "--run-id", "run_a/../../private", "--outcome", "accepted"),
        ):
            result = run(root, *arguments, success=False)
            assert result.returncode == 2

        state_path = root / "sai" / "ship-it" / "telemetry" / "runs" / f"{started['run_id']}.json"
        state_path.write_text("{}", encoding="utf-8")
        result = run(root, "record", "--run-id", started["run_id"], "--phase", "test", success=False)
        assert result.returncode == 2 and "invalid run state" in result.stderr

        state_path.write_bytes(b"\xff")
        result = run(root, "record", "--run-id", started["run_id"], "--phase", "test", success=False)
        assert result.returncode == 2 and "cannot read run state" in result.stderr


def sample_event(
    event_id: str,
    emitted_at: str,
    event: str,
    phase: str,
    observation_id: str | None = None,
    worker_id: str | None = None,
    wait_kind: str | None = None,
    metrics: dict[str, int | None] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 3,
        "event_id": event_id,
        "emitted_at": emitted_at,
        "run_id": "run_0123456789abcdef01234567",
        "task_id": "task-1",
        "event": event,
        "harness": "codex",
        "provider": "openai",
        "model": "gpt",
        "role": "subagent" if worker_id else "primary",
        "phase": phase,
        "observation_id": observation_id,
        "worker_id": worker_id,
        "wait_kind": wait_kind,
        "metrics": metrics or {},
        "outcome": "accepted" if event == "run_finished" else None,
    }


def test_report_separates_elapsed_work_waits_and_workers() -> None:
    run_id = "run_0123456789abcdef01234567"
    events = [
        sample_event("evt_000000000000000000000001", "2026-01-01T00:00:00Z", "run_started", "resolve", "run"),
        sample_event("evt_000000000000000000000002", "2026-01-01T00:00:00Z", "phase_started", "implement", "primary-1"),
        sample_event("evt_000000000000000000000003", "2026-01-01T00:00:10Z", "phase_started", "review", "worker-1", "reviewer-1"),
        sample_event("evt_000000000000000000000004", "2026-01-01T00:00:20Z", "phase_started", "test", "worker-2", "tester-1"),
        sample_event("evt_000000000000000000000005", "2026-01-01T00:00:30Z", "wait_started", "implement", "wait-1", wait_kind="approval"),
        sample_event("evt_000000000000000000000006", "2026-01-01T00:00:35Z", "user_interruption", "implement", "interrupt-1"),
        sample_event("evt_000000000000000000000007", "2026-01-01T00:00:40Z", "wait_completed", "implement", "wait-1", wait_kind="approval"),
        sample_event("evt_000000000000000000000008", "2026-01-01T00:00:50Z", "phase_completed", "review", "worker-1", "reviewer-1"),
        sample_event("evt_000000000000000000000009", "2026-01-01T00:01:00Z", "phase_completed", "test", "worker-2", "tester-1"),
        sample_event("evt_00000000000000000000000a", "2026-01-01T00:01:10Z", "phase_completed", "implement", "primary-1"),
        sample_event(
            "evt_00000000000000000000000b", "2026-01-01T00:01:30Z",
            "run_finished", "complete", "run",
            metrics={
                "review_cycles": 3,
                "test_runs": 2,
                "full_quality_gate_runs": 2,
                "user_interruptions": 1,
            },
        ),
    ]
    report = telemetry.build_report(run_id, events)
    assert report["delivery_elapsed_ms"] == 90_000
    assert report["phase_durations_ms"]["implement"] == 70_000
    assert report["observed_wait_ms"] == {
        "approval": 10_000,
        "hosted_service": None,
        "resource_queue": None,
    }
    assert report["active_work_ms"] == 60_000
    assert report["worker_durations_ms"] == {
        "reviewer-1": 40_000,
        "tester-1": 40_000,
    }
    assert report["repeated_gate_counts"] == {"review": 2, "test": 1, "quality": 1}
    assert report["user_interruptions"] == 1
    assert report["observations_complete"] is True

    incomplete = telemetry.build_report(
        run_id,
        [events[0], sample_event(
            "evt_00000000000000000000000c", "2026-01-01T00:00:05Z",
            "phase_started", "explore", "missing-completion",
        )],
    )
    assert incomplete["delivery_elapsed_ms"] is None
    assert incomplete["phase_durations_ms"]["explore"] is None
    assert incomplete["repeated_gate_counts"]["review"] is None
    assert incomplete["user_interruptions"] is None
    assert incomplete["observations_complete"] is False


def test_short_append_completes_record() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "events.ndjson"
        real_write = telemetry.os.write

        def short_write(descriptor: int, data: bytes | memoryview) -> int:
            size = max(1, len(data) // 2)
            return real_write(descriptor, data[:size])

        telemetry.os.write = short_write
        try:
            telemetry.append_event(path, b'{"event_id":"evt_one","event":"one"}\n')
            telemetry.append_event(path, b'{"event_id":"evt_two","event":"two"}\n')
        finally:
            telemetry.os.write = real_write
        assert [json.loads(line)["event"] for line in path.read_text().splitlines()] == ["one", "two"]


if __name__ == "__main__":
    test_lifecycle_resumes_and_deduplicates()
    print("ok test_lifecycle_resumes_and_deduplicates")
    test_unknown_values_and_validation()
    print("ok test_unknown_values_and_validation")
    test_report_separates_elapsed_work_waits_and_workers()
    print("ok test_report_separates_elapsed_work_waits_and_workers")
    test_short_append_completes_record()
    print("ok test_short_append_completes_record")
