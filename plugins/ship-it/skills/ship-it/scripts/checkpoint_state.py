#!/usr/bin/env python3
"""Build and mutate ship-it checkpoint sections without hand-edited JSON.

Used by bookkeeping.py under its checkpoint lock: every function here changes an
in-memory checkpoint dict and raises StateError on invalid input. The caller
validates the complete document and writes it atomically.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from convergence import DEFAULTS as CONVERGENCE_DEFAULTS

FULL_COMMIT_ID: Final[re.Pattern[str]] = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")
RISK_LEVELS: Final[tuple[str, ...]] = ("low", "medium", "high")
DIFF_CLASSES: Final[frozenset[str]] = frozenset({"docs", "code"})
GATE_STATUSES: Final[frozenset[str]] = frozenset({"passed", "failed", "blocked"})
DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"open", "fixed", "follow-up", "blocked"},
)
REVIEW_GATES: Final[frozenset[str]] = frozenset(
    {"adversarial-review", "inline-review"},
)
HOSTED_GATES: Final[frozenset[str]] = frozenset({"ci", "hosted-review"})
SOURCE_FIELDS: Final[dict[str, frozenset[str]]] = {
    "github": frozenset({"sourceType", "repository", "issue"}),
    "jira": frozenset({"sourceType", "site", "key"}),
    "description": frozenset(
        {"sourceType", "repository", "objective", "acceptanceCriteria"},
    ),
}
RELEASE_LISTS: Final[tuple[str, ...]] = (
    "sources",
    "requiredReviewers",
    "requiredChecks",
    "activatedFallbacks",
)
RELEASE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schemaVersion",
        "sources",
        "requiredReviewers",
        "requiredChecks",
        "merge",
        "issueClosure",
        "branchCleanup",
        "activatedFallbacks",
        "resolvedAt",
    },
)
RELEASE_MERGE_FIELDS: Final[frozenset[str]] = frozenset(
    {"method", "strategy", "botComment"},
)
RELEASE_METHODS: Final[frozenset[str]] = frozenset({"github", "bot-comment"})
RELEASE_STRATEGIES: Final[frozenset[str]] = frozenset({"merge", "squash", "rebase"})
RELEASE_CLOSURES: Final[frozenset[str]] = frozenset(
    {"pull-request-keyword", "manual-after-merge", "unchanged"},
)
RELEASE_CLEANUPS: Final[frozenset[str]] = frozenset({"delete", "preserve"})
RELEASE_REVIEWER_ENUMS: Final[dict[str, frozenset[str]]] = {
    "kind": frozenset({"human", "automated"}),
    "requirement": frozenset({"review", "approval"}),
    "request": frozenset({"reviewer", "team-reviewer", "automatic"}),
}
LEGACY_FALLBACK: Final[dict[str, str]] = {
    "gate": "hosted-review",
    "fromMechanism": "copilot-review",
    "mechanism": "human-review",
    "reason": "copilot unavailable",
}
HOSTED_DECISIONS: Final[frozenset[str]] = frozenset(
    {"not-required", "serviceable", "fallback", "blocked"},
)
HOSTED_DECISION_FIELDS: Final[frozenset[str]] = frozenset(
    {"status", "reason", "decidedAt"},
)
HOSTED_DECISION_CHANGES: Final[frozenset[str]] = frozenset({"fallback", "blocked"})
SUMMARY_LIMIT: Final[int] = 500


class StateError(ValueError):
    """A deterministic checkpoint-state input error."""


def require(condition: object, message: str) -> None:
    """Raise a state error when an input invariant does not hold."""
    if not condition:
        raise StateError(message)


def now_utc() -> str:
    """Return the current time as an RFC 3339 UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_json(text: str, option: str) -> object:
    """Parse a JSON option."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        message = f"invalid {option}: {error}"
        raise StateError(message) from error


def parse_object(text: str, option: str) -> dict[str, Any]:
    """Parse a JSON object option."""
    value = parse_json(text, option)
    require(isinstance(value, dict), f"{option} must contain an object")
    return value


def one_of(value: object, allowed: frozenset[str]) -> bool:
    """Report membership without hashing arbitrary JSON values."""
    return isinstance(value, str) and value in allowed


def non_empty(value: object, field: str) -> str:
    """Require a non-blank string."""
    require(
        isinstance(value, str) and bool(value.strip()),
        f"{field} must be a non-empty string",
    )
    return str(value)


def utc_timestamp(value: object, field: str) -> str:
    """Require an RFC 3339 timestamp whose offset is UTC."""
    text = non_empty(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        message = f"{field} must be an RFC 3339 UTC timestamp"
        raise StateError(message) from error
    require(
        "T" in text and parsed.utcoffset() == timedelta(0),
        f"{field} must be an RFC 3339 UTC timestamp",
    )
    return text


def commit_id(value: object, field: str) -> str:
    """Require a full hexadecimal commit ID."""
    require(
        isinstance(value, str) and FULL_COMMIT_ID.fullmatch(value) is not None,
        f"{field} must be a full hexadecimal commit ID",
    )
    return str(value)


def canonical_source(source: dict[str, Any]) -> str:
    """Validate a task source and serialize it exactly as the identity contract."""
    source_type = source.get("sourceType")
    require(
        isinstance(source_type, str) and source_type in SOURCE_FIELDS,
        "source sourceType must be github, jira or description",
    )
    expected = SOURCE_FIELDS[str(source_type)]
    require(
        set(source) == expected,
        f"{source_type} source requires exactly: {', '.join(sorted(expected))}",
    )
    if source_type == "github":
        require(
            type(source["issue"]) is int and source["issue"] > 0,
            "github source issue must be a positive integer",
        )
    if source_type == "jira":
        require(
            non_empty(source["site"], "jira site") == source["site"].lower(),
            "jira site must be lowercase",
        )
        require(
            non_empty(source["key"], "jira key") == source["key"].upper(),
            "jira key must be uppercase",
        )
    if source_type in ("github", "description"):
        repository = non_empty(source["repository"], "source repository")
        require(
            repository == repository.lower(),
            "source repository must use the lowercase identity",
        )
    return json.dumps(
        source,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def checkpoint_identity(source: dict[str, Any]) -> tuple[str, str]:
    """Return the canonical source string and its checkpoint ID."""
    canonical = canonical_source(source)
    return canonical, hashlib.sha256(canonical.encode()).hexdigest()


def new_checkpoint(
    *,
    source: dict[str, Any],
    task: dict[str, Any],
    repository: dict[str, Any],
    policy: dict[str, Any],
    grants: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a fresh checkpoint at phase resolve with documented defaults."""
    canonical, identity = checkpoint_identity(source)
    criteria = task["acceptanceCriteria"]
    require(
        isinstance(criteria, list)
        and bool(criteria)
        and all(isinstance(item, str) and item.strip() for item in criteria),
        "acceptance criteria must be a non-empty array of non-empty strings",
    )
    if source["sourceType"] == "description":
        require(
            source["objective"] == task["objective"]
            and source["acceptanceCriteria"] == criteria,
            "description source must repeat the objective and acceptance criteria",
        )
    for field in ("title", "objective"):
        non_empty(task[field], field)
    now = now_utc()
    convergence = {
        key: value.copy() if isinstance(value, list) else value
        for key, value in CONVERGENCE_DEFAULTS.items()
    }
    return {
        "schemaVersion": 1,
        "checkpointId": identity,
        "task": {
            "sourceType": source["sourceType"],
            "canonicalSource": canonical,
            **task,
        },
        "repository": repository,
        "workflow": {
            "phase": "resolve",
            "status": "active",
            "revision": None,
            "blocker": None,
            "unresolvedQuestions": [],
            "nextAction": "Resolve the task source and acceptance criteria",
        },
        "delivery": {
            "pullRequestUrl": None,
            "pullRequestHead": None,
            "pullRequestState": None,
            "mergeCommit": None,
            "mergedAt": None,
            "reconciliation": None,
        },
        "evidence": {
            "revision": None,
            "recordPath": None,
            "status": "missing" if policy["evidence"] else "disabled",
            "updatedAt": None,
        },
        "gateVerdicts": [],
        "claim": None,
        "authorization": {"grants": grants},
        "bookkeeping": policy,
        "risk": {
            "level": None,
            "diffClass": None,
            "policySource": None,
            "matchedRules": [],
            "requiredGates": [],
            "overrideAuthorization": None,
        },
        "releasePolicy": None,
        "hostedReviewDecision": None,
        "convergence": convergence,
        "ciTriage": {"failures": []},
        "orchestration": None,
        "outcome": None,
        "createdAt": now,
        "updatedAt": now,
    }


def set_risk(checkpoint: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    """Replace the risk selection, refusing a lower level without an override."""
    current = checkpoint["risk"]
    level = risk.get("level")
    require(level in RISK_LEVELS, "risk level must be low, medium or high")
    require(
        risk.get("diffClass") in DIFF_CLASSES,
        "risk diffClass must be docs or code",
    )
    non_empty(risk.get("policySource"), "risk policySource")
    require(
        isinstance(risk.get("matchedRules"), list),
        "risk matchedRules must be an array",
    )
    gates = risk.get("requiredGates")
    require(
        isinstance(gates, list)
        and all(isinstance(gate, str) and gate.strip() for gate in gates)
        and len(set(gates)) == len(gates),
        "risk requiredGates must be unique non-empty strings",
    )
    override = risk.get("overrideAuthorization") or current.get(
        "overrideAuthorization",
    )
    require(
        override is None or (isinstance(override, str) and override.strip()),
        "risk overrideAuthorization must be the exact user authorization or null",
    )
    previous = current.get("level")
    lowered = previous in RISK_LEVELS and RISK_LEVELS.index(level) < RISK_LEVELS.index(
        previous,
    )
    require(
        not lowered or override is not None,
        "lowering risk requires explicit overrideAuthorization",
    )
    checkpoint["risk"] = {**current, **risk, "overrideAuthorization": override}
    return {"risk": checkpoint["risk"]["level"], "previous": previous}


def add_grant(checkpoint: dict[str, Any], grant: dict[str, Any]) -> dict[str, Any]:
    """Append one grant; recorded grants, including revoked ones, stay as they are."""
    identity = non_empty(grant.get("id"), "grant id")
    grants = checkpoint["authorization"]["grants"]
    require(
        all(existing.get("id") != identity for existing in grants),
        f"grant ID already recorded: {identity}",
    )
    source = grant.get("source")
    require(isinstance(source, dict), "grant source must be an object")
    non_empty(source.get("message"), "grant source message")
    scope = grant.get("scope")
    require(
        isinstance(scope, list)
        and bool(scope)
        and all(isinstance(item, str) and item.strip() for item in scope),
        "grant scope must be a non-empty array of non-empty strings",
    )
    grants.append(grant)
    return {"grant": identity, "grants": len(grants)}


def material_release_change(old: object, new: dict[str, Any]) -> bool:
    """Report whether the normalized release policy changed, ignoring resolvedAt."""
    if not isinstance(old, dict):
        return False
    return {k: v for k, v in old.items() if k != "resolvedAt"} != {
        k: v for k, v in new.items() if k != "resolvedAt"
    }


def unique_strings(values: object, field: str, *, allow_empty: bool) -> None:
    """Require an array of unique non-empty strings."""
    require(
        isinstance(values, list)
        and all(isinstance(item, str) and item.strip() for item in values)
        and len(set(values)) == len(values)
        and (allow_empty or bool(values)),
        f"releasePolicy {field} must be unique non-empty strings",
    )


def validate_release_merge(merge: object) -> None:
    """Validate the normalized merge mechanism."""
    require(
        isinstance(merge, dict) and set(merge) == RELEASE_MERGE_FIELDS,
        "releasePolicy merge requires exactly method, strategy and botComment",
    )
    require(
        one_of(merge["method"], RELEASE_METHODS),
        "releasePolicy merge method is invalid",
    )
    require(
        one_of(merge["strategy"], RELEASE_STRATEGIES),
        "releasePolicy merge strategy is invalid",
    )
    comment = merge["botComment"]
    require(
        (merge["method"] == "bot-comment")
        == (isinstance(comment, str) and bool(comment.strip())),
        "releasePolicy merge botComment is set only for bot-comment",
    )
    require(
        comment is None or isinstance(comment, str),
        "releasePolicy merge botComment must be a string or null",
    )


def validate_release_reviewers(reviewers: list[Any]) -> None:
    """Validate reviewer entries without fixing their optional extra fields."""
    identities: set[str] = set()
    for reviewer in reviewers:
        require(isinstance(reviewer, dict), "releasePolicy reviewers must be objects")
        identity = non_empty(reviewer.get("id"), "releasePolicy reviewer id")
        require(identity not in identities, "releasePolicy reviewer ids must be unique")
        identities.add(identity)
        non_empty(reviewer.get("actor"), "releasePolicy reviewer actor")
        request = reviewer.get("request")
        require(
            request != "team-reviewer" or str(reviewer["actor"]).startswith("team:"),
            "releasePolicy team-reviewer actor must start with team:",
        )
        require(
            "request_target" not in reviewer
            or (reviewer["request_target"] is None) == (request == "automatic"),
            "releasePolicy request_target is null only for automatic requests",
        )
        for field, allowed in RELEASE_REVIEWER_ENUMS.items():
            require(
                field not in reviewer or one_of(reviewer[field], allowed),
                f"releasePolicy reviewer {field} is invalid",
            )


def validate_release_policy(policy: dict[str, Any]) -> None:
    """Validate the normalized release policy object."""
    require(
        set(policy) == RELEASE_FIELDS,
        "releasePolicy requires exactly: " + ", ".join(sorted(RELEASE_FIELDS)),
    )
    require(
        type(policy["schemaVersion"]) is int and policy["schemaVersion"] == 1,
        "releasePolicy schemaVersion must be 1",
    )
    for field in RELEASE_LISTS:
        require(
            isinstance(policy[field], list),
            f"releasePolicy {field} must be an array",
        )
    unique_strings(policy["sources"], "sources", allow_empty=False)
    unique_strings(policy["requiredChecks"], "requiredChecks", allow_empty=True)
    validate_release_merge(policy["merge"])
    validate_release_reviewers(policy["requiredReviewers"])
    require(
        one_of(policy["issueClosure"], RELEASE_CLOSURES),
        "releasePolicy issueClosure is invalid",
    )
    require(
        one_of(policy["branchCleanup"], RELEASE_CLEANUPS),
        "releasePolicy branchCleanup is invalid",
    )
    utc_timestamp(policy["resolvedAt"], "releasePolicy resolvedAt")
    fallbacks = policy["activatedFallbacks"]
    require(len(fallbacks) <= 1, "releasePolicy allows at most one activated fallback")
    if fallbacks:
        any_reviewer = any(
            reviewer.get("actor") == "any-authorized-reviewer"
            for reviewer in policy["requiredReviewers"]
        )
        require(
            fallbacks[0] == LEGACY_FALLBACK and any_reviewer,
            "releasePolicy activatedFallbacks entry is not the documented v1 fallback",
        )


def set_release_policy(
    checkpoint: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Store the normalized release policy and stale hosted evidence on a change."""
    validate_release_policy(policy)
    changed = material_release_change(checkpoint["releasePolicy"], policy)
    invalidated = 0
    if changed:
        invalidation = {"reason": "release-policy-changed", "at": now_utc()}
        for verdict in checkpoint["gateVerdicts"]:
            if (
                verdict.get("gate") in HOSTED_GATES
                and verdict.get("status") == "passed"
            ):
                verdict.update(status="stale", invalidation=invalidation)
                invalidated += 1
    checkpoint["releasePolicy"] = policy
    return {"materialChange": changed, "invalidatedVerdicts": invalidated}


def set_hosted_review_decision(
    checkpoint: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Record the hosted-review decision; only serviceable may change, once."""
    require(
        set(decision) <= HOSTED_DECISION_FIELDS
        and {"status", "reason"} <= set(decision),
        "hostedReviewDecision takes status and reason, plus optional decidedAt",
    )
    status = decision["status"]
    require(
        one_of(status, HOSTED_DECISIONS),
        "hostedReviewDecision status must be not-required, serviceable, "
        "fallback or blocked",
    )
    reason = non_empty(decision["reason"], "hostedReviewDecision reason")
    require(
        len(reason) <= SUMMARY_LIMIT,
        f"hostedReviewDecision reason exceeds {SUMMARY_LIMIT} characters",
    )
    decided_at = utc_timestamp(
        decision["decidedAt"] if "decidedAt" in decision else now_utc(),
        "hostedReviewDecision decidedAt",
    )
    current = checkpoint.get("hostedReviewDecision")
    previous = current.get("status") if isinstance(current, dict) else None
    require(
        current is None
        or (previous == "serviceable" and status in HOSTED_DECISION_CHANGES),
        f"hostedReviewDecision is already set ({previous}); only serviceable may "
        "change, once, to fallback or blocked",
    )
    checkpoint["hostedReviewDecision"] = {
        "status": status,
        "reason": reason,
        "decidedAt": decided_at,
    }
    return {"hostedReviewDecision": status, "previous": previous}


def put_verdict(checkpoint: dict[str, Any], verdict: dict[str, Any]) -> None:
    """Replace a same gate, revision and provider verdict or append a new one."""
    verdicts = checkpoint["gateVerdicts"]
    for index, existing in enumerate(verdicts):
        if all(
            existing.get(key) == verdict[key]
            for key in ("gate", "revision", "provider")
        ):
            verdicts[index] = verdict
            return
    verdicts.append(verdict)


def require_checkpoint_verdicts(checkpoint: dict[str, Any]) -> None:
    """Gate verdicts live in the evidence record when evidence is enabled."""
    require(
        not checkpoint["bookkeeping"]["evidence"],
        "evidence is enabled: record gate verdicts in the evidence record",
    )


def record_gate(checkpoint: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    """Record one gate verdict for the current workflow revision."""
    require_checkpoint_verdicts(checkpoint)
    gate = non_empty(verdict.get("gate"), "verdict gate")
    require(
        verdict.get("status") in GATE_STATUSES,
        "verdict status must be passed, failed or blocked",
    )
    revision = commit_id(verdict.get("revision"), "verdict revision")
    require(
        revision == checkpoint["workflow"]["revision"],
        "verdict revision must match the current workflow revision",
    )
    non_empty(verdict.get("provider"), "verdict provider")
    summary = non_empty(verdict.get("summary"), "verdict summary")
    require(
        len(summary) <= SUMMARY_LIMIT,
        f"verdict summary exceeds {SUMMARY_LIMIT} characters",
    )
    verdict = {
        **verdict,
        "timestamp": utc_timestamp(
            verdict["timestamp"] if "timestamp" in verdict else now_utc(),
            "verdict timestamp",
        ),
    }
    put_verdict(checkpoint, verdict)
    return {"gate": gate, "status": verdict["status"], "revision": revision}


def split_disposition(update: object) -> tuple[object, object]:
    """Read a disposition string or a follow-up object."""
    if isinstance(update, str):
        return update, None
    if isinstance(update, dict):
        return update.get("disposition"), update.get("followUpIssue")
    return None, None


def stale_review_attestations(checkpoint: dict[str, Any]) -> None:
    """Stale helper-made re-attestations while a finding is unresolved."""
    if all(
        finding["disposition"] in ("fixed", "follow-up")
        for finding in checkpoint["convergence"]["findings"]
    ):
        return
    invalidation = {"reason": "finding-reopened", "at": now_utc()}
    for verdict in checkpoint["gateVerdicts"]:
        if (
            verdict.get("provider") == "ship-it-convergence"
            and verdict.get("gate") in REVIEW_GATES
            and verdict.get("status") == "passed"
        ):
            verdict.update(status="stale", invalidation=invalidation)


def set_dispositions(
    checkpoint: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Apply finding dispositions and retain follow-up issue URLs."""
    state = checkpoint["convergence"]
    findings = {finding["id"]: finding for finding in state["findings"]}
    require(bool(updates), "dispositions must name at least one finding")
    for identity, update in updates.items():
        require(identity in findings, f"unknown finding ID: {identity}")
        disposition, url = split_disposition(update)
        require(
            one_of(disposition, DISPOSITIONS),
            f"finding {identity} has invalid disposition",
        )
        require(
            (disposition == "follow-up") == (url is not None),
            f"finding {identity}: only a follow-up disposition takes "
            "followUpIssue, and it requires one",
        )
        require(
            disposition != "blocked" or checkpoint["workflow"]["status"] == "blocked",
            "a blocked finding requires a blocked workflow",
        )
        if url is not None:
            require(
                isinstance(url, str) and url.startswith(("https://", "http://")),
                f"finding {identity} followUpIssue must be a URL",
            )
            if url not in state["followUpIssues"]:
                state["followUpIssues"].append(url)
        findings[identity]["disposition"] = disposition
    stale_review_attestations(checkpoint)
    return {"findings": {k: v["disposition"] for k, v in findings.items()}}


def attest_review(
    checkpoint: dict[str, Any],
    *,
    revision: str,
    summary: str,
    gate: str,
    commands: list[str],
) -> dict[str, Any]:
    """Re-attest a fixed or follow-up-resolved review for the current revision."""
    require_checkpoint_verdicts(checkpoint)
    require(gate in REVIEW_GATES, "gate must be adversarial-review or inline-review")
    commit_id(revision, "attested revision")
    require(
        revision == checkpoint["workflow"]["revision"],
        "attested revision must match the current workflow revision",
    )
    state = checkpoint["convergence"]
    require(
        state["reviewCycles"] > 0 and state["reviewedRevision"] is not None,
        "re-attestation requires a completed review cycle",
    )
    review = next(
        (
            receipt
            for receipt in state["reservations"]
            if receipt["kind"] == "review"
            and receipt["status"] == "completed"
            and receipt["revision"] == state["reviewedRevision"]
        ),
        None,
    )
    require(
        review is not None
        and review["result"]["verdict"] == "failed"
        and bool(state["findings"]),
        "re-attestation requires a failed review receipt with recorded findings; "
        "carry a clean review to a new head with assess and reserve",
    )
    require(
        all(
            finding["disposition"] in ("fixed", "follow-up")
            for finding in state["findings"]
        ),
        "re-attestation requires every finding fixed or deferred to a follow-up",
    )
    text = non_empty(summary, "summary")
    require(len(text) <= SUMMARY_LIMIT, f"summary exceeds {SUMMARY_LIMIT} characters")
    put_verdict(
        checkpoint,
        {
            "gate": gate,
            "status": "passed",
            "revision": revision,
            "provider": "ship-it-convergence",
            "timestamp": now_utc(),
            "summary": text,
            "reviewedRevision": state["reviewedRevision"],
            "findings": [
                {"id": finding["id"], "disposition": finding["disposition"]}
                for finding in state["findings"]
            ],
            "followUpIssues": list(state["followUpIssues"]),
            "commands": commands,
        },
    )
    return {
        "gate": gate,
        "revision": revision,
        "reviewedRevision": state["reviewedRevision"],
    }
