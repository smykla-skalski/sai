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
        completed_retry = json.loads(run(
            root,
            "begin",
            "--task-id", "github-159",
            "--harness", "codex",
            "--provider", "openai",
            "--model", "gpt-5",
            "--role", "primary",
        ).stdout)
        assert completed_retry["run_id"] == run_id
        assert completed_retry["duplicate"] is True

        event_path = root / "sai" / "ship-it" / "telemetry" / "events.ndjson"
        events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        assert [event["event"] for event in events] == [
            "run_started", "phase_started", "wait_started", "wait_completed",
            "phase_completed", "run_finished",
        ]
        assert all(event["schema_version"] == 4 for event in events)
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


def test_blocked_run_resumes_the_same_history() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        started = json.loads(run(
            root,
            "begin",
            "--task-id", "github-224",
            "--harness", "codex",
            "--provider", "openai",
            "--model", "gpt",
            "--role", "primary",
        ).stdout)
        blocked = (
            "finish", "--run-id", started["run_id"], "--outcome", "blocked",
        )
        assert json.loads(run(root, *blocked).stdout)["duplicate"] is False
        assert json.loads(run(root, *blocked).stdout)["duplicate"] is True

        resumed = json.loads(run(
            root,
            "begin",
            "--task-id", "github-224",
            "--harness", "codex",
            "--provider", "openai",
            "--model", "gpt",
            "--role", "primary",
        ).stdout)
        assert resumed["run_id"] == started["run_id"]
        assert resumed["duplicate"] is True
        accepted = (
            "finish", "--run-id", resumed["run_id"], "--outcome", "accepted",
        )
        assert json.loads(run(root, *accepted).stdout)["duplicate"] is False
        assert json.loads(run(root, *accepted).stdout)["duplicate"] is True
        report = json.loads(run(root, "report", "--task-id", "github-224").stdout)
        assert report["run_id"] == started["run_id"]
        assert report["delivery_elapsed_ms"] is not None

        event_path = root / "sai" / "ship-it" / "telemetry" / "events.ndjson"
        events = [json.loads(line) for line in event_path.read_text().splitlines()]
        assert [event["outcome"] for event in events if event["event"] == "run_finished"] == [
            "blocked", "accepted",
        ]


def test_direct_blocked_completion_preserves_terminal_guards() -> None:
    for outcome in ("accepted", "rejected", "cancelled", "failed"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            started = json.loads(run(
                root, "begin", "--task-id", "direct-resume",
                "--harness", "codex", "--provider", "openai",
                "--model", "unknown", "--role", "primary",
            ).stdout)
            run_id = started["run_id"]
            run(root, "finish", "--run-id", run_id, "--outcome", "blocked")
            completion = ("finish", "--run-id", run_id, "--outcome", outcome)
            assert json.loads(run(root, *completion).stdout)["duplicate"] is False
            assert json.loads(run(root, *completion).stdout)["duplicate"] is True
            for conflicting in ("accepted", "rejected", "cancelled", "failed", "blocked"):
                if conflicting != outcome:
                    rejected = run(
                        root, "finish", "--run-id", run_id,
                        "--outcome", conflicting, success=False,
                    )
                    assert "already finished with a different outcome" in rejected.stderr
            state_path = root / "sai/ship-it/telemetry/runs" / f"{run_id}.json"
            assert json.loads(state_path.read_text())["outcome"] == outcome
            event_path = root / "sai/ship-it/telemetry/events.ndjson"
            events = [json.loads(line) for line in event_path.read_text().splitlines()]
            assert [event["outcome"] for event in events if event["event"] == "run_finished"] == [
                "blocked", outcome,
            ]
            assert sum(event["event"] == "run_started" for event in events) == 1


def test_worker_observation_ids_are_scoped_to_the_worker() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        started = json.loads(run(
            root,
            "begin",
            "--task-id", "github-224-workers",
            "--harness", "codex",
            "--provider", "openai",
            "--model", "gpt",
            "--role", "primary",
        ).stdout)
        run_id = started["run_id"]
        for worker in ("worker-a", "worker-b"):
            for event in ("phase_started", "phase_completed"):
                result = json.loads(run(
                    root,
                    "observe",
                    "--run-id", run_id,
                    "--event", event,
                    "--phase", "review",
                    "--observation-id", "review-1",
                    "--worker-id", worker,
                    "--role", "validator",
                ).stdout)
                assert result["duplicate"] is False
                assert result["event"]["worker_id"] == worker
        run(root, "finish", "--run-id", run_id, "--outcome", "accepted")
        report = json.loads(run(root, "report", "--run-id", run_id).stdout)
        assert set(report["worker_durations_ms"]) == {"worker-a", "worker-b"}
        assert report["observations_complete"] is True


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


def test_usage_cost_cli() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        run_id = json.loads(run(root, "begin", "--task-id", "cost-test", "--harness", "codex", "--provider", "openai", "--model", "unknown", "--role", "primary").stdout)["run_id"]
        command = ["usage", "--run-id", run_id, "--phase", "implement", "--observation-id", "request-1", "--input-tokens", "1000000", "--cache-write-tokens", "1000000", "--cache-read-tokens", "1000000", "--output-tokens", "1000000", "--input-price", "2", "--cache-write-price", "2.5", "--cache-read-price", "0.2", "--output-price", "8"]
        run(root, *command)
        assert json.loads(run(root, *command).stdout)["duplicate"] is True
        report = json.loads(run(root, "report", "--run-id", run_id).stdout)["token_cost"]
        assert report["total"]["estimated_usd"] == "12.7"
        assert report["by_phase"]["implement"] == report["by_role"]["primary"]
        run(root, "usage", "--run-id", run_id, "--phase", "review", "--observation-id", "unavailable", "--role", "validator", "--worker-id", "review-1")
        report = json.loads(run(root, "report", "--run-id", run_id).stdout)["token_cost"]
        assert report["total"]["estimated_usd"] is None
        assert report["total"]["known_estimated_usd"] == "12.7"
        assert report["by_role"]["validator"]["estimated_usd"] is None
        comment = run(root, "report", "--run-id", run_id, "--markdown").stdout
        assert "unknown" in comment and "12.7" in comment and run_id in comment
        assert str(root) not in comment and "openai" not in comment
        for option, value in [("--input-tokens", "-1"), ("--input-price", "NaN"), ("--output-price", "-2"), ("--output-price", "1e5")]:
            run(root, "usage", "--run-id", run_id, "--phase", "test", "--observation-id", "invalid", option, value, success=False)



def test_mixed_history_retains_unknown_cost() -> None:
    import token_cost

    old = {"schema_version": 3, "event": "phase_completed", "phase": "implement", "role": "primary"}
    new = {"schema_version": 4, "event": "usage_recorded", "phase": "review", "role": "validator", "worker_id": "reviewer", "usage": {"tokens": {"input": 1000000, "cache_write": 0, "cache_read": 0, "output": 0}, "prices_usd_per_million": {"input": "2", "cache_write": None, "cache_read": None, "output": None}}}
    result = token_cost.summarize([old, old, new])
    assert result["total"]["estimated_usd"] is None
    assert result["total"]["known_estimated_usd"] == "2"
    assert result["total"]["unknown_observations"] == 1
    assert result["by_phase"]["implement"]["estimated_usd"] is None
    assert result["by_role"]["primary"]["estimated_usd"] is None
    current_missing = {**old, "schema_version": 4}
    assert token_cost.summarize([current_missing, new])["total"]["estimated_usd"] is None

if __name__ == "__main__":
    test_mixed_history_retains_unknown_cost()
    print("ok test_mixed_history_retains_unknown_cost")
    test_usage_cost_cli()
    print("ok test_usage_cost_cli")
    test_lifecycle_resumes_and_deduplicates()
    print("ok test_lifecycle_resumes_and_deduplicates")
    test_direct_blocked_completion_preserves_terminal_guards()
    print("ok test_direct_blocked_completion_preserves_terminal_guards")
    test_blocked_run_resumes_the_same_history()
    print("ok test_blocked_run_resumes_the_same_history")
    test_worker_observation_ids_are_scoped_to_the_worker()
    print("ok test_worker_observation_ids_are_scoped_to_the_worker")
    test_unknown_values_and_validation()
    print("ok test_unknown_values_and_validation")
    test_report_separates_elapsed_work_waits_and_workers()
    print("ok test_report_separates_elapsed_work_waits_and_workers")
    test_short_append_completes_record()
    print("ok test_short_append_completes_record")
