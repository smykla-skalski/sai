#!/usr/bin/env python3
"""Resolve ship-it bookkeeping and atomically transition a checkpoint.

Usage:
  bookkeeping.py policy --repository PATH [--enable FEATURE,...]
  bookkeeping.py reconcile-delivery --checkpoint FILE
      (--pull-request-json OBJECT | --failure TEXT)
  bookkeeping.py transition --checkpoint FILE --phase PHASE --status STATUS
      --next-action TEXT [--revision SHA] [--blocker TEXT]
      [--outcome-json OBJECT]
  bookkeeping.py reserve --checkpoint FILE --id ID --kind KIND
      --revision SHA (--inputs FINGERPRINT | --inputs-json MANIFEST)
      [--reason TEXT] [--trigger CATEGORY]
      [--grant ID]
  bookkeeping.py assess --checkpoint FILE --kind KIND
      --revision SHA --inputs-json MANIFEST
  bookkeeping.py finish --checkpoint FILE --id ID --result-json OBJECT
  bookkeeping.py create --repository PATH --identity TEXT --source-json OBJECT
      --title TEXT --objective TEXT --criteria-json ARRAY [--source-url URL]
      [--default-branch NAME] [--branch NAME] [--enable FEATURE,...]
      [--grant-json OBJECT]... [--checkpoint-dir DIR]
  bookkeeping.py set-risk --checkpoint FILE --risk-json OBJECT
  bookkeeping.py set-release-policy --checkpoint FILE --policy-json OBJECT
  bookkeeping.py record-gate --checkpoint FILE --verdict-json OBJECT
  bookkeeping.py add-grant --checkpoint FILE --grant-json OBJECT
  bookkeeping.py set-findings --checkpoint FILE --dispositions-json OBJECT
  bookkeeping.py attest-review --checkpoint FILE --revision SHA --summary TEXT
      [--gate GATE] [--command TEXT]...

Output is one compact JSON result on stdout. Input or validation errors are
reported on stderr and exit 2; successful policy resolution or transition
exits 0.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

import checkpoint_state
import orchestration_state
from checkpoint_state import StateError
from convergence import (
    ConvergenceError,
    finish,
    reserve,
)
from convergence import (
    validate as validate_convergence,
)
from handoff import record_handoff
from validation_reuse import assess, capture, digest, unavailable_decision

SECTION_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "set-risk",
        "set-release-policy",
        "set-hosted-review-decision",
        "record-gate",
        "add-grant",
        "set-findings",
        "attest-review",
        "set-orchestration",
        "record-orchestration-event",
        "record-acceptance-recovery",
    },
)
JSON_SECTION_COMMANDS: Final[
    dict[str, tuple[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]]]
] = {
    "set-risk": ("--risk-json", checkpoint_state.set_risk),
    "set-release-policy": ("--policy-json", checkpoint_state.set_release_policy),
    "set-hosted-review-decision": (
        "--decision-json",
        checkpoint_state.set_hosted_review_decision,
    ),
    "record-gate": ("--verdict-json", checkpoint_state.record_gate),
    "add-grant": ("--grant-json", checkpoint_state.add_grant),
    "set-findings": ("--dispositions-json", checkpoint_state.set_dispositions),
    "set-orchestration": (
        "--orchestration-json",
        orchestration_state.set_orchestration,
    ),
    "record-orchestration-event": ("--event-json", orchestration_state.record_event),
    "record-acceptance-recovery": (
        "--recovery-json",
        orchestration_state.record_acceptance_recovery,
    ),
}
FEATURES: Final[tuple[str, ...]] = ("claims", "evidence", "telemetry")
POLICY_PATH: Final[Path] = Path(".sai/ship-it-bookkeeping.json")
VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {"active", "blocked", "completed", "cancelled", "failed"},
)
VALID_PHASES: Final[frozenset[str]] = frozenset(
    {
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
        "complete",
    },
)
TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "cancelled", "failed"},
)
PULL_REQUEST_STATES: Final[frozenset[str]] = frozenset(
    {"open", "closed-unmerged", "merged"},
)
FULL_COMMIT_ID: Final[re.Pattern[str]] = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
REQUIRED_CHECKPOINT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schemaVersion",
        "checkpointId",
        "task",
        "repository",
        "workflow",
        "delivery",
        "evidence",
        "gateVerdicts",
        "claim",
        "bookkeeping",
        "risk",
        "releasePolicy",
        "hostedReviewDecision",
        "convergence",
        "authorization",
        "ciTriage",
        "orchestration",
        "outcome",
        "createdAt",
        "updatedAt",
    },
)
REQUIRED_WORKFLOW_FIELDS: Final[frozenset[str]] = frozenset(
    {"phase", "status", "revision", "blocker", "unresolvedQuestions", "nextAction"},
)


@contextmanager
def checkpoint_lock(path: Path) -> Iterator[None]:
    """Serialize read/validate/write transactions across processes and harnesses."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path.with_suffix(path.suffix + ".lock"),
        os.O_CREAT | os.O_RDWR,
        0o600,
    )
    with os.fdopen(descriptor, "a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class BookkeepingError(ValueError):
    """A deterministic input or state validation error."""


def parse_enabled(value: str) -> set[str]:
    """Parse and validate an explicit comma-separated feature list."""
    enabled = {item.strip() for item in value.split(",") if item.strip()}
    unknown = enabled.difference(FEATURES)
    if unknown:
        names = ", ".join(sorted(unknown))
        message = f"unknown bookkeeping feature: {names}"
        raise BookkeepingError(message)
    return enabled


def load_object(path: Path) -> dict[str, Any]:
    """Load a JSON object or raise a deterministic validation error."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        message = f"cannot read JSON object {path}: {error}"
        raise BookkeepingError(message) from error
    if not isinstance(value, dict):
        message = f"expected JSON object: {path}"
        raise BookkeepingError(message)
    return value


def resolve_policy(repository: Path, explicit: set[str]) -> dict[str, Any]:
    """Resolve bookkeeping features from repo policy and user input."""
    values = {"claims": False, "evidence": False, "telemetry": True}
    source = "bundled default"
    policy_file = repository / POLICY_PATH
    if policy_file.is_file():
        raw = load_object(policy_file)
        unknown = set(raw).difference(FEATURES)
        if unknown:
            names = ", ".join(sorted(unknown))
            message = f"unknown policy field: {names}"
            raise BookkeepingError(message)
        for feature in FEATURES:
            if feature in raw:
                if not isinstance(raw[feature], bool):
                    message = f"policy field {feature} must be boolean"
                    raise BookkeepingError(message)
                values[feature] = raw[feature]
        source = POLICY_PATH.as_posix()
    if explicit:
        for feature in explicit:
            values[feature] = True
        source = "explicit user request"
    return {**values, "policySource": source}


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    """Replace a JSON file atomically while retaining its previous version."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                value,
                stream,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_workflow(workflow: dict[str, Any]) -> None:
    """Validate the workflow object and its status coupling."""
    missing_workflow = REQUIRED_WORKFLOW_FIELDS.difference(workflow)
    if missing_workflow:
        names = ", ".join(sorted(missing_workflow))
        message = f"checkpoint.workflow missing required fields: {names}"
        raise BookkeepingError(message)

    phase = workflow["phase"]
    status = workflow["status"]
    blocker = workflow["blocker"]
    next_action = workflow["nextAction"]
    if not isinstance(phase, str) or phase not in VALID_PHASES:
        message = f"invalid workflow phase: {phase}"
        raise BookkeepingError(message)
    if not isinstance(status, str) or status not in VALID_STATUSES:
        message = f"invalid workflow status: {status}"
        raise BookkeepingError(message)
    if not isinstance(next_action, str) or not next_action.strip():
        message = "checkpoint.workflow.nextAction must be non-empty"
        raise BookkeepingError(message)
    if status == "blocked" and (not isinstance(blocker, str) or not blocker.strip()):
        message = "blocked workflow requires a non-empty blocker"
        raise BookkeepingError(message)
    if status != "blocked" and blocker is not None:
        message = "non-blocked workflow requires a null blocker"
        raise BookkeepingError(message)


def migrate_legacy(checkpoint: dict[str, Any]) -> None:
    """Add only documented defaults for known schema-v1 legacy shapes."""
    if checkpoint.get("schemaVersion") != 1:
        return
    task = checkpoint.get("task")
    github_source = isinstance(task, dict) and task.get("sourceType") == "github"
    delivery = checkpoint.get("delivery")
    if isinstance(delivery, dict):
        delivery.setdefault("pullRequestState", None)
        delivery.setdefault("mergedAt", None)
        delivery.setdefault("reconciliation", None)
    checkpoint.setdefault("authorization", {"grants": []})
    checkpoint.setdefault("claim", None)
    checkpoint.setdefault("releasePolicy", None)
    checkpoint.setdefault("hostedReviewDecision", None)
    checkpoint.setdefault(
        "bookkeeping",
        {
            "claims": github_source,
            "evidence": True,
            "telemetry": True,
            "policySource": "legacy compatibility",
        },
    )
    checkpoint.setdefault(
        "risk",
        {
            "level": None,
            "diffClass": None,
            "policySource": None,
            "matchedRules": [],
            "requiredGates": [],
            "overrideAuthorization": None,
        },
    )
    checkpoint.setdefault("ciTriage", {"failures": []})
    checkpoint.setdefault("gateVerdicts", [])
    checkpoint.setdefault(
        "convergence",
        {
            "mode": "bounded",
            "authorizedBy": None,
            "startedAt": None,
            "reviewCycles": 0,
            "fixPasses": 0,
            "fullQualityGateRuns": 0,
            "reviewedRevision": None,
            "findings": [],
            "followUpIssues": [],
        },
    )


def validate_identity(checkpoint: dict[str, Any], path: Path) -> None:
    """Validate checkpoint filename and canonical-source identity."""
    checkpoint_id = checkpoint.get("checkpointId")
    task = checkpoint.get("task")
    canonical = task.get("canonicalSource") if isinstance(task, dict) else None
    if not isinstance(checkpoint_id, str) or not isinstance(canonical, str):
        message = "checkpoint identity fields must be strings"
        raise BookkeepingError(message)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    if checkpoint_id != digest or path.name != f"{checkpoint_id}.json":
        message = "checkpoint ID, canonical source, and filename must match"
        raise BookkeepingError(message)


def validate_authorization(checkpoint: dict[str, Any]) -> None:
    """Reject incomplete authority without inferring or expanding a grant."""
    authorization = checkpoint.get("authorization")
    if not isinstance(authorization, dict) or not isinstance(
        authorization.get("grants"),
        list,
    ):
        message = "authorization requires a grants array"
        raise BookkeepingError(message)
    identities: set[str] = set()
    for grant in authorization["grants"]:
        if not isinstance(grant, dict):
            message = "authorization grant must be an object"
            raise BookkeepingError(message)
        identity = grant.get("id")
        if (
            not isinstance(identity, str)
            or not identity.strip()
            or identity in identities
        ):
            message = "authorization grant IDs must be non-empty and unique"
            raise BookkeepingError(message)
        identities.add(identity)
        if grant.get("status") not in ("active", "ambiguous", "revoked", "exhausted"):
            message = "invalid authorization grant status"
            raise BookkeepingError(message)
        validate_authorization_source(grant.get("source"))
        scope = grant.get("scope")
        if (
            not isinstance(scope, list)
            or not scope
            or any(not isinstance(item, str) or not item.strip() for item in scope)
        ):
            message = "authorization grant scope must be a non-empty array of strings"
            raise BookkeepingError(message)
        validate_authorization_limits(grant.get("limits"))


def validate_authorization_source(source: object) -> None:
    """Require the original user source and concrete request for approval replies."""
    if not isinstance(source, dict) or source.get("kind") not in (
        "user-request",
        "user-reply",
    ):
        message = "authorization source must identify the original user"
        raise BookkeepingError(message)
    for field in ("message", "reference"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            message = f"authorization source requires {field}"
            raise BookkeepingError(message)
    request = source.get("request")
    if source["kind"] == "user-reply" and (
        not isinstance(request, str) or not request.strip()
    ):
        message = "authorization reply requires the concrete pending request"
        raise BookkeepingError(message)


def validate_authorization_limits(limits: object) -> None:
    """Validate explicit allowances and retained consumed amounts."""
    if not isinstance(limits, list):
        message = "authorization limits must be an array"
        raise BookkeepingError(message)
    for limit in limits:
        if not isinstance(limit, dict):
            message = "authorization limit must be an object"
            raise BookkeepingError(message)
        resource = limit.get("resource")
        if not isinstance(resource, str) or not resource.strip():
            message = "authorization limit requires a resource with units"
            raise BookkeepingError(message)
        maximum, used = limit.get("maximum"), limit.get("used")
        if type(maximum) is not int or type(used) is not int:
            message = "authorization limit maximum and used must be integers"
            raise BookkeepingError(message)
        if maximum < 0 or used < 0 or used > maximum:
            message = "authorization consumed amount must stay within its limit"
            raise BookkeepingError(message)


def validate_bookkeeping(checkpoint: dict[str, Any]) -> None:
    """Validate optional bookkeeping state coupling."""
    bookkeeping = checkpoint.get("bookkeeping")
    evidence = checkpoint.get("evidence")
    if not isinstance(bookkeeping, dict) or not isinstance(evidence, dict):
        message = "checkpoint bookkeeping and evidence must be objects"
        raise BookkeepingError(message)
    for feature in FEATURES:
        if not isinstance(bookkeeping.get(feature), bool):
            message = f"checkpoint bookkeeping.{feature} must be boolean"
            raise BookkeepingError(message)
    if not bookkeeping["claims"] and checkpoint.get("claim") is not None:
        message = "disabled claims require claim: null"
        raise BookkeepingError(message)
    if not bookkeeping["evidence"]:
        disabled = (
            evidence.get("status") == "disabled"
            and evidence.get("revision") is None
            and evidence.get("recordPath") is None
        )
        if not disabled:
            message = "disabled evidence requires null pointers and disabled status"
            raise BookkeepingError(message)


def validate_commit_id(value: object, field: str) -> None:
    """Require a full hexadecimal Git object ID."""
    if not isinstance(value, str) or FULL_COMMIT_ID.fullmatch(value) is None:
        message = f"{field} must be a full hexadecimal commit ID"
        raise BookkeepingError(message)


def validate_utc_timestamp(value: object, field: str) -> None:
    """Require an RFC 3339 timestamp whose offset is UTC."""
    if not isinstance(value, str) or "T" not in value:
        message = f"{field} must be an RFC 3339 UTC timestamp"
        raise BookkeepingError(message)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        message = f"{field} must be an RFC 3339 UTC timestamp"
        raise BookkeepingError(message) from error
    if parsed.utcoffset() != timedelta(0):
        message = f"{field} must be an RFC 3339 UTC timestamp"
        raise BookkeepingError(message)


def validate_delivery_facts(delivery: dict[str, Any], state: object) -> None:
    """Validate pull request object IDs and merge facts."""
    for field in ("pullRequestHead", "mergeCommit"):
        value = delivery.get(field)
        if value is not None:
            validate_commit_id(value, f"checkpoint.delivery.{field}")
    if delivery.get("mergedAt") is not None:
        validate_utc_timestamp(
            delivery["mergedAt"],
            "checkpoint.delivery.mergedAt",
        )
    if state == "merged":
        for field in ("pullRequestUrl", "pullRequestHead", "mergeCommit", "mergedAt"):
            value = delivery.get(field)
            if not isinstance(value, str) or not value.strip():
                message = f"merged delivery requires {field}"
                raise BookkeepingError(message)
    if state in {"open", "closed-unmerged"} and (
        delivery.get("mergeCommit") is not None or delivery.get("mergedAt") is not None
    ):
        message = "unmerged delivery cannot retain merge facts"
        raise BookkeepingError(message)


def validate_delivery(checkpoint: dict[str, Any]) -> None:
    """Validate durable pull request facts and their reconciliation audit."""
    delivery = checkpoint.get("delivery")
    if not isinstance(delivery, dict):
        message = "checkpoint.delivery must be an object"
        raise BookkeepingError(message)
    state = delivery.get("pullRequestState")
    if state is not None and state not in PULL_REQUEST_STATES:
        message = "checkpoint.delivery has invalid pullRequestState"
        raise BookkeepingError(message)
    validate_delivery_facts(delivery, state)
    reconciliation = delivery.get("reconciliation")
    if reconciliation is None:
        return
    validate_delivery_reconciliation(reconciliation)


def validate_delivery_reconciliation(reconciliation: object) -> None:
    """Validate the last authoritative delivery read or connection failure."""
    if not isinstance(reconciliation, dict):
        message = "checkpoint.delivery.reconciliation must be an object or null"
        raise BookkeepingError(message)
    status = reconciliation.get("status")
    if status not in {"matched", "unreachable"}:
        message = "delivery reconciliation has invalid status"
        raise BookkeepingError(message)
    checked_at = reconciliation.get("checkedAt")
    validate_utc_timestamp(checked_at, "delivery reconciliation checkedAt")
    error = reconciliation.get("error")
    if status == "matched" and error is not None:
        message = "matched delivery reconciliation requires a null error"
        raise BookkeepingError(message)
    if status == "unreachable" and (not isinstance(error, str) or not error.strip()):
        message = "unreachable delivery reconciliation requires an error"
        raise BookkeepingError(message)


def outcome_fields(result: object) -> set[str]:
    """Return required fields for a terminal outcome result."""
    common = {"sourceState", "completedAt"}
    if result == "merged":
        return common | {
            "pullRequestUrl",
            "pullRequestHead",
            "mergeCommit",
            "branchCleanup",
        }
    if result == "coordinated":
        return common | {"umbrellaUrl", "children"}
    if result == "already-satisfied":
        return common | {"reason", "branchCleanup", "verifiedRevision", "evidence"}
    return common | {"reason", "branchCleanup"}


def validate_outcome_values(result: object, outcome: dict[str, Any]) -> None:
    """Validate terminal outcome enums and result-specific values."""
    if outcome["sourceState"] not in {"closed", "unchanged", "not-applicable"}:
        message = "terminal outcome has invalid sourceState"
        raise BookkeepingError(message)
    cleanup = outcome.get("branchCleanup")
    if cleanup is not None and cleanup not in {
        "deleted",
        "preserved",
        "not-applicable",
    }:
        message = "terminal outcome has invalid branchCleanup"
        raise BookkeepingError(message)
    if result == "coordinated":
        if not isinstance(outcome["children"], list):
            message = "coordinated outcome children must be an array"
            raise BookkeepingError(message)
        if outcome["sourceState"] != "closed":
            message = "coordinated outcome requires closed sourceState"
            raise BookkeepingError(message)
    if result in {"cancelled", "failed"} and (
        outcome["sourceState"] != "unchanged" or cleanup != "not-applicable"
    ):
        message = "undelivered outcome requires unchanged source and no cleanup"
        raise BookkeepingError(message)


def validate_outcome(status: str, outcome: dict[str, Any]) -> None:
    """Validate terminal outcome fields for the selected terminal status."""
    result = outcome.get("result")
    if status == "completed" and result not in {
        "merged",
        "coordinated",
        "already-satisfied",
    }:
        message = (
            "completed outcome result must be merged, coordinated or already-satisfied"
        )
        raise BookkeepingError(message)
    if status in {"cancelled", "failed"} and result != status:
        message = f"{status} outcome result must match its status"
        raise BookkeepingError(message)

    required = outcome_fields(result)
    missing = required.difference(outcome)
    if missing:
        names = ", ".join(sorted(missing))
        message = f"terminal outcome missing required fields: {names}"
        raise BookkeepingError(message)
    for field in required.difference({"children", "evidence"}):
        if not isinstance(outcome[field], str) or not outcome[field].strip():
            message = f"terminal outcome field {field} must be non-empty"
            raise BookkeepingError(message)
    validate_outcome_values(result, outcome)
    if result == "already-satisfied":
        validate_satisfied_values(outcome)


def validate_satisfied_values(outcome: dict[str, Any]) -> None:
    """Require explicit investigation evidence without manufactured delivery."""
    evidence = outcome["evidence"]
    if (
        not isinstance(evidence, list)
        or not evidence
        or not all(isinstance(item, str) and item.strip() for item in evidence)
    ):
        message = "already-satisfied outcome requires non-empty evidence strings"
        raise BookkeepingError(message)
    validate_commit_id(outcome["verifiedRevision"], "verifiedRevision")
    validate_utc_timestamp(outcome["completedAt"], "completedAt")
    if outcome["sourceState"] != "closed" or outcome["branchCleanup"] not in {
        "preserved",
        "not-applicable",
    }:
        message = (
            "already-satisfied outcome requires closed source and no branch deletion"
        )
        raise BookkeepingError(message)
    if any(
        outcome.get(field) is not None
        for field in (
            "pullRequestUrl",
            "pullRequestHead",
            "mergeCommit",
        )
    ):
        message = "already-satisfied outcome must not claim PR delivery"
        raise BookkeepingError(message)


def validate_satisfied_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Bind a no-change investigation to its verified revision and selected gates."""
    outcome = checkpoint["outcome"]
    if outcome.get("result") != "already-satisfied":
        return
    revision = outcome["verifiedRevision"]
    if checkpoint["workflow"]["revision"] != revision:
        message = "already-satisfied verifiedRevision must match workflow revision"
        raise BookkeepingError(message)
    if any(value is not None for value in checkpoint["delivery"].values()):
        message = "already-satisfied checkpoint must have null delivery state"
        raise BookkeepingError(message)
    required = checkpoint["risk"].get("requiredGates", [])
    passed = {
        verdict.get("gate")
        for verdict in checkpoint["gateVerdicts"]
        if verdict.get("status") == "passed" and verdict.get("revision") == revision
    }
    if not required or not set(required) <= passed:
        message = "already-satisfied requires every selected gate on verifiedRevision"
        raise BookkeepingError(message)


def validate_merged_delivery(
    checkpoint: dict[str, Any],
    outcome: dict[str, Any],
    *,
    allow_unreconciled_legacy: bool = False,
) -> None:
    """Require a merged outcome to repeat the validated delivery identity."""
    if outcome.get("result") != "merged":
        return
    delivery = checkpoint.get("delivery")
    if not isinstance(delivery, dict):
        message = "merged outcome requires delivery state"
        raise BookkeepingError(message)
    unreconciled_legacy = (
        delivery.get("pullRequestState") is None
        and delivery.get("mergedAt") is None
        and delivery.get("reconciliation") is None
    )
    if delivery.get("pullRequestState") != "merged" and not (
        allow_unreconciled_legacy and unreconciled_legacy
    ):
        message = "merged outcome requires delivery.pullRequestState merged"
        raise BookkeepingError(message)
    reconciliation = delivery.get("reconciliation")
    if (
        not isinstance(reconciliation, dict)
        or reconciliation.get("status") != "matched"
    ) and not (allow_unreconciled_legacy and unreconciled_legacy):
        message = "merged outcome requires matched delivery reconciliation"
        raise BookkeepingError(message)
    for field in ("pullRequestUrl", "pullRequestHead", "mergeCommit"):
        if outcome[field] != delivery.get(field):
            message = f"merged outcome {field} must match delivery.{field}"
            raise BookkeepingError(message)
    workflow = checkpoint["workflow"]
    if outcome["pullRequestHead"] != workflow.get("revision"):
        message = "merged outcome pullRequestHead must match workflow.revision"
        raise BookkeepingError(message)


def validate_checkpoint(
    checkpoint: dict[str, Any],
    path: Path,
    *,
    allow_unreconciled_legacy: bool = False,
) -> None:
    """Validate fields and invariants affected by a workflow transition."""
    missing = REQUIRED_CHECKPOINT_FIELDS.difference(checkpoint)
    if missing:
        names = ", ".join(sorted(missing))
        message = f"checkpoint missing required fields: {names}"
        raise BookkeepingError(message)
    validate_identity(checkpoint, path)
    validate_bookkeeping(checkpoint)
    validate_delivery(checkpoint)
    validate_authorization(checkpoint)
    orchestration_state.validate_saved_state(checkpoint)
    validate_convergence(checkpoint)
    if checkpoint.get("schemaVersion") != 1:
        message = "unsupported checkpoint schemaVersion"
        raise BookkeepingError(message)
    if not isinstance(checkpoint.get("gateVerdicts"), list):
        message = "checkpoint.gateVerdicts must be an array"
        raise BookkeepingError(message)

    workflow = checkpoint.get("workflow")
    if not isinstance(workflow, dict):
        message = "checkpoint.workflow must be an object"
        raise BookkeepingError(message)
    validate_workflow(workflow)

    phase = workflow["phase"]
    status = workflow["status"]
    if phase == "complete":
        terminal_outcome = status in TERMINAL_STATUSES and isinstance(
            checkpoint["outcome"],
            dict,
        )
        if not terminal_outcome:
            message = "complete workflow requires terminal status and outcome"
            raise BookkeepingError(message)
        validate_outcome(status, checkpoint["outcome"])
        validate_merged_delivery(
            checkpoint,
            checkpoint["outcome"],
            allow_unreconciled_legacy=allow_unreconciled_legacy,
        )
        validate_satisfied_checkpoint(checkpoint)
    elif status in TERMINAL_STATUSES or checkpoint["outcome"] is not None:
        message = "terminal status and outcome require phase complete"
        raise BookkeepingError(message)


def resolve_outcome(args: argparse.Namespace) -> dict[str, Any] | None:
    """Parse the outcome for a terminal transition."""
    if args.phase == "complete":
        if args.outcome_json is None:
            message = "--outcome-json is required for phase complete"
            raise BookkeepingError(message)
        try:
            outcome = json.loads(args.outcome_json)
        except json.JSONDecodeError as error:
            message = f"invalid --outcome-json: {error}"
            raise BookkeepingError(message) from error
        if not isinstance(outcome, dict):
            message = "--outcome-json must contain an object"
            raise BookkeepingError(message)
        return outcome
    if args.outcome_json is not None:
        message = "--outcome-json is valid only for phase complete"
        raise BookkeepingError(message)
    return None


def transition(args: argparse.Namespace) -> dict[str, Any]:
    """Apply one validated workflow transition under the shared checkpoint lock."""
    with checkpoint_lock(Path(args.checkpoint).resolve()):
        return transition_locked(args)


def pull_request_merge_commit(remote: dict[str, Any]) -> str | None:
    """Return the merge commit from gh's scalar or object representation."""
    value = remote.get("mergeCommit")
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("oid"), str):
        return value["oid"]
    message = "pull request mergeCommit must be a commit ID, object, or null"
    raise BookkeepingError(message)


def parse_pull_request(value: str) -> dict[str, Any]:
    """Parse the authoritative gh pull request observation."""
    try:
        remote = json.loads(value)
    except json.JSONDecodeError as error:
        message = f"invalid --pull-request-json: {error}"
        raise BookkeepingError(message) from error
    if not isinstance(remote, dict):
        message = "--pull-request-json must contain an object"
        raise BookkeepingError(message)
    url = remote.get("url")
    head = remote.get("headRefOid")
    state = remote.get("state")
    if not isinstance(url, str) or not url.strip():
        message = "pull request observation requires url"
        raise BookkeepingError(message)
    validate_commit_id(head, "pull request observation headRefOid")
    if not isinstance(state, str) or state.upper() not in {"OPEN", "CLOSED", "MERGED"}:
        message = "pull request observation has invalid state"
        raise BookkeepingError(message)
    return remote


def reconcile_pull_request(
    delivery: dict[str, Any],
    remote: dict[str, Any],
    now: str,
) -> str:
    """Apply one matching authoritative pull request observation."""
    url = remote["url"]
    stored_url = delivery.get("pullRequestUrl")
    if stored_url is not None and stored_url != url:
        message = (
            "pull request identity mismatch: "
            f"checkpoint has {stored_url}, remote returned {url}"
        )
        raise BookkeepingError(message)
    remote_state = {
        "OPEN": "open",
        "CLOSED": "closed-unmerged",
        "MERGED": "merged",
    }[remote["state"].upper()]
    confirmed_merged = (
        delivery.get("pullRequestState") == "merged"
        or delivery.get("mergeCommit") is not None
        or delivery.get("mergedAt") is not None
    )
    if confirmed_merged and remote_state != "merged":
        message = "confirmed merged delivery conflicts with remote pull request state"
        raise BookkeepingError(message)
    merge_commit = pull_request_merge_commit(remote)
    merged_at = remote.get("mergedAt")
    if remote_state == "merged":
        reconcile_merged_pull_request(
            delivery,
            remote,
            merge_commit,
            merged_at,
            confirmed_merged=confirmed_merged,
        )
    elif merge_commit is not None or merged_at is not None:
        message = "unmerged pull request observation contains merge facts"
        raise BookkeepingError(message)
    delivery.update(
        {
            "pullRequestUrl": url,
            "pullRequestHead": remote["headRefOid"],
            "pullRequestState": remote_state,
            "reconciliation": {
                "status": "matched",
                "checkedAt": now,
                "error": None,
            },
        },
    )
    return remote_state


def reconcile_merged_pull_request(
    delivery: dict[str, Any],
    remote: dict[str, Any],
    merge_commit: str | None,
    merged_at: object,
    *,
    confirmed_merged: bool,
) -> None:
    """Validate and retain authoritative merge facts without downgrades."""
    validate_commit_id(merge_commit, "merged pull request observation mergeCommit")
    validate_utc_timestamp(merged_at, "merged pull request observation mergedAt")
    if confirmed_merged:
        for field, observed in (
            ("pullRequestHead", remote["headRefOid"]),
            ("mergeCommit", merge_commit),
            ("mergedAt", merged_at),
        ):
            stored = delivery.get(field)
            if stored is not None and stored != observed:
                message = f"confirmed delivery {field} conflicts with remote"
                raise BookkeepingError(message)
    delivery["mergeCommit"] = merge_commit
    delivery["mergedAt"] = merged_at


def reconcile_delivery(args: argparse.Namespace) -> dict[str, Any]:
    """Reconcile checkpoint delivery facts with one authoritative remote read."""
    path = Path(args.checkpoint).resolve()
    with checkpoint_lock(path):
        checkpoint = load_object(path)
        migrate_legacy(checkpoint)
        validate_checkpoint(checkpoint, path, allow_unreconciled_legacy=True)
        delivery = checkpoint["delivery"]
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        if args.failure is not None:
            if not args.failure.strip():
                message = "--failure must be non-empty"
                raise BookkeepingError(message)
            delivery["reconciliation"] = {
                "status": "unreachable",
                "checkedAt": now,
                "error": args.failure,
            }
            result = "unreachable"
        else:
            remote = parse_pull_request(args.pull_request_json)
            result = reconcile_pull_request(delivery, remote, now)
        checkpoint["updatedAt"] = now
        validate_checkpoint(checkpoint, path)
        atomic_write(path, checkpoint)
        return {
            "checkpoint": str(path),
            "result": result,
            "pullRequestUrl": delivery.get("pullRequestUrl"),
        }


def transition_locked(args: argparse.Namespace) -> dict[str, Any]:
    """Apply a transition after acquiring the transaction lock."""
    checkpoint_path = Path(args.checkpoint).resolve()
    checkpoint = load_object(checkpoint_path)
    migrate_legacy(checkpoint)
    validate_checkpoint(checkpoint, checkpoint_path)
    workflow = checkpoint["workflow"]
    if args.phase not in VALID_PHASES:
        message = f"invalid workflow phase: {args.phase}"
        raise BookkeepingError(message)
    if args.status not in VALID_STATUSES:
        message = f"invalid workflow status: {args.status}"
        raise BookkeepingError(message)
    if args.status == "blocked" and not args.blocker:
        message = "--blocker is required for blocked status"
        raise BookkeepingError(message)
    if args.status != "blocked" and args.blocker:
        message = "--blocker is valid only for blocked status"
        raise BookkeepingError(message)
    workflow["phase"] = args.phase
    workflow["status"] = args.status
    workflow["blocker"] = args.blocker
    workflow["nextAction"] = args.next_action
    checkpoint["outcome"] = resolve_outcome(args)
    if args.phase == "complete":
        workflow["unresolvedQuestions"] = []
    if args.revision is not None:
        workflow["revision"] = args.revision
    checkpoint["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    validate_checkpoint(checkpoint, checkpoint_path)
    atomic_write(checkpoint_path, checkpoint)
    return {
        "checkpoint": str(checkpoint_path),
        "phase": args.phase,
        "status": args.status,
        "transition": "applied",
    }


def convergence_operation(args: argparse.Namespace) -> dict[str, Any]:
    """Reserve or complete validation work as one locked durable transaction."""
    path = Path(args.checkpoint).resolve()
    with checkpoint_lock(path):
        checkpoint = load_object(path)
        migrate_legacy(checkpoint)
        validate_checkpoint(checkpoint, path)
        if args.command in ("reserve", "assess"):
            snapshot = None
            if args.inputs_json:
                before_capture = copy.deepcopy(checkpoint)
                try:
                    snapshot = capture(
                        load_object(Path(args.inputs_json)),
                        args.revision,
                        checkpoint["task"].get("acceptanceCriteria", []),
                    )
                except ConvergenceError as error:
                    unavailable_decision(checkpoint, args.kind, args.revision, error)
                    persist_invalidations(before_capture, checkpoint, path)
                    raise
            if args.command == "assess":
                result = assess(checkpoint, args.kind, args.revision, snapshot)
            else:
                before = copy.deepcopy(checkpoint)
                try:
                    result = reserve_request(args, checkpoint, snapshot)
                except ConvergenceError:
                    persist_invalidations(before, checkpoint, path)
                    raise
        else:
            try:
                outcome = json.loads(args.result_json)
            except json.JSONDecodeError as error:
                msg = "invalid --result-json"
                raise BookkeepingError(msg) from error
            if not isinstance(outcome, dict):
                msg = "--result-json must contain an object"
                raise BookkeepingError(msg)
            result = finish(checkpoint, args.id, outcome)
        checkpoint["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        validate_checkpoint(checkpoint, path)
        atomic_write(path, checkpoint)
        return {"checkpoint": str(path), **result}


def mutate_checkpoint(
    path: Path,
    apply: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Apply one validated section change under the shared checkpoint lock."""
    path = path.resolve()
    with checkpoint_lock(path):
        checkpoint = load_object(path)
        migrate_legacy(checkpoint)
        validate_checkpoint(checkpoint, path)
        result = apply(checkpoint)
        checkpoint["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        validate_checkpoint(checkpoint, path)
        atomic_write(path, checkpoint)
        return {"checkpoint": str(path), **result}


def default_checkpoint_dir() -> Path:
    """Resolve the documented checkpoint data root."""
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(data_home) / "sai/ship-it/checkpoints"


def relocate_checkpoint(args: argparse.Namespace) -> dict[str, Any]:
    """Move a validated checkpoint to its default durable path without resetting it."""
    source = Path(args.checkpoint).resolve()
    destination = (default_checkpoint_dir() / source.name).resolve()
    with ExitStack() as locks:
        for path in sorted({source, destination}):
            locks.enter_context(checkpoint_lock(path))
        if not source.exists() and destination.exists():
            validate_checkpoint(load_object(destination), destination)
            return {"checkpoint": str(destination), "relocated": False}
        checkpoint = load_object(source)
        validate_checkpoint(checkpoint, source)
        if source == destination:
            return {"checkpoint": str(destination), "relocated": False}
        validate_checkpoint(checkpoint, destination)
        if destination.exists():
            if load_object(destination) != checkpoint:
                message = "durable checkpoint already exists with different state"
                raise BookkeepingError(message)
        else:
            atomic_write(destination, checkpoint)
        if load_object(destination) != checkpoint:
            message = "durable checkpoint verification failed; source preserved"
            raise BookkeepingError(message)
        source.unlink()
    return {"checkpoint": str(destination), "relocated": True}


def create_checkpoint(args: argparse.Namespace) -> dict[str, Any]:
    """Create a checkpoint at phase resolve; never replace an existing one."""
    source = checkpoint_state.parse_object(args.source_json, "--source-json")
    criteria = checkpoint_state.parse_json(args.criteria_json, "--criteria-json")
    task = {
        "sourceUrl": args.source_url,
        "title": args.title,
        "objective": args.objective,
        "acceptanceCriteria": criteria,
    }
    grants = [
        checkpoint_state.parse_object(grant, "--grant-json")
        for grant in args.grant_json
    ]
    policy = resolve_policy(Path(args.repository).resolve(), parse_enabled(args.enable))
    repository = {
        "identity": checkpoint_state.non_empty(args.identity, "--identity"),
        "defaultBranch": args.default_branch,
        "branch": args.branch,
    }
    checkpoint = checkpoint_state.new_checkpoint(
        source=source,
        task=task,
        repository=repository,
        policy=policy,
        grants=grants,
    )
    directory = (
        Path(args.checkpoint_dir) if args.checkpoint_dir else default_checkpoint_dir()
    )
    path = (directory / f"{checkpoint['checkpointId']}.json").resolve()
    validate_checkpoint(checkpoint, path)
    with checkpoint_lock(path):
        if path.exists():
            existing = load_object(path)
            existing_task = existing.get("task")
            if (
                not isinstance(existing_task, dict)
                or existing_task.get("canonicalSource")
                != checkpoint["task"]["canonicalSource"]
            ):
                message = f"checkpoint {path} belongs to another canonical source"
                raise BookkeepingError(message)
            return {
                "checkpoint": str(path),
                "checkpointId": checkpoint["checkpointId"],
                "created": False,
            }
        atomic_write(path, checkpoint)
    return {
        "checkpoint": str(path),
        "checkpointId": checkpoint["checkpointId"],
        "created": True,
    }


def section_operation(args: argparse.Namespace) -> dict[str, Any]:
    """Run one checkpoint section command through the locked transaction."""
    command = args.command
    if command == "attest-review":
        return mutate_checkpoint(
            Path(args.checkpoint),
            lambda checkpoint: checkpoint_state.attest_review(
                checkpoint,
                revision=args.revision,
                summary=args.summary,
                gate=args.gate,
                commands=args.commands,
            ),
        )
    option, apply = JSON_SECTION_COMMANDS[command]
    value = checkpoint_state.parse_object(
        getattr(args, option[2:].replace("-", "_")),
        option,
    )
    return mutate_checkpoint(
        Path(args.checkpoint),
        lambda checkpoint: apply(checkpoint, value),
    )


def persist_invalidations(
    before: dict[str, Any],
    attempted: dict[str, Any],
    path: Path,
) -> None:
    """Keep derived invalidation after refusal, rolling back all attempted spending."""
    decisions = attempted["convergence"].get("validityDecisions", [])
    if decisions == before["convergence"].get("validityDecisions", []):
        return
    before["convergence"]["validityDecisions"] = decisions
    for original, current in zip(
        before["gateVerdicts"],
        attempted["gateVerdicts"],
        strict=False,
    ):
        if (
            original.get("status") == "passed"
            and current.get("status") == "stale"
            and isinstance(current.get("invalidation"), dict)
        ):
            original.update(status="stale", invalidation=current["invalidation"])
    before["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    validate_checkpoint(before, path)
    atomic_write(path, before)


def reserve_request(
    args: argparse.Namespace,
    checkpoint: dict[str, Any],
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve a structured snapshot or a legacy opaque reservation input."""
    inputs = digest(snapshot) if snapshot is not None else args.inputs
    for field, value in (
        ("id", args.id),
        ("revision", args.revision),
        ("inputs", inputs),
    ):
        if not value.strip():
            msg = f"--{field} must be non-empty"
            raise BookkeepingError(msg)
    request = {
        "id": args.id,
        "kind": args.kind,
        "revision": args.revision,
        "inputs": inputs,
        "reason": args.reason,
        "trigger": args.trigger,
        "grant": args.grant,
    }
    if snapshot is not None:
        request["inputSnapshot"] = snapshot
        request["inputManifest"] = load_object(Path(args.inputs_json))
    return reserve(checkpoint, request, datetime.now(UTC))


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    policy = commands.add_parser("policy", help="resolve bookkeeping policy")
    policy.add_argument("--repository", required=True)
    policy.add_argument("--enable", default="")

    update = commands.add_parser(
        "transition",
        help="atomically update checkpoint workflow",
    )
    update.add_argument("--checkpoint", required=True)
    update.add_argument("--phase", required=True)
    update.add_argument("--status", required=True)
    update.add_argument("--blocker")
    update.add_argument("--outcome-json")
    update.add_argument("--next-action", required=True)
    update.add_argument("--revision")
    reconciliation = commands.add_parser(
        "reconcile-delivery",
        help="reconcile durable delivery facts with an authoritative PR read",
    )
    reconciliation.add_argument("--checkpoint", required=True)
    observation = reconciliation.add_mutually_exclusive_group(required=True)
    observation.add_argument("--pull-request-json")
    observation.add_argument("--failure")
    reservation = commands.add_parser(
        "reserve",
        help="spend an idempotent validation allowance before work",
    )
    reservation.add_argument("--checkpoint", required=True)
    reservation.add_argument("--id", required=True)
    reservation.add_argument(
        "--kind",
        choices=("review", "fix", "quality", "test"),
        required=True,
    )
    reservation.add_argument("--revision", required=True)
    inputs = reservation.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--inputs")
    inputs.add_argument("--inputs-json", help="path to relevant input manifest")
    reservation.add_argument("--reason")
    reservation.add_argument(
        "--trigger",
        choices=("security", "data-loss", "destructive-concurrency"),
    )
    reservation.add_argument("--grant")
    validity = commands.add_parser(
        "assess",
        help="persist gate input validity without dispatch",
    )
    validity.add_argument("--checkpoint", required=True)
    validity.add_argument(
        "--kind",
        choices=("review", "test", "quality"),
        required=True,
    )
    validity.add_argument("--revision", required=True)
    validity.add_argument("--inputs-json", required=True)
    completion = commands.add_parser(
        "finish",
        help="record a reserved operation result without spending again",
    )
    completion.add_argument("--checkpoint", required=True)
    completion.add_argument("--id", required=True)
    completion.add_argument("--result-json", required=True)
    add_state_commands(commands)
    return parser


def add_state_commands(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the checkpoint creation and section commands."""
    creation = commands.add_parser(
        "create",
        help="create a checkpoint at phase resolve without overwriting",
    )
    creation.add_argument("--repository", required=True, help="repository root")
    creation.add_argument("--identity", required=True, help="normalized identity")
    creation.add_argument("--source-json", required=True)
    creation.add_argument("--title", required=True)
    creation.add_argument("--objective", required=True)
    creation.add_argument("--criteria-json", required=True)
    creation.add_argument("--source-url")
    creation.add_argument("--default-branch", default="main")
    creation.add_argument("--branch")
    creation.add_argument("--enable", default="")
    creation.add_argument("--grant-json", action="append", default=[])
    creation.add_argument("--checkpoint-dir")
    relocation = commands.add_parser(
        "relocate-checkpoint",
        help="move a checkpoint to the default durable root",
    )
    relocation.add_argument("--checkpoint", required=True)
    for name, option, text in (
        ("handoff", "--handoff-json", "prepare or acknowledge a phase handoff"),
        ("set-risk", "--risk-json", "set the risk selection"),
        ("set-release-policy", "--policy-json", "store the release policy"),
        (
            "set-hosted-review-decision",
            "--decision-json",
            "record the hosted-review decision",
        ),
        ("record-gate", "--verdict-json", "record one gate verdict"),
        ("add-grant", "--grant-json", "record one authorization grant"),
        ("set-findings", "--dispositions-json", "set finding dispositions"),
        (
            "set-orchestration",
            "--orchestration-json",
            "initialize or extend the child graph",
        ),
        (
            "record-orchestration-event",
            "--event-json",
            "record one validated child event",
        ),
        (
            "record-acceptance-recovery",
            "--recovery-json",
            "record one focused acceptance correction",
        ),
    ):
        section = commands.add_parser(name, help=text)
        section.add_argument("--checkpoint", required=True)
        section.add_argument(option, required=True)
    attestation = commands.add_parser(
        "attest-review",
        help="re-attest a review for the current revision",
    )
    attestation.add_argument("--checkpoint", required=True)
    attestation.add_argument("--revision", required=True)
    attestation.add_argument("--summary", required=True)
    attestation.add_argument("--gate", default="adversarial-review")
    attestation.add_argument("--command", dest="commands", action="append", default=[])


def main(argv: list[str] | None = None) -> int:
    """Run the selected bookkeeping command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "policy":
            result = resolve_policy(
                Path(args.repository).resolve(),
                parse_enabled(args.enable),
            )
        elif args.command == "transition":
            result = transition(args)
        elif args.command == "reconcile-delivery":
            result = reconcile_delivery(args)
        elif args.command == "create":
            result = create_checkpoint(args)
        elif args.command == "relocate-checkpoint":
            result = relocate_checkpoint(args)
        elif args.command == "handoff":
            update = checkpoint_state.parse_object(args.handoff_json, "--handoff-json")
            result = mutate_checkpoint(
                Path(args.checkpoint),
                lambda checkpoint: record_handoff(checkpoint, update),
            )
        elif args.command in SECTION_COMMANDS:
            result = section_operation(args)
        else:
            result = convergence_operation(args)
    except (BookkeepingError, ConvergenceError, StateError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
