#!/usr/bin/env python3
# Copyright 2026 Marcin Skalski
"""Remember user-wide Copilot quota refusals without repository content.

Usage: copilot_quota.py status|clear
       copilot_quota.py classify REVIEWS.json [--previous STATE.json]
           [--max-age SECONDS]
Output: one JSON record. Exit codes: 0 success; 2 invalid input/state.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from copilot_review import classify_reviews

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_MAX_AGE: Final = 86400
REASON: Final = "copilot-quota-refusal"
REVIEWER: Final = "copilot"
CLEARED: Final = "cleared"


def quota_directory() -> Path:
    """Return the current OS user shared XDG serviceability directory."""
    return (
        Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        / "sai/ship-it/serviceability"
    )


@contextmanager
def _locked(directory: Path) -> Iterator[None]:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "copilot-quota.lock").open("a", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if (
        not isinstance(state, dict)
        or set(state) != {"reviewer", "reason", "expiresAt"}
        or state["reviewer"] != REVIEWER
        or state["reason"] not in {REASON, CLEARED}
        or type(state["expiresAt"]) not in {int, float}
        or not math.isfinite(state["expiresAt"])
    ):
        message = "invalid Copilot quota memory; inspect or clear it"
        raise ValueError(message)
    return state


def quota_status(*, directory: Path | None = None) -> dict[str, Any]:
    """Inspect memory without requesting or waiting for a review."""
    directory = directory or quota_directory()
    with _locked(directory):
        state = _read_state(directory / "copilot-quota.json")
        if state and (state["reason"] == CLEARED or state["expiresAt"] <= time.time()):
            state = None
    return {"requestAllowed": state is None, "quotaMemory": state}


def clear_quota(*, directory: Path | None = None) -> dict[str, Any]:
    """Clear the refusal under the same lock used by writers."""
    directory = directory or quota_directory()
    with _locked(directory):
        _write_state(
            directory / "copilot-quota.json",
            {"reviewer": REVIEWER, "reason": CLEARED, "expiresAt": time.time()},
        )
    return {"requestAllowed": True, "quotaMemory": None}


def remember_quota(
    *,
    max_age: int = DEFAULT_MAX_AGE,
    directory: Path | None = None,
    submitted_at: float | None = None,
) -> dict[str, Any] | None:
    """Store a refusal atomically without extending an active expiry."""
    if type(max_age) is not int or max_age <= 0:
        message = "max-age must be a positive integer number of seconds"
        raise ValueError(message)
    directory = directory or quota_directory()
    with _locked(directory):
        path = directory / "copilot-quota.json"
        now = time.time()
        state = _read_state(path)
        if state is not None:
            if state["expiresAt"] > now:
                return state
            if submitted_at is None or submitted_at <= state["expiresAt"]:
                return None
        observed = now if submitted_at is None else min(submitted_at, now)
        if observed + max_age > now:
            state = {
                "reviewer": REVIEWER,
                "reason": REASON,
                "expiresAt": observed + max_age,
            }
            _write_state(path, state)
    return state


def _write_state(path: Path, state: dict[str, Any]) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def classify_and_remember(
    reviews: list[dict[str, Any]],
    previous: dict[str, Any] | None = None,
    *,
    max_age: int = DEFAULT_MAX_AGE,
    directory: Path | None = None,
) -> dict[str, Any]:
    """Classify PR reviews and remember only newly observed refusal evidence.

    Preserve the returned PR state across snapshots so an old refusal never
    renews the shared expiry. Global memory never removes genuine reviews.
    """
    result = classify_reviews(reviews, previous)
    prior = (previous or {}).get("refusalEvidence", [])
    for item in result["refusalEvidence"]:
        if item in prior:
            continue
        raw = next((review for review in reviews if review.get("id") == item["id"]), {})
        timestamp = raw.get("submitted_at") or raw.get("submittedAt")
        submitted_at = None
        if timestamp:
            if not isinstance(timestamp, str):
                message = "review submitted timestamp must be an ISO datetime"
                raise ValueError(message)
            submitted = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if submitted.tzinfo is None:
                message = "review submitted timestamp requires a timezone"
                raise ValueError(message)
            submitted_at = submitted.timestamp()
        remember_quota(max_age=max_age, directory=directory, submitted_at=submitted_at)
    result["quotaMemory"] = quota_status(directory=directory)["quotaMemory"]
    result["requestAllowed"] = (
        result["requestAllowed"] and result["quotaMemory"] is None
    )
    return result


def main(argv: list[str] | None = None) -> int:
    """Inspect, clear, or update user-wide refusal memory."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("clear")
    classify = commands.add_parser("classify")
    classify.add_argument("reviews", type=Path)
    classify.add_argument("--previous", type=Path)
    classify.add_argument("--max-age", type=int, default=DEFAULT_MAX_AGE)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = quota_status()
        elif args.command == "clear":
            result = clear_quota()
        else:
            reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
            previous = (
                json.loads(args.previous.read_text(encoding="utf-8"))
                if args.previous
                else None
            )
            result = classify_and_remember(reviews, previous, max_age=args.max_age)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
