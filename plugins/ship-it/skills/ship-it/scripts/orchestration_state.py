#!/usr/bin/env python3
"""Validate orchestration events and focused acceptance recovery updates.

Called by bookkeeping.py inside its locked, atomic checkpoint transaction.
Returns JSON result fields; invalid input raises StateError (CLI exit 2).

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Final

from checkpoint_state import commit_id, non_empty, one_of, require

ISSUE_URL: Final[re.Pattern[str]] = re.compile(
    r"https://[^/]+/[^/]+/[^/]+/issues/[1-9][0-9]*",
)
CHILD_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "revision",
        "evidenceRevision",
        "evidenceRecordPath",
        "evidenceStatus",
        "gatedHead",
        "pullRequestUrl",
        "unresolvedThreadCount",
        "mergeCommit",
        "issueState",
        "nextAction",
        "requiredGates",
        "checkpointPath",
        "investigation",
    },
)
EVENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "dispatch",
        "child-update",
        "capacity-request",
        "capacity-grant",
        "capacity-release",
        "gate",
        "terminal",
    },
)
TERMINAL_STATUSES: Final[frozenset[str]] = frozenset({"completed", "blocked", "failed"})
NON_AGENT_GATES: Final[frozenset[str]] = frozenset(
    {"ci", "hosted-review", "local-checks"},
)


def issue_url(value: object, field: str) -> str:
    """Require an issue identity with a positive issue number."""
    text = non_empty(value, field)
    require(ISSUE_URL.fullmatch(text) is not None, f"{field} must be an issue URL")
    return text


def validate_saved_state(checkpoint: dict[str, Any]) -> None:
    """Reject malformed durable structures before any section is mutated."""
    graph = checkpoint.get("orchestration")
    if graph is None:
        return
    require(
        isinstance(graph, dict) and set(graph) == {"umbrellaUrl", "children", "events"},
        "saved orchestration requires umbrellaUrl, children and events",
    )
    issue_url(graph["umbrellaUrl"], "saved umbrellaUrl")
    require(isinstance(graph["children"], list), "saved children must be an array")
    identities: set[str] = set()
    for child in graph["children"]:
        require(
            isinstance(child, dict) and set(child) == set(new_child("identity")),
            "saved child has invalid fields",
        )
        identity = issue_url(child["issueUrl"], "saved child issueUrl")
        require(identity not in identities, "saved child identities must be unique")
        identities.add(identity)
        require(
            isinstance(child["dependencies"], list)
            and all(isinstance(item, str) for item in child["dependencies"]),
            "saved dependencies must be issue URL strings",
        )
        require(
            one_of(
                child["status"],
                frozenset({"pending", "running", "completed", "blocked", "failed"}),
            ),
            "invalid saved child status",
        )
        require(
            isinstance(child["gateVerdicts"], list)
            and all(isinstance(item, dict) for item in child["gateVerdicts"]),
            "saved gateVerdicts must be objects",
        )
        require(
            isinstance(child["capacityLeases"], list)
            and all(
                isinstance(item, dict)
                and set(item) == {"leaseId", "gate", "status"}
                and one_of(
                    item["status"],
                    frozenset({"requested", "active", "released"}),
                )
                for item in child["capacityLeases"]
            ),
            "invalid saved capacity leases",
        )
    require(
        all(
            dependency in identities
            for child in graph["children"]
            for dependency in child["dependencies"]
        ),
        "saved dependency names an unknown child",
    )
    events = graph["events"]
    require(
        isinstance(events, list)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("eventId"), str)
            and item["eventId"].strip()
            for item in events
        ),
        "saved events must have event IDs",
    )
    require(
        len({item["eventId"] for item in events}) == len(events),
        "saved event IDs must be unique",
    )


def set_orchestration(
    checkpoint: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    """Initialize or extend a graph, preserving dispatched children and events."""
    require(
        set(graph) == {"umbrellaUrl", "children", "nextAction"},
        "orchestration graph requires umbrellaUrl, children and nextAction",
    )
    umbrella = issue_url(graph["umbrellaUrl"], "umbrellaUrl")
    source_url = checkpoint["task"].get("sourceUrl")
    require(
        source_url == umbrella,
        "umbrellaUrl must match the checkpoint task sourceUrl",
    )
    children = graph["children"]
    require(
        isinstance(children, list) and children,
        "children must be a non-empty array",
    )
    old = checkpoint.get("orchestration")
    require(
        old is None or old["umbrellaUrl"] == umbrella,
        "umbrella identity cannot change",
    )
    existing = {child["issueUrl"]: child for child in old["children"]} if old else {}
    updated: dict[str, Any] = {}
    for child in children:
        require(
            isinstance(child, dict) and set(child) == {"issueUrl", "dependencies"},
            "graph children require exactly issueUrl and dependencies",
        )
        identity = issue_url(child["issueUrl"], "child issueUrl")
        require(
            identity != umbrella and identity not in updated,
            "child identities must be unique",
        )
        dependencies = child["dependencies"]
        require(
            isinstance(dependencies, list)
            and all(isinstance(item, str) for item in dependencies)
            and len(set(dependencies)) == len(dependencies),
            "dependencies must be unique issue URLs",
        )
        previous = existing.get(identity)
        require(
            previous is None
            or previous["dependencies"] == dependencies
            or previous["dispatchId"] is None,
            "dispatched dependencies cannot change",
        )
        updated[identity] = {
            **(previous or new_child(identity)),
            "dependencies": dependencies,
        }
    require(set(existing) <= set(updated), "recorded children cannot be removed")
    for identity, child in updated.items():
        require(
            all(dep in updated and dep != identity for dep in child["dependencies"]),
            "every dependency must name another recorded child",
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identity: str) -> None:
        require(identity not in visiting, "dependency graph contains a cycle")
        if identity in visited:
            return
        visiting.add(identity)
        for dependency in updated[identity]["dependencies"]:
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in updated:
        visit(identity)
    checkpoint["orchestration"] = {
        "umbrellaUrl": umbrella,
        "children": list(updated.values()),
        "events": old["events"] if old else [],
    }
    checkpoint["workflow"]["nextAction"] = non_empty(graph["nextAction"], "nextAction")
    return {"children": len(updated)}


def new_child(identity: str) -> dict[str, Any]:
    """Create an undispatched child with explicit unknown fields."""
    return {
        "issueUrl": identity,
        "dependencies": [],
        "status": "pending",
        "dispatchId": None,
        "worker": None,
        "worktree": None,
        "branch": None,
        "revision": None,
        "evidenceRevision": None,
        "evidenceRecordPath": None,
        "evidenceStatus": "disabled",
        "gatedHead": None,
        "pullRequestUrl": None,
        "unresolvedThreadCount": None,
        "mergeCommit": None,
        "issueState": "open",
        "nextAction": "Dispatch after dependencies complete",
        "gateVerdicts": [],
        "capacityLeases": [],
        "terminalEventId": None,
        "requiredGates": [],
        "checkpointPath": None,
        "investigation": None,
    }


def replay(events: list[dict[str, Any]], event: dict[str, Any]) -> bool:
    """Accept identical retries and reject reuse of an event ID with new data."""
    identity = non_empty(event.get("eventId"), "eventId")
    require(
        all(isinstance(item, dict) for item in events),
        "recorded events must be objects",
    )
    previous = next((item for item in events if item.get("eventId") == identity), None)
    require(
        previous is None or previous == event,
        "eventId already has different content",
    )
    return previous is not None


def record_event(checkpoint: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Apply one identity- and revision-bound child event exactly once."""
    require(
        set(event)
        == {
            "eventId",
            "kind",
            "issueUrl",
            "dispatchId",
            "expectedRevision",
            "data",
            "nextAction",
        },
        "event requires eventId, kind, issueUrl, dispatchId, expectedRevision, "
        "data and nextAction",
    )
    graph = checkpoint.get("orchestration")
    require(isinstance(graph, dict), "initialize orchestration before recording events")
    if replay(graph["events"], event):
        return {"eventId": event["eventId"], "applied": False}
    require(one_of(event["kind"], EVENT_KINDS), "invalid orchestration event kind")
    child = next(
        (item for item in graph["children"] if item["issueUrl"] == event["issueUrl"]),
        None,
    )
    require(child is not None, "event issueUrl is not a recorded child")
    require(
        child["terminalEventId"] is None
        or (event["kind"] == "dispatch" and child["status"] in {"blocked", "failed"}),
        "child already has a terminal event",
    )
    require(child["revision"] == event["expectedRevision"], "stale expectedRevision")
    non_empty(event["dispatchId"], "dispatchId")
    data = event["data"]
    require(isinstance(data, dict), "event data must be an object")
    if event["kind"] == "dispatch":
        dispatch(checkpoint, child, event)
    else:
        require(
            event["dispatchId"] == child["dispatchId"],
            "stale or unknown dispatchId",
        )
        apply_child_event(checkpoint, child, event)
    checkpoint["workflow"]["nextAction"] = non_empty(event["nextAction"], "nextAction")
    graph["events"].append(copy.deepcopy(event))
    return {"eventId": event["eventId"], "applied": True}


def dispatch(
    checkpoint: dict[str, Any],
    child: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Start one fresh worker after all prerequisites are delivered."""
    data = event["data"]
    require(
        child["dispatchId"] is None or child["status"] in {"blocked", "failed"},
        "child already dispatched",
    )
    require(
        set(data) == {"worker", "worktree", "branch", "revision"},
        "dispatch data requires worker, worktree, branch and revision",
    )
    siblings = checkpoint["orchestration"]["children"]
    require(
        all(item["dispatchId"] != event["dispatchId"] for item in siblings)
        and all(
            item["dispatchId"] != event["dispatchId"]
            for item in checkpoint["orchestration"]["events"]
            if item["kind"] == "dispatch"
        ),
        "dispatchId already used",
    )
    require(
        all(
            item["status"] == "completed"
            for item in siblings
            if item["issueUrl"] in child["dependencies"]
        ),
        "dependencies are not completed",
    )
    for field in ("worker", "worktree", "branch"):
        non_empty(data[field], field)
    commit_id(data["revision"], "revision")
    child.update(
        data,
        dispatchId=event["dispatchId"],
        status="running",
        terminalEventId=None,
        gateVerdicts=[],
        capacityLeases=[],
        gatedHead=None,
        evidenceRevision=None,
        evidenceRecordPath=None,
        evidenceStatus="missing"
        if checkpoint["bookkeeping"]["evidence"]
        else "disabled",
        pullRequestUrl=None,
        mergeCommit=None,
        issueState=None,
        unresolvedThreadCount=None,
        investigation=None,
    )


def apply_child_event(
    checkpoint: dict[str, Any],
    child: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Apply a supported event to the currently dispatched child."""
    kind, data = event["kind"], event["data"]
    if kind == "child-update":
        require(bool(data) and set(data) <= CHILD_FIELDS, "invalid child-update fields")
        validate_child_update(data)
        if "revision" in data and data["revision"] != child["revision"]:
            child.update(
                gateVerdicts=[],
                gatedHead=None,
                investigation=None,
                mergeCommit=None,
                evidenceRevision=None,
                evidenceStatus="missing"
                if checkpoint["bookkeeping"]["evidence"]
                else "disabled",
            )
        child.update(data)
    elif kind in {"capacity-request", "capacity-grant", "capacity-release"}:
        require(
            set(data) == {"leaseId", "gate"},
            "capacity data requires leaseId and gate",
        )
        for field in ("leaseId", "gate"):
            non_empty(data[field], field)
        leases = child["capacityLeases"]
        if kind == "capacity-request":
            require(
                not any(
                    lease["leaseId"] == data["leaseId"]
                    for sibling in checkpoint["orchestration"]["children"]
                    for lease in sibling["capacityLeases"]
                ),
                "leaseId already recorded",
            )
            leases.append({**data, "status": "requested"})
        else:
            lease = next(
                (item for item in leases if item["leaseId"] == data["leaseId"]),
                None,
            )
            expected = (
                {"requested"} if kind == "capacity-grant" else {"requested", "active"}
            )
            require(
                lease is not None
                and lease["status"] in expected
                and lease["gate"] == data["gate"],
                "capacity event requires matching lease and status",
            )
            lease["status"] = "active" if kind == "capacity-grant" else "released"
    elif kind == "gate":
        require(
            set(data) == {"gate", "status", "revision", "leaseId"},
            "gate data requires gate, status, revision and leaseId",
        )
        non_empty(data["gate"], "gate")
        require(data["revision"] == child["revision"], "gate revision is stale")
        require(
            one_of(data["status"], frozenset({"passed", "failed", "blocked"})),
            "invalid gate status",
        )
        require(
            (data["leaseId"] is None and data["gate"] in NON_AGENT_GATES)
            or any(
                lease["leaseId"] == data["leaseId"]
                and lease["gate"] == data["gate"]
                and lease["status"] == "active"
                for lease in child["capacityLeases"]
            ),
            "gate requires matching active capacity lease",
        )
        child["gateVerdicts"] = [
            item for item in child["gateVerdicts"] if item["gate"] != data["gate"]
        ] + [copy.deepcopy(data)]
    elif kind == "terminal":
        require(
            set(data) == {"status", "nextAction"},
            "terminal data requires status and nextAction",
        )
        require(one_of(data["status"], TERMINAL_STATUSES), "invalid terminal status")
        non_empty(data["nextAction"], "child nextAction")
        require(
            all(lease["status"] == "released" for lease in child["capacityLeases"]),
            "release active capacity leases before terminal event",
        )
        if data["status"] == "completed":
            validate_completed_child(checkpoint, child)
        child.update(data, terminalEventId=event["eventId"])


def validate_child_update(data: dict[str, Any]) -> None:
    """Validate the whitelisted worker delivery facts."""
    for field in ("revision", "evidenceRevision", "gatedHead", "mergeCommit"):
        if field in data and data[field] is not None:
            commit_id(data[field], field)
    for field in (
        "pullRequestUrl",
        "evidenceRecordPath",
        "nextAction",
        "checkpointPath",
    ):
        if field in data and data[field] is not None:
            non_empty(data[field], field)
    if "unresolvedThreadCount" in data:
        require(
            type(data["unresolvedThreadCount"]) is int
            and data["unresolvedThreadCount"] >= 0,
            "unresolvedThreadCount must be a non-negative integer",
        )
    if "issueState" in data:
        require(
            one_of(data["issueState"], frozenset({"open", "closed"})),
            "invalid issueState",
        )
    if "evidenceStatus" in data:
        require(
            one_of(
                data["evidenceStatus"],
                frozenset({"disabled", "missing", "stale", "complete"}),
            ),
            "invalid evidenceStatus",
        )
    if "requiredGates" in data:
        gates = data["requiredGates"]
        require(
            isinstance(gates, list)
            and bool(gates)
            and all(isinstance(item, str) and item.strip() for item in gates)
            and len(set(gates)) == len(gates),
            "requiredGates must be unique non-empty strings",
        )
    if "investigation" in data and data["investigation"] is not None:
        investigation = data["investigation"]
        require(
            isinstance(investigation, dict)
            and set(investigation) == {"reason", "evidence", "verifiedRevision"},
            "investigation requires reason, evidence and verifiedRevision",
        )
        non_empty(investigation["reason"], "investigation reason")
        commit_id(investigation["verifiedRevision"], "investigation verifiedRevision")
        require(
            isinstance(investigation["evidence"], list)
            and investigation["evidence"]
            and all(
                isinstance(item, str) and item.strip()
                for item in investigation["evidence"]
            ),
            "investigation evidence must be non-empty strings",
        )


def validate_completed_child(checkpoint: dict[str, Any], child: dict[str, Any]) -> None:
    """Reject completion without revision-bound gates and delivery facts."""
    require(
        child["gatedHead"] == child["revision"] and child["gatedHead"] is not None,
        "completed child requires gatedHead matching revision",
    )
    require(
        child["issueState"] == "closed" and child["unresolvedThreadCount"] == 0,
        "completed child requires closed issue and no unresolved threads",
    )
    if child["investigation"] is None:
        require(
            child["mergeCommit"] is not None and child["pullRequestUrl"] is not None,
            "completed child requires merged PR facts or an investigation",
        )
    else:
        require(
            child["investigation"]["verifiedRevision"] == child["revision"]
            and child["pullRequestUrl"] is None
            and child["mergeCommit"] is None,
            "investigation requires matching revision and null delivery facts",
        )
    require(
        bool(child["gateVerdicts"])
        and all(
            item["status"] == "passed" and item["revision"] == child["gatedHead"]
            for item in child["gateVerdicts"]
        ),
        "completed child requires passing gates on gatedHead",
    )
    require(
        bool(child["requiredGates"])
        and set(child["requiredGates"])
        <= {item["gate"] for item in child["gateVerdicts"]},
        "completed child requires every selected gate",
    )
    if checkpoint["bookkeeping"]["evidence"]:
        require(
            child["evidenceStatus"] == "complete"
            and child["evidenceRevision"] == child["gatedHead"]
            and child["evidenceRecordPath"] is not None,
            "completed child requires matching complete evidence",
        )


def record_acceptance_recovery(
    checkpoint: dict[str, Any],
    recovery: dict[str, Any],
) -> dict[str, Any]:
    """Append one focused correction under an existing active user grant."""
    require(
        set(recovery)
        == {
            "eventId",
            "failure",
            "criterion",
            "grantId",
            "revision",
            "correction",
            "verification",
            "result",
        },
        "recovery requires eventId, failure, criterion, grantId, revision, "
        "correction, verification and result",
    )
    history = checkpoint["convergence"].setdefault("acceptanceRecovery", [])
    require(isinstance(history, list), "acceptanceRecovery must be an array")
    if replay(history, recovery):
        return {"eventId": recovery["eventId"], "applied": False}
    for field in ("failure", "criterion", "grantId", "correction", "verification"):
        non_empty(recovery[field], field)
    require(
        recovery["criterion"] in checkpoint["task"].get("acceptanceCriteria", []),
        "recovery criterion must match a recorded acceptance criterion",
    )
    commit_id(recovery["revision"], "recovery revision")
    require(
        recovery["revision"] == checkpoint["workflow"]["revision"],
        "recovery revision is stale",
    )
    require(
        one_of(recovery["result"], frozenset({"passed", "failed", "blocked"})),
        "invalid recovery result",
    )
    grant = next(
        (
            item
            for item in checkpoint["authorization"]["grants"]
            if item["id"] == recovery["grantId"]
        ),
        None,
    )
    require(
        grant is not None and grant["status"] == "active",
        "recovery requires an active recorded grant",
    )
    require(
        all(limit["used"] < limit["maximum"] for limit in grant["limits"]),
        "recovery grant allowance is exhausted",
    )
    history.append(copy.deepcopy(recovery))
    return {"eventId": recovery["eventId"], "applied": True}
