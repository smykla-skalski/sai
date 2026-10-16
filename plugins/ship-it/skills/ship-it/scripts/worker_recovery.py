#!/usr/bin/env python3
"""Persist worker receipts and reconcile resume diagnostics under the checkpoint lock.

Called through bookkeeping.py record-worker-event / reconcile-workers.
Returns JSON fields; invalid state raises StateError (CLI exit 2).

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Final

from checkpoint_state import StateError, non_empty, require, utc_timestamp

MAX_RECORDS: Final[int] = 256


def timestamp(value: object, field: str) -> datetime:
    """Parse a strict UTC instant."""
    return datetime.fromisoformat(utc_timestamp(value, field).replace("Z", "+00:00"))


def held(checkpoint: dict[str, Any], dispatch_id: str) -> bool:
    """Retain ownership until an explicit host terminal observation."""
    return any(
        item["dispatchId"] == dispatch_id and item["ownerReleasedAt"] is None
        for item in checkpoint.get("workerRecovery", [])
    )


def validate(checkpoint: dict[str, Any]) -> None:
    """Validate bounded per-dispatch state without copying workflow results."""
    records = checkpoint.get("workerRecovery", [])
    require(
        isinstance(records, list) and len(records) <= MAX_RECORDS,
        "workerRecovery exceeds bounded receipt storage",
    )
    identities: set[str] = set()
    for item in records:
        require(
            isinstance(item, dict)
            and set(item)
            == {
                "dispatchId",
                "target",
                "owner",
                "registeredAt",
                "deadlineAt",
                "startedAt",
                "result",
                "acknowledgedAt",
                "ownerReleasedAt",
                "ownerObservation",
                "lastReconciledAt",
            },
            "invalid worker recovery fields",
        )
        identity = non_empty(item["dispatchId"], "dispatchId")
        require(identity not in identities, "duplicate worker recovery dispatchId")
        identities.add(identity)
        non_empty(item["owner"], "owner")
        require(
            isinstance(item["target"], dict)
            and set(item["target"]) in ({"issueUrl"}, {"reservationId"}),
            "worker target requires issueUrl or reservationId",
        )
        for value in item["target"].values():
            non_empty(value, "worker target")
        registered = timestamp(item["registeredAt"], "registeredAt")
        require(
            timestamp(item["deadlineAt"], "deadlineAt") > registered,
            "deadlineAt must follow registration",
        )
        for field in (
            "startedAt",
            "acknowledgedAt",
            "ownerReleasedAt",
            "lastReconciledAt",
        ):
            if item[field] is not None:
                require(
                    timestamp(item[field], field) >= registered,
                    f"{field} precedes registration",
                )
        result = item["result"]
        if result is not None:
            require(
                isinstance(result, dict)
                and set(result)
                == {
                    "eventId",
                    "status",
                    "checkpointPath",
                    "recordedAt",
                },
                "invalid worker result receipt",
            )
            for field in ("eventId", "checkpointPath"):
                non_empty(result[field], field)
            require(
                isinstance(result["status"], str)
                and result["status"] in {"completed", "failed", "blocked"},
                "invalid worker result status",
            )
            require(
                timestamp(result["recordedAt"], "recordedAt") >= registered,
                "result precedes registration",
            )
        require(
            item["acknowledgedAt"] is None or result is not None,
            "acknowledgement requires a result receipt",
        )
        require(
            (item["ownerReleasedAt"] is None) == (item["ownerObservation"] is None),
            "owner release requires host observation",
        )
        if item["ownerObservation"] is not None:
            non_empty(item["ownerObservation"], "ownerObservation")


def resolve_target(
    checkpoint: dict[str, Any], target: dict[str, Any], dispatch: str,
) -> str | None:
    """Bind recovery to an existing child dispatch or gate reservation."""
    if set(target) == {"issueUrl"}:
        graph = checkpoint.get("orchestration") or {"children": []}
        child = next(
            (
                item
                for item in graph["children"]
                if item["issueUrl"] == target["issueUrl"]
            ),
            None,
        )
        require(
            child is not None
            and child["dispatchId"] == dispatch
            and child["status"] == "running",
            "worker requires active child dispatch",
        )
        return child["worker"]
    require(set(target) == {"reservationId"}, "invalid worker target")
    receipt = next(
        (
            item
            for item in checkpoint["convergence"]["reservations"]
            if item["id"] == target["reservationId"]
        ),
        None,
    )
    require(
        receipt is not None and receipt["status"] == "reserved",
        "worker requires pending gate reservation",
    )
    return None


def record_event(checkpoint: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Record one worker transition; results never attest a passing workflow gate."""
    require(
        set(event) == {"dispatchId", "kind", "at", "data"},
        "worker event requires dispatchId, kind, at and data",
    )
    dispatch = non_empty(event["dispatchId"], "dispatchId")
    at = timestamp(event["at"], "at")
    data = event["data"]
    require(isinstance(data, dict), "worker event data must be an object")
    records = checkpoint.setdefault("workerRecovery", [])
    record = next((item for item in records if item["dispatchId"] == dispatch), None)
    kind = event["kind"]
    if kind == "register":
        require(
            set(data) == {"target", "owner", "deadlineAt"},
            "register requires target, owner and deadlineAt",
        )
        if record is not None:
            require(
                all(record[key] == value for key, value in data.items())
                and record["registeredAt"] == event["at"],
                "dispatch already registered with different content",
            )
            return {"dispatchId": dispatch, "applied": False}
        require(
            len(records) < MAX_RECORDS,
            "worker receipt storage full; archive the completed run before dispatch",
        )
        owner = non_empty(data["owner"], "owner")
        require(isinstance(data["target"], dict), "target must be an object")
        existing_owner = resolve_target(checkpoint, data["target"], dispatch)
        require(
            existing_owner is None or existing_owner == owner,
            "owner does not match child dispatch",
        )
        require(
            not any(
                item["target"] == data["target"] and item["ownerReleasedAt"] is None
                for item in records
            ),
            "target still has an active or unknown owner",
        )
        require(
            timestamp(data["deadlineAt"], "deadlineAt") > at,
            "deadlineAt must follow registration",
        )
        records.append(
            {
                "dispatchId": dispatch,
                **copy.deepcopy(data),
                "registeredAt": event["at"],
                "startedAt": None,
                "result": None,
                "acknowledgedAt": None,
                "ownerReleasedAt": None,
                "ownerObservation": None,
                "lastReconciledAt": None,
            },
        )
        return {"dispatchId": dispatch, "applied": True}
    require(record is not None, "unknown worker dispatch")
    require(
        at >= timestamp(record["registeredAt"], "registeredAt"),
        "worker event precedes registration",
    )
    if kind == "started":
        require(not data, "started data must be empty")
        if record["startedAt"] == event["at"]:
            return {"dispatchId": dispatch, "applied": False}
        require(
            record["result"] is None and record["ownerReleasedAt"] is None,
            "worker already terminal",
        )
        field, value = "startedAt", event["at"]
    elif kind == "result":
        require(
            set(data) == {"eventId", "status", "checkpointPath"},
            "result requires eventId, status and checkpointPath",
        )
        field, value = "result", {**copy.deepcopy(data), "recordedAt": event["at"]}
        if record["result"] == value:
            return {"dispatchId": dispatch, "applied": False}
        require(record["ownerReleasedAt"] is None, "worker owner already released")
    elif kind == "acknowledge":
        require(
            set(data) == {"eventId"}
            and record["result"] is not None
            and data["eventId"] == record["result"]["eventId"],
            "acknowledgement requires matching result eventId",
        )
        require(
            at >= timestamp(record["result"]["recordedAt"], "recordedAt"),
            "acknowledgement precedes result",
        )
        field, value = "acknowledgedAt", event["at"]
    elif kind == "release-owner":
        require(
            set(data) == {"hostStatus", "observation"}
            and isinstance(data["hostStatus"], str)
            and data["hostStatus"] in {"closed", "exited"},
            "owner release requires closed or exited host status",
        )
        observation = non_empty(data["observation"], "host observation")
        require(
            record["ownerObservation"] in {None, observation},
            "owner observation already recorded",
        )
        record["ownerObservation"] = observation
        field, value = "ownerReleasedAt", event["at"]
    else:
        message = "invalid worker event kind"
        raise StateError(message)
    previous = record[field]
    require(previous is None or previous == value, "worker transition already recorded")
    record[field] = value
    return {"dispatchId": dispatch, "applied": previous is None}


def reconcile(
    checkpoint: dict[str, Any], observation: dict[str, Any],
) -> dict[str, Any]:
    """Classify durable facts at a caller-observed UTC resume instant."""
    require(set(observation) == {"at"}, "reconcile-workers requires at")
    at = timestamp(observation["at"], "at")
    diagnostics = []
    for record in checkpoint.get("workerRecovery", []):
        require(
            at >= timestamp(record["registeredAt"], "registeredAt"),
            "reconciliation precedes registration",
        )
        if record["lastReconciledAt"] is not None:
            require(
                at >= timestamp(record["lastReconciledAt"], "lastReconciledAt"),
                "reconciliation moves backwards",
            )
        result = record["result"]
        state = (
            (
                "completed-but-undelivered"
                if record["acknowledgedAt"] is None
                else "acknowledged"
            )
            if result
            else ("executing-observed" if record["startedAt"] else "queued-unobserved")
        )
        diagnostics.append(
            {
                "dispatchId": record["dispatchId"],
                "state": state,
                "deadlineExceeded": at >= timestamp(record["deadlineAt"], "deadlineAt"),
                "ownerHeld": record["ownerReleasedAt"] is None,
                "result": copy.deepcopy(result),
            },
        )
        record["lastReconciledAt"] = observation["at"]
    return {"workers": diagnostics}
