#!/usr/bin/env python3
"""Validate relational invariants in a ship-it CI triage record.

Usage: ci_triage.py validate CI-TRIAGE.json
Output: one JSON object on stdout.
Exit codes: 0 valid, 1 invariant failures, 2 unreadable or malformed input.

The state functions at the end change an in-memory checkpoint dict for
bookkeeping.py, which holds the checkpoint lock, and raise TriageError.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

MAX_LINE_BYTES: Final[int] = 500
MAX_EVIDENCE_CHARS: Final[int] = 512
MAX_SUPPORTING_EVIDENCE: Final[int] = 10
MAX_LOG_SECTIONS: Final[int] = 3
MAX_SECTION_LINES: Final[int] = 40
MAX_LINE_CHARS: Final[int] = 125
MAX_LABEL_CHARS: Final[int] = 200
MAX_ACCEPTANCE_EVIDENCE: Final[int] = 20
UTC_TIMESTAMP: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)",
)
REVISION: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{40,64}")
FAILURE_ID: Final[re.Pattern[str]] = re.compile(r"cif_[0-9a-f]{64}")
GROUP_ID: Final[re.Pattern[str]] = re.compile(r"cig_[0-9a-f]{64}")
RECURRENCE_KEY: Final[re.Pattern[str]] = re.compile(r"cir_[0-9a-f]{64}")
KEY_FIELDS: Final[frozenset[str]] = frozenset(
    {"revision", "workflow", "job", "attempt"},
)
SECTION_FIELDS: Final[frozenset[str]] = frozenset({"label", "lines"})
AUTHORIZATION_FIELDS: Final[frozenset[str]] = frozenset(
    {"source", "reference", "maxAttempts", "authorizedAt"},
)
RESOLUTION_FIELDS: Final[frozenset[str]] = frozenset(
    {"kind", "evidence", "resolvedAt"},
)
REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "schemaVersion",
    "failureId",
    "key",
    "recurrenceKey",
    "recurrenceOf",
    "recurrenceCount",
    "rerunGroupId",
    "rerunsUsed",
    "rerunRequest",
    "classification",
    "status",
    "supportingEvidence",
    "logSections",
    "failedAcceptanceEvidence",
    "rerunAuthorization",
    "resolution",
    "nextAction",
    "firstObservedAt",
    "lastObservedAt",
)
CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {"code", "flaky", "infrastructure", "unknown"},
)
STATUSES: Final[frozenset[str]] = frozenset({"open", "resolved"})
RESOLUTION_KINDS: Final[frozenset[str]] = frozenset(
    {"rerun-passed", "provider-recovered", "superseded-by-revision"},
)
AUTHORIZATION_SOURCES: Final[frozenset[str]] = frozenset(
    {"repository-policy", "explicit-approval"},
)
SETTLEMENTS: Final[frozenset[str]] = frozenset({"accepted", "not-accepted"})


class TriageError(ValueError):
    """A deterministic CI triage state input error."""


def digest(prefix: str, value: dict[str, Any]) -> str:
    """Return a prefixed digest of canonical compact JSON."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}{hashlib.sha256(encoded).hexdigest()}"


def validate_identity(record: dict[str, Any], key: dict[str, Any]) -> list[str]:
    """Validate hashes against their canonical identity keys."""
    errors: list[str] = []
    required_key = ("revision", "workflow", "job", "attempt")
    if any(name not in key for name in required_key):
        errors.append("key must contain revision, workflow, job and attempt")
    else:
        invalid_text = [
            name
            for name in ("revision", "workflow", "job")
            if isinstance(key[name], str) and not is_scalar_text(key[name])
        ]
        if invalid_text:
            errors.append(
                "identity fields contain non-scalar Unicode: "
                + ", ".join(invalid_text),
            )
            return errors
        expected_failure = digest(
            "cif_",
            {name: key[name] for name in sorted(required_key)},
        )
        if record.get("failureId") != expected_failure:
            errors.append("failureId does not match the canonical key")

        group_key = {
            name: key[name] for name in sorted(("revision", "workflow", "job"))
        }
        if record.get("rerunGroupId") != digest("cig_", group_key):
            errors.append("rerunGroupId does not match revision, workflow and job")
    return errors


def is_scalar_text(value: str) -> bool:
    """Return whether text can be encoded as strict UTF-8."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def validate_recurrence(record: dict[str, Any]) -> list[str]:
    """Validate recurrence relationships."""
    errors: list[str] = []
    failure_id = record.get("failureId")
    recurrence_of = record.get("recurrenceOf")
    recurrence_count = record.get("recurrenceCount")
    recurrence_key = record.get("recurrenceKey")
    if recurrence_of is None:
        if recurrence_count != 0:
            errors.append("a first observation must have recurrenceCount 0")
    else:
        if not isinstance(recurrence_of, str):
            errors.append("recurrenceOf must be a string or null")
            return errors
        if recurrence_of == failure_id:
            errors.append("recurrenceOf cannot refer to the same failureId")
        if recurrence_key is None:
            errors.append("a recurrence requires recurrenceKey")
        if not isinstance(recurrence_count, int) or recurrence_count < 1:
            errors.append("a recurrence requires a positive recurrenceCount")
    return errors


def validate_reruns(record: dict[str, Any]) -> list[str]:
    """Validate consumed reruns against their authorization."""
    errors: list[str] = []
    reruns_used = record.get("rerunsUsed")
    authorization = record.get("rerunAuthorization")
    if not isinstance(reruns_used, int) or isinstance(reruns_used, bool):
        errors.append("rerunsUsed must be an integer")
    elif reruns_used < 0:
        errors.append("rerunsUsed cannot be negative")
    elif authorization is None:
        if reruns_used != 0:
            errors.append("rerunsUsed requires rerunAuthorization")
    elif not isinstance(authorization, dict):
        errors.append("rerunAuthorization must be an object or null")
    else:
        limit = authorization.get("maxAttempts")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            errors.append("rerunAuthorization maxAttempts must be positive")
        elif reruns_used > limit:
            errors.append("rerunsUsed exceeds the authorized maximum")
    errors.extend(
        validate_rerun_request(
            reruns_used,
            authorization,
            record.get("rerunRequest"),
        ),
    )
    return errors


def validate_rerun_request(
    reruns_used: object,
    authorization: object,
    request: object,
) -> list[str]:
    """Validate one durable provider-request intent."""
    if request is None:
        return []
    errors: list[str] = []
    if authorization is None:
        errors.append("rerunRequest requires rerunAuthorization")
    if not isinstance(request, dict):
        return [*errors, "rerunRequest must be an object or null"]
    requested_attempt = request.get("requestedAttempt")
    if (
        not isinstance(requested_attempt, int)
        or isinstance(requested_attempt, bool)
        or requested_attempt < 1
    ):
        errors.append("rerunRequest requestedAttempt must be a positive integer")
    recorded_at = request.get("recordedAt")
    if not isinstance(recorded_at, str) or not is_scalar_text(recorded_at):
        errors.append("rerunRequest recordedAt must be scalar text")
    if (
        isinstance(reruns_used, int)
        and not isinstance(reruns_used, bool)
        and (requested_attempt != reruns_used + 1)
    ):
        errors.append("rerunRequest must reserve rerunsUsed plus one")
    if isinstance(authorization, dict):
        limit = authorization.get("maxAttempts")
        if (
            isinstance(limit, int)
            and not isinstance(limit, bool)
            and isinstance(requested_attempt, int)
            and not isinstance(requested_attempt, bool)
            and requested_attempt > limit
        ):
            errors.append("rerunRequest exceeds the authorized maximum")
    return errors


def validate_state(record: dict[str, Any]) -> list[str]:
    """Validate classification and resolution state."""
    errors: list[str] = []
    acceptance = record.get("failedAcceptanceEvidence")
    if record.get("classification") == "code" and not acceptance:
        errors.append("code classification requires failed acceptance evidence")

    status = record.get("status")
    resolution = record.get("resolution")
    if status == "resolved" and not isinstance(resolution, dict):
        errors.append("resolved status requires a resolution")
    if status == "open" and resolution is not None:
        errors.append("open status cannot have a resolution")
    return errors


def validate_logs(record: dict[str, Any]) -> list[str]:
    """Validate encoded log-line bounds."""
    errors: list[str] = []
    sections = record.get("logSections")
    if isinstance(sections, list):
        for section_index, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            lines = section.get("lines")
            if not isinstance(lines, list):
                continue
            for line_index, line in enumerate(lines):
                if not isinstance(line, str):
                    continue
                try:
                    encoded = line.encode("utf-8")
                except UnicodeEncodeError:
                    errors.append(
                        f"logSections[{section_index}].lines[{line_index}] "
                        "contains a non-scalar Unicode surrogate",
                    )
                    continue
                if len(encoded) > MAX_LINE_BYTES:
                    errors.append(
                        f"logSections[{section_index}].lines[{line_index}] "
                        f"exceeds {MAX_LINE_BYTES} UTF-8 bytes",
                    )
    return errors


def validate_record(record: object) -> list[str]:
    """Return one record's deterministic invariant failures."""
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    key = record.get("key")
    if not isinstance(key, dict):
        return ["key must be an object"]

    return [
        *validate_identity(record, key),
        *validate_recurrence(record),
        *validate_reruns(record),
        *validate_state(record),
        *validate_logs(record),
    ]


def collect_failures(
    failures: list[object],
) -> tuple[list[str], dict[str, list[dict[str, Any]]], set[str]]:
    """Validate records while collecting their cross-record identities."""
    errors: list[str] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    failure_ids: set[str] = set()
    for index, failure in enumerate(failures):
        errors.extend(
            f"failures[{index}]: {error}" for error in validate_record(failure)
        )
        if not isinstance(failure, dict):
            continue
        failure_id = failure.get("failureId")
        if isinstance(failure_id, str):
            if failure_id in failure_ids:
                errors.append(f"failures[{index}]: duplicate failureId")
            failure_ids.add(failure_id)
        group_id = failure.get("rerunGroupId")
        if isinstance(group_id, str):
            groups.setdefault(group_id, []).append(failure)
    return errors, groups, failure_ids


def validate_groups(groups: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Validate state shared by every record in a rerun group."""
    errors: list[str] = []
    for group_id, records in sorted(groups.items()):
        usage = {
            json.dumps(record.get("rerunsUsed"), sort_keys=True) for record in records
        }
        if len(usage) > 1:
            errors.append(f"rerun group {group_id} has inconsistent rerunsUsed")
        requests = {
            json.dumps(record.get("rerunRequest"), sort_keys=True) for record in records
        }
        if len(requests) > 1:
            errors.append(f"rerun group {group_id} has inconsistent rerunRequest")
    return errors


def validate_recurrence_targets(
    failures: list[object],
    failure_ids: set[str],
) -> list[str]:
    """Validate recurrence references against the complete failure set."""
    records = {
        failure.get("failureId"): failure
        for failure in failures
        if isinstance(failure, dict) and isinstance(failure.get("failureId"), str)
    }
    errors: list[str] = []
    for index, failure in enumerate(failures):
        errors.extend(
            validate_recurrence_target(index, failure, records, failure_ids),
        )
    return errors


def validate_recurrence_target(
    index: int,
    failure: object,
    records: dict[object, dict[str, Any]],
    failure_ids: set[str],
) -> list[str]:
    """Validate one recurrence link against its target record."""
    if not isinstance(failure, dict) or failure.get("recurrenceOf") is None:
        return []
    recurrence_of = failure["recurrenceOf"]
    if not isinstance(recurrence_of, str):
        return [f"failures[{index}]: recurrenceOf must be a string or null"]
    if recurrence_of not in failure_ids:
        return [f"failures[{index}]: recurrenceOf is not in this checkpoint"]
    target = records[recurrence_of]
    key = failure.get("key")
    target_key = target.get("key")
    if not isinstance(key, dict) or not isinstance(target_key, dict):
        return []

    errors: list[str] = []
    identity = ("revision", "workflow", "job")
    if any(key.get(name) != target_key.get(name) for name in identity):
        errors.append(f"failures[{index}]: recurrence target identity differs")
    if failure.get("recurrenceKey") != target.get("recurrenceKey"):
        errors.append(f"failures[{index}]: recurrence target key differs")
    expected_target = most_recent_recurrence_target(failure, records)
    if expected_target is not None and recurrence_of != expected_target:
        errors.append(f"failures[{index}]: recurrence target is not most recent")
    attempt = key.get("attempt")
    target_attempt = target_key.get("attempt")
    if (
        isinstance(attempt, int)
        and isinstance(target_attempt, int)
        and target_attempt >= attempt
    ):
        errors.append(f"failures[{index}]: recurrence target is not earlier")
    target_count = target.get("recurrenceCount")
    if isinstance(target_count, int) and (
        failure.get("recurrenceCount") != target_count + 1
    ):
        errors.append(f"failures[{index}]: recurrenceCount is not sequential")
    return errors


def most_recent_recurrence_target(
    failure: dict[str, Any],
    records: dict[object, dict[str, Any]],
) -> object | None:
    """Return the latest earlier record with the same recurrence identity."""
    key = failure.get("key")
    if not isinstance(key, dict) or not isinstance(key.get("attempt"), int):
        return None
    identity = ("revision", "workflow", "job")
    candidates: list[tuple[int, object]] = []
    for failure_id, candidate in records.items():
        candidate_key = candidate.get("key")
        if not isinstance(candidate_key, dict):
            continue
        candidate_attempt = candidate_key.get("attempt")
        if (
            not isinstance(candidate_attempt, int)
            or candidate_attempt >= key["attempt"]
        ):
            continue
        if any(candidate_key.get(name) != key.get(name) for name in identity):
            continue
        if candidate.get("recurrenceKey") != failure.get("recurrenceKey"):
            continue
        candidates.append((candidate_attempt, failure_id))
    return max(candidates)[1] if candidates else None


def validate(document: object) -> list[str]:
    """Validate a complete checkpoint ciTriage object."""
    if not isinstance(document, dict) or not isinstance(document.get("failures"), list):
        return ["document must be an object with a failures array"]

    failures = document["failures"]
    errors, groups, failure_ids = collect_failures(failures)
    return [
        *errors,
        *validate_groups(groups),
        *validate_recurrence_targets(failures, failure_ids),
    ]


def is_text(value: object, limit: int) -> bool:
    """Return whether a value is non-empty encodable text within a bound."""
    return isinstance(value, str) and 0 < len(value) <= limit and is_scalar_text(value)


def is_member(value: object, allowed: frozenset[str]) -> bool:
    """Report membership without hashing arbitrary JSON values."""
    return isinstance(value, str) and value in allowed


def is_utc_timestamp(value: object) -> bool:
    """Return whether a value is an RFC 3339 timestamp in UTC."""
    if not isinstance(value, str) or UTC_TIMESTAMP.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0)


def now_utc() -> str:
    """Return the current time as an RFC 3339 UTC timestamp."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def has_keys(value: object, names: frozenset[str]) -> bool:
    """Return whether a value is an object with exactly the named keys."""
    return isinstance(value, dict) and set(value) == names


def matches(value: object, pattern: re.Pattern[str]) -> bool:
    """Return whether a value is a string that fully matches a pattern."""
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def key_errors(record: dict[str, Any]) -> list[str]:
    """Check the identity key against its schema bounds."""
    key = record["key"]
    if not (
        has_keys(key, KEY_FIELDS)
        and matches(key["revision"], REVISION)
        and is_text(key["workflow"], MAX_LABEL_CHARS)
        and is_text(key["job"], MAX_LABEL_CHARS)
        and is_attempt(key["attempt"])
    ):
        message = (
            "key needs exactly revision (40 to 64 hex), workflow and job "
            f"(1 to {MAX_LABEL_CHARS} characters) and a positive integer attempt"
        )
        return [message]
    return []


def link_errors(record: dict[str, Any]) -> list[str]:
    """Check identifiers, recurrence fields and evidence arrays."""
    errors: list[str] = []
    for name, pattern, nullable in (
        ("failureId", FAILURE_ID, False),
        ("rerunGroupId", GROUP_ID, False),
        ("recurrenceKey", RECURRENCE_KEY, True),
        ("recurrenceOf", FAILURE_ID, True),
    ):
        if not (matches(record[name], pattern) or (nullable and record[name] is None)):
            errors.append(f"{name} must match {pattern.pattern}")
    count = record["recurrenceCount"]
    if type(count) is not int or count < 0:
        errors.append("recurrenceCount must be a non-negative integer")
    for name, minimum, maximum in (
        ("supportingEvidence", 1, MAX_SUPPORTING_EVIDENCE),
        ("failedAcceptanceEvidence", 0, MAX_ACCEPTANCE_EVIDENCE),
    ):
        items = record[name]
        if not (
            isinstance(items, list)
            and minimum <= len(items) <= maximum
            and all(is_text(item, MAX_EVIDENCE_CHARS) for item in items)
        ):
            errors.append(
                f"{name} needs {minimum} to {maximum} statements of "
                f"1 to {MAX_EVIDENCE_CHARS} characters",
            )
    return errors


def section_errors(record: dict[str, Any]) -> list[str]:
    """Check the log excerpt bounds of the schema."""
    sections = record["logSections"]
    if not isinstance(sections, list) or len(sections) > MAX_LOG_SECTIONS:
        return [f"logSections must be an array of at most {MAX_LOG_SECTIONS}"]
    errors: list[str] = []
    for index, section in enumerate(sections):
        if not (
            has_keys(section, SECTION_FIELDS)
            and is_text(section["label"], MAX_LABEL_CHARS)
            and isinstance(section["lines"], list)
            and len(section["lines"]) <= MAX_SECTION_LINES
            and all(
                isinstance(line, str)
                and len(line) <= MAX_LINE_CHARS
                and is_scalar_text(line)
                for line in section["lines"]
            )
        ):
            errors.append(
                f"logSections[{index}] needs exactly a label and at most "
                f"{MAX_SECTION_LINES} lines of {MAX_LINE_CHARS} characters",
            )
    return errors


def authorization_errors(record: dict[str, Any]) -> list[str]:
    """Check the shape of the rerun authorization and the resolution."""
    errors: list[str] = []
    authorization = record["rerunAuthorization"]
    if authorization is not None and not (
        has_keys(authorization, AUTHORIZATION_FIELDS)
        and is_member(authorization["source"], AUTHORIZATION_SOURCES)
        and is_text(authorization["reference"], MAX_EVIDENCE_CHARS)
        and is_attempt(authorization["maxAttempts"])
        and is_utc_timestamp(authorization["authorizedAt"])
    ):
        errors.append(
            "rerunAuthorization needs exactly source, reference, "
            "a positive integer maxAttempts and authorizedAt",
        )
    resolution = record["resolution"]
    if resolution is not None and not (
        has_keys(resolution, RESOLUTION_FIELDS)
        and is_member(resolution["kind"], RESOLUTION_KINDS)
        and is_text(resolution["evidence"], MAX_EVIDENCE_CHARS)
        and is_utc_timestamp(resolution["resolvedAt"])
    ):
        errors.append("resolution needs exactly kind, evidence and resolvedAt")
    return errors


def shape_errors(record: dict[str, Any]) -> list[str]:
    """Check an incoming record against the schema constraints in the contract."""
    missing = [name for name in REQUIRED_FIELDS if name not in record]
    if missing:
        return [f"record missing required fields: {', '.join(missing)}"]
    errors: list[str] = []
    if type(record["schemaVersion"]) is not int or record["schemaVersion"] != 1:
        errors.append("schemaVersion must be 1")
    for name, allowed in (("classification", CLASSIFICATIONS), ("status", STATUSES)):
        if not is_member(record[name], allowed):
            errors.append(f"{name} must be one of: {', '.join(sorted(allowed))}")
    if not is_text(record["nextAction"], MAX_EVIDENCE_CHARS):
        errors.append("nextAction must be bounded non-empty text")
    errors.extend(
        f"{name} must be an RFC 3339 UTC timestamp"
        for name in ("firstObservedAt", "lastObservedAt")
        if not is_utc_timestamp(record[name])
    )
    return [
        *errors,
        *key_errors(record),
        *link_errors(record),
        *section_errors(record),
        *authorization_errors(record),
    ]


def is_attempt(value: object) -> bool:
    """Return whether a value is a positive integer attempt number."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def attempt_of(failure: dict[str, Any]) -> int:
    """Return the provider run attempt of a validated record."""
    return int(failure["key"]["attempt"])


def stored_failures(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the checkpoint's validated failure list, creating it when absent."""
    state = checkpoint.setdefault("ciTriage", {})
    if not isinstance(state, dict):
        message = "checkpoint ciTriage must be an object"
        raise TriageError(message)
    failures = state.setdefault("failures", [])
    errors = validate({"failures": failures})
    if errors:
        message = "stored ciTriage is invalid: " + "; ".join(errors)
        raise TriageError(message)
    return failures


def commit_failures(failures: list[dict[str, Any]], candidate: list[Any]) -> None:
    """Replace the failure list only when the complete next set validates."""
    errors = validate({"failures": candidate})
    if errors:
        raise TriageError("; ".join(errors))
    failures[:] = candidate


def group_records(
    failures: list[dict[str, Any]],
    group_id: object,
) -> list[dict[str, Any]]:
    """Return every record of one rerun group."""
    group = [failure for failure in failures if failure["rerunGroupId"] == group_id]
    if not group:
        message = f"no failure is recorded for rerunGroupId {group_id}"
        raise TriageError(message)
    return group


def inherited_rerun_state(
    record: dict[str, Any],
    group: list[dict[str, Any]],
) -> dict[str, Any]:
    """Give a record the durable rerun state of its group."""
    if not group:
        if record["rerunsUsed"] != 0 or record["rerunRequest"] is not None:
            message = (
                "a new rerun group starts with rerunsUsed 0 and rerunRequest null; "
                "request-ci-rerun and settle-ci-rerun change them"
            )
            raise TriageError(message)
        return {}
    inherited = {
        "rerunsUsed": group[0]["rerunsUsed"],
        "rerunRequest": group[0]["rerunRequest"],
    }
    latest = max(group, key=attempt_of)
    if record["rerunAuthorization"] is None:
        inherited["rerunAuthorization"] = latest["rerunAuthorization"]
    return inherited


def record_failure(
    checkpoint: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    """Append a failure or replace the record with the same failureId.

    The stored rerun group owns rerunsUsed and rerunRequest, so a supplied value
    never resets the limit; the rerun commands are the only writers.
    """
    errors = shape_errors(record)
    if errors:
        raise TriageError("; ".join(errors))
    failures = stored_failures(checkpoint)
    group = [f for f in failures if f["rerunGroupId"] == record["rerunGroupId"]]
    same_id = [f for f in failures if f["failureId"] == record["failureId"]]
    existing = same_id[0] if same_id else None
    record = {**record, **inherited_rerun_state(record, group)}
    if existing is None:
        candidate = [*failures, record]
    else:
        if existing["status"] == "resolved" and record["status"] == "open":
            message = "a resolved failure stays resolved; record a new attempt instead"
            raise TriageError(message)
        record["firstObservedAt"] = existing.get(
            "firstObservedAt",
            record["firstObservedAt"],
        )
        candidate = [record if f is existing else f for f in failures]
    commit_failures(failures, candidate)
    return {
        "failureId": record["failureId"],
        "recorded": "created" if existing is None else "updated",
        "failures": len(failures),
    }


def covering_authorization(
    failure: dict[str, Any],
    latest: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    """Keep a record's own authorization unless it cannot cover the request."""
    own = failure["rerunAuthorization"]
    if isinstance(own, dict) and own["maxAttempts"] >= attempt:
        return own
    return latest


def request_rerun(
    checkpoint: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    """Reserve the next rerun attempt of a group before the provider is called."""
    if not {"rerunGroupId"} <= set(request) <= {"rerunGroupId", "recordedAt"}:
        message = "request-ci-rerun takes rerunGroupId and optional recordedAt"
        raise TriageError(message)
    recorded_at = request.get("recordedAt", now_utc())
    if not is_utc_timestamp(recorded_at):
        message = "recordedAt must be an RFC 3339 UTC timestamp"
        raise TriageError(message)
    failures = stored_failures(checkpoint)
    group = group_records(failures, request["rerunGroupId"])
    latest = max(group, key=attempt_of)
    if any(failure["rerunRequest"] is not None for failure in group):
        message = "a rerun request is already pending; settle it with settle-ci-rerun"
        raise TriageError(message)
    if latest["status"] != "open":
        message = "the latest failure of this rerun group is resolved"
        raise TriageError(message)
    authorization = latest["rerunAuthorization"]
    if authorization is None:
        message = "a rerun needs rerunAuthorization on the latest failure"
        raise TriageError(message)
    used = group[0]["rerunsUsed"]
    if used + 1 > authorization["maxAttempts"]:
        message = (
            f"rerun budget exhausted: {used} of {authorization['maxAttempts']} used"
        )
        raise TriageError(message)
    pending = {"requestedAttempt": used + 1, "recordedAt": recorded_at}
    candidate = [
        {
            **failure,
            "rerunAuthorization": covering_authorization(
                failure,
                authorization,
                used + 1,
            ),
            "rerunRequest": dict(pending),
        }
        if failure in group
        else failure
        for failure in failures
    ]
    commit_failures(failures, candidate)
    return {"rerunGroupId": request["rerunGroupId"], **pending}


def settle_rerun(
    checkpoint: dict[str, Any],
    settlement: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a pending rerun request after the provider answered."""
    if set(settlement) != {"rerunGroupId", "outcome"} or not is_member(
        settlement["outcome"],
        SETTLEMENTS,
    ):
        message = "settle-ci-rerun takes rerunGroupId and outcome accepted|not-accepted"
        raise TriageError(message)
    failures = stored_failures(checkpoint)
    group = group_records(failures, settlement["rerunGroupId"])
    pending = group[0]["rerunRequest"]
    if pending is None:
        message = "no rerun request is pending for this group"
        raise TriageError(message)
    accepted = settlement["outcome"] == "accepted"
    used = pending["requestedAttempt"] if accepted else group[0]["rerunsUsed"]
    candidate = [
        {**failure, "rerunsUsed": used, "rerunRequest": None}
        if failure in group
        else failure
        for failure in failures
    ]
    commit_failures(failures, candidate)
    return {
        "rerunGroupId": settlement["rerunGroupId"],
        "outcome": settlement["outcome"],
        "rerunsUsed": used,
    }


def command_validate(path: Path) -> int:
    """Validate one record and emit a machine-readable result."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(
            json.dumps({"valid": False, "errors": [f"cannot read record: {error}"]}),
            file=sys.stderr,
        )
        return 2

    errors = validate(record)
    print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
    return 1 if errors else 0


def parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("record", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    """Run the selected command."""
    args = parser().parse_args(argv)
    if args.command == "validate":
        return command_validate(args.record)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
