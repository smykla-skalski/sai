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


def test_lifecycle() -> None:
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
        run_id = started["run_id"]
        run(
            root,
            "record",
            "--run-id", run_id,
            "--phase", "publish",
            "--role", "validator",
            "--tool-calls", "4",
        )
        run(root, "finish", "--run-id", run_id, "--outcome", "accepted", "--elapsed-ms", "93")

        event_path = root / "sai" / "ship-it" / "telemetry" / "events.ndjson"
        events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        assert [event["event"] for event in events] == ["run_started", "phase_completed", "run_finished"]
        assert all(event["schema_version"] == 2 for event in events)
        assert events[0]["task_id"] == "github-159"
        assert events[1]["phase"] == "publish"
        assert events[1]["role"] == "validator" and events[1]["metrics"]["tool_calls"] == 4
        assert events[2]["outcome"] == "accepted" and events[2]["metrics"]["input_tokens"] is None
        assert set(events[0]["metrics"]) == {
            "turns", "tool_calls", "permission_decisions", "compactions",
            "input_tokens", "output_tokens", "elapsed_ms", "retries",
            "findings", "checks", "human_interventions", "failed_commands",
            "approval_wait_ms", "ci_failures", "ci_recurrences",
            "ci_resolutions",
        }
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


def test_short_append_completes_record() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "events.ndjson"
        real_write = telemetry.os.write

        def short_write(descriptor: int, data: bytes | memoryview) -> int:
            size = max(1, len(data) // 2)
            return real_write(descriptor, data[:size])

        telemetry.os.write = short_write
        try:
            telemetry.append_event(path, b'{"event":"one"}\n')
            telemetry.append_event(path, b'{"event":"two"}\n')
        finally:
            telemetry.os.write = real_write
        assert [json.loads(line)["event"] for line in path.read_text().splitlines()] == ["one", "two"]


if __name__ == "__main__":
    test_lifecycle()
    print("ok test_lifecycle")
    test_unknown_values_and_validation()
    print("ok test_unknown_values_and_validation")
    test_short_append_completes_record()
    print("ok test_short_append_completes_record")
