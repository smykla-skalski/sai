#!/usr/bin/env python3
# Copyright 2026 Marcin Skalski
"""Classify submitted Copilot quota refusals without contacting GitHub.

Usage: copilot_review.py REVIEWS.json [--previous STATE.json]
Output: one JSON state record. Exit codes: 0 classified; 2 invalid input.
The state is PR-scoped and must be retained across heads and waiter resumes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Final

COPILOT_ACTORS: Final = frozenset({"copilot-pull-request-reviewer", "copilot"})
QUOTA: Final = re.compile(
    r"\bquota\b|\b(?:premium|review|request|usage)\s+"
    r"(?:requests?\s+)?(?:limit|allowance)\b"
    r"|\blimit\b.{0,60}\b(?:copilot|code reviews?)\b",
    re.IGNORECASE,
)
REFUSAL: Final = re.compile(
    r"(?:^|[.!?]\s+)(?:copilot\s+|i(?:\s+am|\s+was|'m)?\s+)?"
    r"(?:unable|cannot|can't|could not|couldn't)\s+"
    r"(?:to\s+)?review\b"
    r"|\byou(?:'ve|\s+have)?\s+(?:exceeded|exhausted|reached|used up)\b"
    r".{0,100}\b(?:quota|limit|allowance|requests?)\b",
    re.IGNORECASE | re.DOTALL,
)


def classify_reviews(
    reviews: list[dict[str, Any]],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Separate quota refusals from real reviews, retaining prior refusal evidence.

    Accept REST or GraphQL reviews. ``reviews`` in the result contains all genuine
    submitted reviews, including Copilot reviews preceding or following a refusal.
    Never use ``unserviceable`` to discard those reviews or their review threads.
    """
    validate_inputs(reviews, previous)
    evidence = list((previous or {}).get("refusalEvidence", []))
    genuine = []
    for review in reviews:
        if str(review.get("state", "")).upper() in {"PENDING", "DISMISSED", ""}:
            continue
        author = review.get("user") or review.get("author") or {}
        login = str(author.get("login", "")).lower().removesuffix("[bot]")
        body = str(review.get("body") or "")
        if login in COPILOT_ACTORS and QUOTA.search(body) and REFUSAL.search(body):
            refusal = {
                "id": review.get("id"),
                "url": review.get("html_url") or review.get("url"),
                "actor": login,
                "reason": "copilot-quota-refusal",
                "body": body,
            }
            if refusal not in evidence:
                evidence.append(refusal)
        else:
            genuine.append(review)
    unavailable = bool(evidence) or (previous or {}).get("unserviceable") is True
    return {
        "unserviceable": unavailable,
        "refusalEvidence": evidence,
        "reviews": genuine,
        "requestAllowed": not unavailable,
    }


def validate_inputs(reviews: object, previous: object) -> None:
    """Reject malformed provider responses and persisted refusal state."""
    if not isinstance(reviews, list) or any(
        not isinstance(review, dict) for review in reviews
    ):
        message = "reviews must be an array of objects"
        raise TypeError(message)
    for review in reviews:
        author = review.get("user") or review.get("author") or {}
        if not isinstance(author, dict):
            message = "review author must be an object"
            raise TypeError(message)
    if previous is None:
        return
    if not isinstance(previous, dict):
        message = "previous state must be an object"
        raise TypeError(message)
    evidence = previous.get("refusalEvidence", [])
    if not isinstance(evidence, list) or any(
        not isinstance(item, dict) for item in evidence
    ):
        message = "previous refusalEvidence must be an array of objects"
        raise TypeError(message)
    if type(previous.get("unserviceable", False)) is not bool:
        message = "previous unserviceable must be boolean"
        raise TypeError(message)


def main(argv: list[str] | None = None) -> int:
    """Classify a saved review response and optional prior PR state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args(argv)
    try:
        reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
        previous = (
            json.loads(args.previous.read_text(encoding="utf-8"))
            if args.previous
            else None
        )
        print(json.dumps(classify_reviews(reviews, previous), sort_keys=True))
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
