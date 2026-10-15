#!/usr/bin/env python3
"""Validate phase handoff receipts for bookkeeping.py's locked transaction.

Usage: bookkeeping.py handoff --checkpoint FILE --handoff-json OBJECT
Output: checkpoint mutation result; invalid requests exit 2 without changing state.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

from typing import Any, Final

from checkpoint_state import StateError, non_empty

BOUNDARIES: Final[dict[str, str]] = {
    "draft-published": "review",
    "before-pr-loop": "pr",
}
MAX_BRIEF_BYTES: Final[int] = 1999
MAX_INPUT_TOKENS: Final[int] = 25000


def validate_update(update: dict[str, Any]) -> None:
    """Reject malformed receipts and enforce the startup context bounds."""
    status = non_empty(update.get("status"), "handoff.status")
    allowed = {"id", "boundary", "status", "brief"}
    if status == "accepted":
        allowed.update({"worker", "inputTokens"})
        non_empty(update.get("worker"), "handoff.worker")
        tokens = update.get("inputTokens")
        if type(tokens) is not int or not 0 < tokens < MAX_INPUT_TOKENS:
            message = "fresh worker inputTokens must be between 1 and 24999"
            raise StateError(message)
    elif status == "fallback":
        allowed.add("reason")
        non_empty(update.get("reason"), "handoff.reason")
    elif status != "pending":
        message = "handoff status must be pending|accepted|fallback"
        raise StateError(message)
    if set(update) - allowed:
        message = "handoff contains unknown or status-inappropriate fields"
        raise StateError(message)
    if non_empty(update.get("boundary"), "handoff.boundary") not in BOUNDARIES:
        message = "handoff boundary must be draft-published|before-pr-loop"
        raise StateError(message)
    non_empty(update.get("id"), "handoff.id")


def validate_destination(
    checkpoint: dict[str, Any],
    boundary: str,
    existing: dict[str, Any] | None,
) -> None:
    """Require a published revision at the boundary's continuation phase."""
    workflow = checkpoint["workflow"]
    if workflow["status"] != "active" or workflow["phase"] != BOUNDARIES[boundary]:
        message = "handoff requires its active destination phase"
        raise StateError(message)
    if not checkpoint["delivery"].get("pullRequestUrl"):
        message = "handoff requires a recorded draft PR"
        raise StateError(message)
    if existing is not None and existing["revision"] != workflow["revision"]:
        message = "pending handoff revision changed; reconcile before continuation"
        raise StateError(message)


def find_receipt(
    receipts: list[dict[str, Any]],
    update: dict[str, Any],
) -> dict[str, Any] | None:
    """Reject duplicate boundaries and mismatched acknowledgment identities."""
    existing = next((item for item in receipts if item["id"] == update["id"]), None)
    if existing is not None:
        if existing["boundary"] != update["boundary"]:
            message = "handoff ID belongs to another boundary"
            raise StateError(message)
        return existing
    if update["status"] != "pending":
        message = "prepare a pending handoff before acknowledging it"
        raise StateError(message)
    if any(item["boundary"] == update["boundary"] for item in receipts):
        message = "boundary already has a handoff receipt; resume it"
        raise StateError(message)
    return None


def record_handoff(
    checkpoint: dict[str, Any],
    update: dict[str, Any],
) -> dict[str, Any]:
    """Record an idempotent handoff without replacing workflow or gate state."""
    validate_update(update)
    receipts = checkpoint.setdefault("handoffs", [])
    if not isinstance(receipts, list):
        message = "checkpoint.handoffs must be an array"
        raise StateError(message)
    existing = find_receipt(receipts, update)
    if existing is not None and existing["status"] != "pending":
        if all(existing.get(key) == value for key, value in update.items()):
            return {"handoff": existing}
        message = "completed handoff receipt is immutable"
        raise StateError(message)
    validate_destination(checkpoint, update["boundary"], existing)
    brief = non_empty(
        update.get("brief", existing["brief"] if existing else None), "handoff.brief",
    )
    if len(brief.encode("utf-8")) > MAX_BRIEF_BYTES:
        message = "handoff brief must be at most 1999 UTF-8 bytes"
        raise StateError(message)
    receipt = dict(existing or {})
    receipt.update(update)
    receipt.update({"brief": brief, "revision": checkpoint["workflow"]["revision"]})
    if existing is None:
        receipts.append(receipt)
    else:
        existing.update(receipt)
    return {"handoff": receipt}
