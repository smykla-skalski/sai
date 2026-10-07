#!/usr/bin/env python3
"""Validate relational invariants in a ship-it CI triage record.

Usage: ci_triage.py validate CI-TRIAGE.json
Output: one JSON object on stdout.
Exit codes: 0 valid, 1 invariant failures, 2 unreadable or malformed input.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Final

MAX_LINE_BYTES: Final[int] = 500


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
            name: key[name]
            for name in sorted(("revision", "workflow", "job"))
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
    if isinstance(reruns_used, int) and not isinstance(reruns_used, bool) and (
        request.get("requestedAttempt") != reruns_used + 1
    ):
        errors.append("rerunRequest must reserve rerunsUsed plus one")
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
        usage = {record.get("rerunsUsed") for record in records}
        if len(usage) > 1:
            errors.append(f"rerun group {group_id} has inconsistent rerunsUsed")
        requests = {
            json.dumps(record.get("rerunRequest"), sort_keys=True)
            for record in records
        }
        if len(requests) > 1:
            errors.append(f"rerun group {group_id} has inconsistent rerunRequest")
    return errors


def validate_recurrence_targets(
    failures: list[object], failure_ids: set[str],
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
