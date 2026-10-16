#!/usr/bin/env python3
"""Block on GitHub checks, reviews and threads using gh alone.

Usage: hosted_wait.py OWNER/REPO NUMBER --head SHA [--check NAME]
    [--reviewer LOGIN:review|approval] [--thread-author LOGIN]
    [--timeout 1800] [--interval 30]
Output: one JSON terminal summary, including changed requirements.
Exit: 0 satisfied, 1 failed/changed/closed/deadline, 2 API/input error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from typing import Final

from copilot_quota import DEFAULT_MAX_AGE, classify_and_remember
from copilot_review import classify_reviews

MAX_TIMEOUT: Final = 86400
MAX_INTERVAL: Final = 600


class ForgeError(ValueError):
    """A forge response cannot establish gate state."""


def _gh_json(payload: dict, timeout: float) -> dict:
    try:
        result = subprocess.run(
            args=["/usr/bin/env", "gh", "api", "graphql", "--input", "-"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError from error
    except OSError as error:
        raise ForgeError(str(error)) from error
    if result.returncode:
        raise ForgeError(result.stderr.strip() or "gh failed")
    try:
        decoded = json.loads(result.stdout)
        if not isinstance(decoded, dict):
            message = "gh returned a non-object response"
            raise ForgeError(message)
    except json.JSONDecodeError as error:
        message = "gh returned malformed JSON"
        raise ForgeError(message) from error
    else:
        return decoded


class GitHub:
    """Read paginated GitHub state within one monotonic deadline."""

    def __init__(
        self,
        repository: str,
        number: int,
        deadline: float,
        *,
        quota_max_age: int = DEFAULT_MAX_AGE,
        merge_integration: int | None = None,
    ) -> None:
        """Retain the PR identity and wait deadline."""
        self.repository = repository
        self.number = number
        self.deadline = deadline
        self.quota_max_age = quota_max_age
        self.review_state: dict | None = None
        self.merge_integration = merge_integration

    def _request(self, payload: dict) -> dict:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        try:
            return _gh_json(payload, min(60, remaining))
        except TimeoutError:
            if time.monotonic() >= self.deadline:
                raise
            message = "gh request timed out before the overall deadline"
            raise ForgeError(message) from None

    def _review_exempt(self, pr: dict) -> bool:
        if self.merge_integration is None:
            return False
        protection = (pr.get("baseRef") or {}).get("branchProtectionRule")
        if protection and protection.get("requiresApprovingReviews", True):
            return False
        rules = (pr.get("baseRef") or {}).get("rules") or {}
        if rules.get("pageInfo", {}).get("hasNextPage", True):
            return False
        review_rules = [
            r for r in rules.get("nodes", []) if r["type"] == "PULL_REQUEST"
        ]
        return bool(review_rules) and all(
            self._ruleset_review_exempt(rule) for rule in review_rules
        )

    def _ruleset_review_exempt(self, rule: dict) -> bool:
        detail = rule.get("repositoryRuleset") or {}
        actors = detail.get("bypassActors") or {}
        if (
            type(detail.get("databaseId")) is not int
            or detail["databaseId"] <= 0
            or detail.get("enforcement") != "ACTIVE"
            or detail.get("target") != "BRANCH"
            or not detail.get("updatedAt")
            or actors.get("pageInfo", {}).get("hasNextPage", True)
        ):
            return False
        return any(
            entry["bypassMode"] == "EXEMPT"
            and (actor := entry.get("actor")) is not None
            and actor.get("__typename") == "App"
            and type(actor.get("databaseId")) is int
            and actor["databaseId"] == self.merge_integration
            for entry in actors.get("nodes", [])
        )

    def read(self) -> dict:
        """Read every page with one fixed gh command and JSON stdin."""
        owner, name = self.repository.split("/")
        query = """query($owner:String!,$name:String!,$number:Int!,
$checks:String,$reviews:String,$threads:String,$mergeActor:Boolean!){
repository(owner:$owner,name:$name){
pullRequest(number:$number){headRefOid baseRefName state merged reviewDecision
baseRef{branchProtectionRule{requiredStatusCheckContexts requiresApprovingReviews}
rules(first:100) @include(if:$mergeActor){nodes{type
repositoryRuleset{databaseId enforcement target updatedAt
bypassActors(first:100){nodes{bypassMode actor{__typename ... on App{databaseId}}}
pageInfo{hasNextPage}}}} pageInfo{hasNextPage endCursor}}}
commits(last:1){nodes{commit{statusCheckRollup{contexts(first:100,after:$checks){
nodes{__typename ... on CheckRun{databaseId name status conclusion checkSuite{id}
isRequired(pullRequestNumber:$number)} ... on StatusContext{id context state
isRequired(pullRequestNumber:$number)}} pageInfo{hasNextPage endCursor}}}}}}
reviews(first:100,after:$reviews){nodes{databaseId state body url submittedAt
author{login}}
pageInfo{hasNextPage endCursor}}
reviewThreads(first:100,after:$threads){nodes{id isResolved isOutdated
comments(first:1){nodes{author{login}}}} pageInfo{hasNextPage endCursor}}}}}
"""
        variables = {
            "owner": owner,
            "name": name,
            "number": self.number,
            "mergeActor": self.merge_integration is not None,
        }
        collected = {"checks": [], "reviews": [], "threads": []}
        finished: set[str] = set()
        observed_head = None
        observed_base = None
        policy_snapshot: list[dict] = []
        policy_consistent = True
        while len(finished) < len(collected):
            response = self._request({"query": query, "variables": variables})
            if response.get("errors"):
                message = "GitHub GraphQL returned errors"
                raise ForgeError(message)
            pr = response["data"]["repository"]["pullRequest"]
            head = pr["headRefOid"]
            if observed_head is not None and head != observed_head:
                return {"head": head}
            observed_head = head
            if observed_base is not None and pr["baseRefName"] != observed_base:
                message = "PR base branch changed during snapshot"
                raise ForgeError(message)
            observed_base = pr["baseRefName"]
            rollup = pr["commits"]["nodes"][0]["commit"]["statusCheckRollup"]
            connections = {
                "checks": rollup["contexts"] if rollup else None,
                "reviews": pr["reviews"],
                "threads": pr["reviewThreads"],
            }
            policy_consistent &= _consistent_policy(
                pr.get("baseRef"),
                policy_snapshot,
            )
            _collect_page(connections, collected, finished, variables)
        serviceability = classify_and_remember(
            _submitted_reviews(collected),
            self.review_state,
            max_age=self.quota_max_age,
        )
        self.review_state = serviceability
        state = _normalize(pr, collected, serviceability)
        if pr["reviewDecision"] == "REVIEW_REQUIRED":
            state["mergeActorReviewExempt"] = policy_consistent and self._review_exempt(
                pr,
            )
        return state


def _consistent_policy(policy: dict | None, previous: list[dict]) -> bool:
    if policy is None or (previous and previous[0] != policy):
        return False
    previous[:] = [policy]
    return True


def _collect_page(
    connections: dict,
    collected: dict,
    finished: set[str],
    variables: dict,
) -> None:
    for key, connection in connections.items():
        if key in finished:
            continue
        if connection is None:
            finished.add(key)
            continue
        collected[key].extend(connection["nodes"])
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            finished.add(key)
        elif not page["endCursor"] or page["endCursor"] == variables.get(key):
            message = "GitHub pagination did not advance"
            raise ForgeError(message)
        else:
            variables[key] = page["endCursor"]


def _submitted_reviews(collected: dict) -> list[dict]:
    return [
        {
            "id": r["databaseId"],
            "state": r["state"],
            "body": r.get("body", ""),
            "html_url": r.get("url"),
            "submitted_at": r.get("submittedAt"),
            "user": {"login": (r.get("author") or {}).get("login", "deleted")},
        }
        for r in collected["reviews"]
    ]


def _normalize(pr: dict, collected: dict, serviceability: dict | None = None) -> dict:
    checks = []
    statuses = []
    required = []
    latest: dict[tuple[str, str, str], dict] = {}
    for item in collected["checks"]:
        key = (
            item["__typename"],
            item.get("name", item.get("context")),
            item["checkSuite"]["id"] if item["__typename"] == "CheckRun" else "",
        )
        previous = latest.get(key)
        if previous is None or item.get("databaseId", 0) > previous.get(
            "databaseId",
            0,
        ):
            latest[key] = item
    for item in latest.values():
        if item["__typename"] == "CheckRun":
            checks.append(
                {
                    "id": item["databaseId"],
                    "suite": item["checkSuite"]["id"],
                    "name": item["name"],
                    "status": item["status"].lower(),
                    "conclusion": (item["conclusion"] or "").lower(),
                },
            )
            state = checks[-1]
            bucket = (
                "pending"
                if state["status"] != "completed"
                else (
                    "pass"
                    if state["conclusion"] in {"success", "neutral", "skipped"}
                    else "fail"
                )
            )
            name = item["name"]
        else:
            statuses.append(
                {
                    "id": len(statuses),
                    "context": item["context"],
                    "state": item["state"].lower(),
                },
            )
            bucket = {
                "SUCCESS": "pass",
                "PENDING": "pending",
                "EXPECTED": "pending",
            }.get(item["state"], "fail")
            name = item["context"]
        if item["isRequired"]:
            required.append({"name": name, "bucket": bucket})
    protection = (pr.get("baseRef") or {}).get("branchProtectionRule") or {}
    present = {item["name"] for item in required}
    required.extend(
        {"name": name, "bucket": "pending"}
        for name in protection.get("requiredStatusCheckContexts", [])
        if name not in present
    )
    serviceability = serviceability or classify_reviews(_submitted_reviews(collected))
    return {
        "copilotUnserviceable": serviceability["unserviceable"],
        "copilotQuotaMemory": serviceability.get("quotaMemory"),
        "head": pr["headRefOid"],
        "state": pr["state"],
        "merged": pr["merged"],
        "reviewDecision": pr["reviewDecision"],
        "threads": collected["threads"],
        "checks": checks,
        "statuses": statuses,
        "reviews": serviceability["reviews"],
        "required": required,
    }


def evaluate(
    snapshot: dict,
    head: str,
    checks: list[str],
    reviewers: dict[str, str],
    thread_authors: list[str],
) -> dict:
    """Classify one snapshot against explicit and platform requirements."""
    pending: list[str] = []
    failed: list[str] = []
    if snapshot["head"] != head:
        return {
            "status": "head-changed",
            "pending": [],
            "failed": [],
            "head": snapshot["head"],
        }
    if snapshot["merged"] or snapshot["state"] != "OPEN":
        return {
            "status": "merged" if snapshot["merged"] else "closed",
            "pending": [],
            "failed": [],
        }
    _check_requirements(snapshot, checks, pending, failed)
    _review_requirements(snapshot, reviewers, pending, failed)
    _thread_requirements(snapshot, thread_authors, pending)
    return {
        "status": "failed" if failed else "pending" if pending else "satisfied",
        "pending": sorted(pending),
        "failed": sorted(failed),
    }


def _check_requirements(
    snapshot: dict,
    checks: list[str],
    pending: list[str],
    failed: list[str],
) -> None:
    latest: dict[tuple[str, str], dict] = {}
    for check in sorted(snapshot["checks"], key=lambda c: c["id"]):
        latest[(check["name"], check["suite"])] = check
    statuses: dict[str, dict] = {}
    for status in sorted(snapshot["statuses"], key=lambda c: c["id"]):
        statuses[status["context"]] = status
    for required in snapshot.get("required", []):
        if required["bucket"] in {"fail", "cancel"}:
            failed.append(f"check:{required['name']}:{required['bucket']}")
        elif required["bucket"] not in {"pass", "skipping"}:
            pending.append(f"check:{required['name']}:pending")
    for name in checks:
        matching = [check for (label, _), check in latest.items() if label == name]
        status = statuses.get(name)
        if not matching and not status:
            pending.append(f"check:{name}:missing")
        for check in matching:
            _named_check(name, check, None, pending, failed)
        _named_check(name, None, status, pending, failed)


def _named_check(
    name: str,
    check: dict | None,
    status: dict | None,
    pending: list[str],
    failed: list[str],
) -> None:
    if check:
        if check["status"] != "completed":
            pending.append(f"check:{name}:pending")
        elif check["conclusion"] not in {"success", "neutral", "skipped"}:
            failed.append(f"check:{name}:{check['conclusion']}")
    if status:
        if status["state"] == "pending":
            pending.append(f"status:{name}:pending")
        elif status["state"] != "success":
            failed.append(f"status:{name}:{status['state']}")


def _changes_requested(reviews: list[dict]) -> bool:
    decisions = {
        review["user"]["login"].casefold(): review["state"]
        for review in sorted(reviews, key=lambda r: r["id"])
        if review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
    }
    return "CHANGES_REQUESTED" in decisions.values()


def _review_requirements(
    snapshot: dict,
    reviewers: dict[str, str],
    pending: list[str],
    failed: list[str],
) -> None:
    requirements = {login.casefold(): value for login, value in reviewers.items()}
    effective: dict[str, dict] = {}
    for review in sorted(snapshot["reviews"], key=lambda r: r["id"]):
        if review["state"] not in {"PENDING", "COMMENTED"} or (
            requirements.get(review["user"]["login"].casefold(), "review") == "review"
            and review["state"] == "COMMENTED"
        ):
            effective[review["user"]["login"].casefold()] = review
    for login, requirement in reviewers.items():
        review = effective.get(login.casefold())
        if login.casefold().removesuffix("[bot]") in {
            "copilot",
            "copilot-pull-request-reviewer",
            "copilot-pull-request-reviewer[bot]",
        } and (
            snapshot.get("copilotUnserviceable")
            or (snapshot.get("copilotQuotaMemory") and not review)
        ):
            failed.append(f"review:{login}:unserviceable:activate-configured-fallback")
            continue
        if not review or review["state"] == "DISMISSED":
            pending.append(f"review:{login}:missing")
        elif review["state"] == "CHANGES_REQUESTED":
            failed.append(f"review:{login}:changes-requested")
        elif requirement == "approval" and review["state"] != "APPROVED":
            pending.append(f"review:{login}:approval")
    if snapshot["reviewDecision"] == "CHANGES_REQUESTED" or _changes_requested(
        snapshot["reviews"],
    ):
        failed.append("platform:changes-requested")
    elif snapshot["reviewDecision"] == "REVIEW_REQUIRED" and not snapshot.get(
        "mergeActorReviewExempt",
        False,
    ):
        pending.append("platform:review-required")


def _thread_requirements(
    snapshot: dict,
    thread_authors: list[str],
    pending: list[str],
) -> None:
    authors = {a.casefold() for a in thread_authors}
    for thread in snapshot["threads"]:
        author = (
            thread["comments"]["nodes"][0].get("author")
            if thread["comments"]["nodes"]
            else None
        )
        if (
            not thread["isResolved"]
            and not thread["isOutdated"]
            and (not authors or (author and author["login"].casefold() in authors))
        ):
            pending.append(f"thread:{thread['id']}")


def wait(
    forge: GitHub,
    head: str,
    policy: tuple[list[str], dict[str, str], list[str]],
    interval: float = 30,
) -> dict:
    """Sleep between complete snapshots and emit only the terminal outcome."""
    checks, reviewers, thread_authors = policy
    deadline = forge.deadline
    previous: dict | None = None
    changes: set[str] = set()
    while True:
        try:
            snapshot = forge.read()
            result = evaluate(snapshot, head, checks, reviewers, thread_authors)
        except TimeoutError:
            result = previous or {"pending": ["snapshot:unavailable"], "failed": []}
            return {**result, "status": "deadline", "changed": sorted(changes)}
        if previous:
            before = set(previous["pending"] + previous["failed"])
            after = set(result["pending"] + result["failed"])
            changes.update(before.symmetric_difference(after))
        previous = result
        if result["status"] != "pending":
            return {**result, "changed": sorted(changes)}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {**result, "status": "deadline", "changed": sorted(changes)}
        time.sleep(min(interval, remaining))


def main() -> int:
    """Validate CLI arguments and print one compact terminal result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("number", type=int)
    parser.add_argument("--head", required=True)
    parser.add_argument("--quota-max-age", type=int, default=DEFAULT_MAX_AGE)
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--reviewer", action="append", default=[])
    parser.add_argument("--thread-author", action="append", default=[])
    parser.add_argument("--merge-integration", type=int)
    parser.add_argument("--bot-comment")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    if (args.merge_integration is None) != (args.bot_comment is None):
        parser.error("--merge-integration and --bot-comment must be supplied together")
    if args.merge_integration is not None and (
        args.merge_integration <= 0 or not args.bot_comment.strip()
    ):
        parser.error(
            "expected a positive integration ID and exact non-empty bot comment",
        )
    reviewers = {}
    for item in args.reviewer:
        login, separator, requirement = item.partition(":")
        if not separator or not login or requirement not in {"review", "approval"}:
            parser.error("--reviewer must be LOGIN:review or LOGIN:approval")
        reviewers[login] = requirement
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repository) or args.number < 1:
        parser.error("expected OWNER/REPO and a positive PR number")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.head):
        parser.error("--head must be a full commit SHA")
    if not 0 < args.timeout <= MAX_TIMEOUT or not 0 < args.interval <= MAX_INTERVAL:
        parser.error("timeout must be 0..86400 and interval 0..600 seconds")
    if args.quota_max_age <= 0:
        parser.error("--quota-max-age must be positive seconds")
    deadline = time.monotonic() + args.timeout
    try:
        result = wait(
            GitHub(
                args.repository,
                args.number,
                deadline,
                quota_max_age=args.quota_max_age,
                merge_integration=args.merge_integration,
            ),
            args.head,
            (args.check, reviewers, args.thread_author),
            interval=args.interval,
        )
    except (ForgeError, KeyError, OSError, TypeError, ValueError) as error:
        print(json.dumps({"status": "error", "detail": str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "satisfied" else 1


if __name__ == "__main__":
    raise SystemExit(main())
