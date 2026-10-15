#!/usr/bin/env python3
"""Calculate privacy-safe USD estimates from disjoint host token usage deltas.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import re
from decimal import Decimal, localcontext
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    import argparse

CATEGORIES: Final[tuple[str, ...]] = ("input", "cache_write", "cache_read", "output")
PRICE: Final[re.Pattern[str]] = re.compile(r"^\d{1,12}(?:\.\d{1,12})?$")


class UsageError(Exception):
    """Reject unsafe usage metadata."""


def validate_usage(args: argparse.Namespace) -> dict[str, Any]:
    """Validate numeric host usage and prices before persistence."""
    tokens: dict[str, int | None] = {}
    prices: dict[str, str | None] = {}
    for category in CATEGORIES:
        count = getattr(args, f"{category}_tokens")
        price = getattr(args, f"{category}_price")
        if count is not None and (count < 0 or count > 10**18):
            message = "usage token counts must be between 0 and 10^18"
            raise UsageError(message)
        if price is not None and not PRICE.fullmatch(price):
            message = "prices require nonnegative decimals, at most 12 digits per part"
            raise UsageError(message)
        tokens[category] = count
        prices[category] = price
    return {"tokens": tokens, "prices_usd_per_million": prices}


def estimate(usage: dict[str, Any] | None) -> Decimal | None:
    """Calculate a complete observation estimate or retain unknown."""
    if usage is None:
        return None
    total = Decimal(0)
    with localcontext() as context:
        context.prec = 60
        for category in CATEGORIES:
            count = usage["tokens"][category]
            price = usage["prices_usd_per_million"][category]
            if count is None or (count != 0 and price is None):
                return None
            if count:
                total += Decimal(count) * Decimal(price) / 1_000_000
    return total


def aggregate(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum disjoint estimates without treating missing usage as zero."""
    values = [estimate(event.get("usage")) for event in events]
    complete = bool(values) and all(value is not None for value in values)
    with localcontext() as context:
        context.prec = 60
        known = sum((value for value in values if value is not None), Decimal(0))
    return {
        "estimated_usd": str(known) if complete else None,
        "known_estimated_usd": str(known)
        if any(value is not None for value in values)
        else None,
        "unknown_observations": sum(value is None for value in values),
        "usage_observations": len(values),
    }


def summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Group estimated cost by phase and execution role."""
    usage_events = [event for event in events if event.get("event") == "usage_recorded"]
    return {
        "currency": "USD",
        "basis": "host usage deltas; caller-supplied USD prices per million tokens",
        "total": aggregate(usage_events),
        "by_phase": {
            phase: aggregate(
                [event for event in usage_events if event["phase"] == phase],
            )
            for phase in sorted({event["phase"] for event in usage_events})
        },
        "by_role": {
            role: aggregate([event for event in usage_events if event["role"] == role])
            for role in sorted({event["role"] for event in usage_events})
        },
    }


def markdown(report: dict[str, Any], version: str) -> str:
    """Render only privacy-safe cost aggregates for the merged PR."""
    cost = report["token_cost"]
    lines = [
        "<!-- ship-it-cost:" + report["run_id"] + " -->",
        "Ship-it token cost estimate (plugin " + version + ")",
        "",
        ("| Scope | Estimated USD | Known subtotal USD | Unknown observations |"),
        "| --- | ---: | ---: | ---: |",
    ]
    groups = [("Run total", cost["total"])]
    for grouping in ("by_phase", "by_role"):
        groups.extend(
            (grouping + ": " + name, value) for name, value in cost[grouping].items()
        )
    for name, value in groups:
        amount = value["estimated_usd"] or "unknown"
        subtotal = value["known_estimated_usd"] or "unknown"
        unknown = value["unknown_observations"]
        lines.append(f"| {name} | {amount} | {subtotal} | {unknown} |")
    lines.extend(["", "Host usage and supplied prices; unknown figures are not zero."])
    return "\n".join(lines)
