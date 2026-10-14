#!/usr/bin/env python3
"""Reserve bounded validation work and retain crash-safe convergence decisions.

Used by bookkeeping.py under its checkpoint lock. Reservations consume allowances
before work starts; completing or retrying a reservation never consumes again.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Final

COUNTERS: Final[dict[str, str]] = {
    "review": "reviewCycles",
    "fix": "fixPasses",
    "quality": "fullQualityGateRuns",
    "test": "broadTestRuns",
}
POLICY: Final[dict[str, Any]] = json.loads(
    (
        Path(__file__).resolve().parent.parent
        / "references"
        / "convergence-policy.json"
    ).read_text(encoding="utf-8"),
)["modes"]["bounded"]
LIMITS: Final[dict[str, int]] = {
    "review": POLICY["review"]["max_cycles"],
    "fix": POLICY["fixes"]["max_passes"],
    "quality": POLICY["full_quality_gate_runs"],
    "test": 1,
}
TRIGGERS: Final[frozenset[str]] = frozenset(
    {"security", "data-loss", "destructive-concurrency"},
)
DEFAULTS: Final[dict[str, Any]] = {
    "mode": "bounded",
    "authorizedBy": None,
    "startedAt": None,
    "reviewCycles": 0,
    "fixPasses": 0,
    "fullQualityGateRuns": 0,
    "broadTestRuns": 0,
    "reviewedRevision": None,
    "findings": [],
    "followUpIssues": [],
    "reservations": [],
    "reassessment": None,
}


class ConvergenceError(ValueError):
    """Invalid or unauthorized validation work."""


def initialize(checkpoint: dict[str, Any]) -> None:
    """Add zero-activity defaults without inventing completed review evidence."""
    state = checkpoint.get("convergence")
    if not isinstance(state, dict):
        msg = "convergence must be an object"
        raise ConvergenceError(msg)
    if state.get("reviewCycles", 0) and (
        "reviewedRevision" not in state or "findings" not in state
    ):
        msg = "recover revision-bound review evidence before resume"
        raise ConvergenceError(msg)
    for key, value in DEFAULTS.items():
        if key not in state:
            state[key] = value.copy() if isinstance(value, list) else value


def timestamp(value: object) -> datetime:
    """Parse a timezone-aware checkpoint timestamp."""
    if not isinstance(value, str):
        msg = "convergence timestamp must be a string"
        raise ConvergenceError(msg)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        msg = "invalid convergence timestamp"
        raise ConvergenceError(msg) from error
    if result.utcoffset() is None:
        msg = "convergence timestamp requires timezone"
        raise ConvergenceError(msg)
    return result


def require(condition: object, message: str) -> None:
    """Fail without mutating durable state when an invariant is unsatisfied."""
    if not condition:
        raise ConvergenceError(message)


def validate_operation(operation: object, identities: set[str]) -> str:
    """Validate one persisted reservation and return its resource kind."""
    require(isinstance(operation, dict), "reservation must be an object")
    identity = operation.get("id")
    require(
        isinstance(identity, str)
        and bool(identity.strip())
        and identity not in identities,
        "reservation IDs must be non-empty and unique",
    )
    identities.add(identity)
    kind = operation.get("kind")
    require(isinstance(kind, str) and kind in COUNTERS, "invalid reservation kind")
    for field in ("revision", "inputs", "reservedAt"):
        require(
            isinstance(operation.get(field), str) and bool(operation[field].strip()),
            f"reservation requires {field}",
        )
    require(
        type(operation.get("ordinal")) is int and operation["ordinal"] > 0,
        "reservation requires positive ordinal",
    )
    require(
        operation.get("status") in ("reserved", "completed"),
        "invalid reservation status",
    )
    require("result" in operation, "reservation requires result")
    result = operation["result"]
    require(
        (operation["status"] == "reserved" and result is None)
        or (
            operation["status"] == "completed"
            and isinstance(result, dict)
            and result.get("verdict") in ("passed", "failed", "blocked")
        ),
        "reservation result must match its status",
    )
    return kind


def validate(checkpoint: dict[str, Any]) -> None:
    """Reject malformed persisted counters and operation identities."""
    initialize(checkpoint)
    state = checkpoint["convergence"]
    require(state["mode"] in ("bounded", "exhaustive"), "invalid convergence mode")
    for field in COUNTERS.values():
        require(
            type(state[field]) is int and state[field] >= 0,
            f"convergence.{field} must be a non-negative integer",
        )
    if state["mode"] == "bounded":
        for kind, maximum in LIMITS.items():
            require(
                state[COUNTERS[kind]] <= maximum,
                "bounded counter exceeds policy allowance",
            )
    if state["startedAt"] is not None:
        timestamp(state["startedAt"])
    require(
        not state["reviewCycles"] or state["startedAt"] is not None,
        "spent review cycle requires startedAt",
    )
    require(
        state["reviewedRevision"] is None or bool(state["reviewCycles"]),
        "reviewedRevision requires a spent review cycle",
    )
    for field in ("reservations", "findings", "followUpIssues"):
        require(isinstance(state[field], list), f"convergence.{field} must be an array")
    require(
        not state["reviewCycles"]
        or state["reviewedRevision"] is not None
        or any(
            isinstance(operation, dict)
            and operation.get("kind") == "review"
            and operation.get("status") == "reserved"
            for operation in state["reservations"]
        ),
        "recover revision-bound review evidence or reconcile a pending review receipt",
    )
    identities: set[str] = set()
    counts = dict.fromkeys(COUNTERS, 0)
    for operation in state["reservations"]:
        counts[validate_operation(operation, identities)] += 1
    for kind, count in counts.items():
        require(count <= state[COUNTERS[kind]], "reservations exceed consumed counter")
    require(
        state["mode"] != "exhaustive"
        or any(
            grant["id"] == state["authorizedBy"]
            for grant in checkpoint["authorization"]["grants"]
        ),
        "exhaustive state requires retained original-user authority",
    )


def active_grant(checkpoint: dict[str, Any], identity: object) -> dict[str, Any]:
    """Resolve only retained active original-user authority."""
    for grant in checkpoint["authorization"]["grants"]:
        if grant["id"] == identity and grant["status"] == "active":
            return grant
    msg = "validation extension requires an active original-user grant"
    raise ConvergenceError(
        msg,
    )


def consume_grant(checkpoint: dict[str, Any], identity: str, resource: str) -> None:
    """Spend one explicit scoped allowance without changing its maximum."""
    grant = active_grant(checkpoint, identity)
    if resource not in grant["scope"]:
        msg = f"grant scope must explicitly include {resource}"
        raise ConvergenceError(msg)
    limits = [limit for limit in grant["limits"] if limit["resource"] == resource]
    if len(limits) != 1 or limits[0]["used"] >= limits[0]["maximum"]:
        msg = f"grant has no remaining bounded {resource} allowance"
        raise ConvergenceError(msg)
    limits[0]["used"] += 1


def check_rerun(state: dict[str, Any], request: dict[str, Any]) -> None:
    """Require relevant changed inputs for the final severity-triggered review."""
    kind = request["kind"]
    used = state[COUNTERS[kind]]
    previous = [op for op in state["reservations"] if op["kind"] == kind]
    if kind in ("review", "test", "quality") and used:
        require(
            not previous or previous[-1]["status"] == "completed",
            "reconcile the pending broad operation before another dispatch",
        )
        changed = bool(previous) and previous[-1]["inputs"] != request["inputs"]
        require(
            bool(request.get("grant")) or (changed and bool(request.get("reason"))),
            "broad rerun requires changed relevant inputs and reason or scoped grant",
        )
    require(
        kind != "review"
        or not used
        or bool(request.get("grant"))
        or request.get("trigger") in TRIGGERS,
        "second review requires a security, data-loss "
        "or destructive-concurrency trigger",
    )


def spend_allowance(
    checkpoint: dict[str, Any],
    request: dict[str, Any],
    now: datetime,
) -> None:
    """Apply internal and explicit user limits in the same transaction."""
    state = checkpoint["convergence"]
    kind = request["kind"]
    counter = COUNTERS[kind]
    grant_id = request.get("grant")
    elapsed = (
        state["startedAt"] is not None
        and (now - timestamp(state["startedAt"])).total_seconds()
        >= POLICY["max_elapsed_minutes"] * 60
    )
    if state[counter] >= LIMITS[kind] or (kind == "review" and elapsed) or grant_id:
        require(
            bool(grant_id),
            f"{counter} allowance exhausted; defer optional work "
            "or recover a named acceptance failure",
        )
        consume_grant(checkpoint, grant_id, counter)
        state["mode"] = "exhaustive"
        state["authorizedBy"] = grant_id
    for grant in checkpoint["authorization"]["grants"]:
        if grant["id"] == grant_id:
            continue
        for limit in grant["limits"]:
            if limit["resource"] == counter:
                require(
                    grant["status"] == "active" and limit["used"] < limit["maximum"],
                    f"explicit user {counter} limit prevents this action",
                )
                limit["used"] += 1


def check_dispatch(checkpoint: dict[str, Any], request: dict[str, Any]) -> None:
    """Check current scope, revision and review prerequisites."""
    require(
        checkpoint["workflow"]["status"] == "active",
        "validation requires an active workflow",
    )
    require(
        checkpoint["convergence"]["reassessment"] is None,
        "scope or design reassessment required before further broad work",
    )
    require(request["kind"] in COUNTERS, "invalid reservation kind")
    require(
        request["revision"] == checkpoint["workflow"]["revision"],
        "reservation must target the current workflow revision",
    )
    require(
        any(
            grant["status"] == "active"
            for grant in checkpoint["authorization"]["grants"]
        ),
        "recover an active original-user task grant before validation",
    )
    if request["kind"] == "test":
        require(
            review_clean(checkpoint, request["revision"]),
            "broad test requires review-clean current revision",
        )


def review_clean(checkpoint: dict[str, Any], revision: str) -> bool:
    """Accept only current-revision review attestations in the selected storage."""
    verdicts = checkpoint["gateVerdicts"]
    if checkpoint["bookkeeping"]["evidence"]:
        pointer = checkpoint["evidence"]
        if pointer.get("revision") != revision or not isinstance(
            pointer.get("recordPath"),
            str,
        ):
            return False
        try:
            record = json.loads(Path(pointer["recordPath"]).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if (
            not isinstance(record, dict)
            or record.get("revision") != revision
            or record.get("checkpointId") != checkpoint["checkpointId"]
            or record.get("invalidatedAt") is not None
        ):
            return False
        verdicts = record.get("results")
    if not isinstance(verdicts, list):
        return False
    return any(
        isinstance(verdict, dict)
        and verdict.get("sourceRevision", verdict.get("revision")) == revision
        and verdict.get("gate", verdict.get("id"))
        in (
            "adversarial-review",
            "inline-review",
            "gate-adversarial-review",
            "gate-inline-review",
        )
        and verdict.get("status") == "passed"
        for verdict in verdicts
    )


def reserve(
    checkpoint: dict[str, Any],
    request: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Reserve exactly one operation; a retry returns its existing receipt."""
    validate(checkpoint)
    state = checkpoint["convergence"]
    for operation in state["reservations"]:
        if operation["id"] == request["id"]:
            require(
                all(operation.get(key) == value for key, value in request.items()),
                "reservation retry changed its request",
            )
            return {"dispatch": False, "reservation": operation}
    check_dispatch(checkpoint, request)
    check_rerun(state, request)
    spend_allowance(checkpoint, request, now)
    kind = request["kind"]
    if kind == "review" and state["startedAt"] is None:
        state["startedAt"] = now.isoformat().replace("+00:00", "Z")
    state[COUNTERS[kind]] += 1
    operation = {
        **request,
        "status": "reserved",
        "reservedAt": now.isoformat().replace("+00:00", "Z"),
        "result": None,
        "ordinal": state[COUNTERS[kind]],
    }
    state["reservations"].append(operation)
    return {"dispatch": True, "reservation": operation}


def record_review(
    checkpoint: dict[str, Any],
    operation: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Store findings and require reassessment after a second severe review."""
    state = checkpoint["convergence"]
    findings = result.get("findings")
    require(
        isinstance(findings, list)
        and all(
            isinstance(finding, dict)
            and finding.get("category") in (*TRIGGERS, "acceptance", "optional")
            and finding.get("label") in ("blocking", "issue", "question")
            and finding.get("disposition") == "open"
            and all(
                isinstance(finding.get(key), str) and bool(finding[key].strip())
                for key in ("id", "label", "location", "summary")
            )
            for finding in findings
        ),
        "review result requires structured surviving findings",
    )
    require(
        len({finding["id"] for finding in findings}) == len(findings),
        "finding IDs must be unique",
    )
    require(
        result["verdict"] != "passed" or not findings,
        "passing review cannot contain open findings",
    )
    state["reviewedRevision"] = operation["revision"]
    state["findings"] = findings
    if operation["ordinal"] > 1 and any(f["category"] in TRIGGERS for f in findings):
        state["reassessment"] = {
            "reservation": operation["id"],
            "revision": operation["revision"],
            "findings": [f["id"] for f in findings if f["category"] in TRIGGERS],
        }
        checkpoint["workflow"].update(
            status="blocked",
            blocker="second review found security, "
            "data-loss or destructive-concurrency defects",
            nextAction="Reassess scope or design for the recorded severe "
            "findings before any further broad validation",
        )


def finish(
    checkpoint: dict[str, Any],
    identity: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Persist an attested result without refunding or spending an allowance."""
    validate(checkpoint)
    state = checkpoint["convergence"]
    for operation in state["reservations"]:
        if operation["id"] != identity:
            continue
        if operation["status"] == "completed":
            if operation["result"] != result:
                msg = "completed reservation result is immutable"
                raise ConvergenceError(msg)
            return {"completion": "already-recorded", "reservation": operation}
        if result.get("verdict") not in ("passed", "failed", "blocked"):
            msg = "result requires passed, failed or blocked verdict"
            raise ConvergenceError(msg)
        if operation["kind"] == "review":
            record_review(checkpoint, operation, result)
        operation["status"] = "completed"
        operation["result"] = result
        return {"completion": "recorded", "reservation": operation}
    msg = "unknown reservation ID"
    raise ConvergenceError(msg)
