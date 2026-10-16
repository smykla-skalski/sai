"""Validate ship-it token and latency efficiency contracts.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIP_IT = ROOT / "plugins/ship-it/skills/ship-it"
REFERENCES = SHIP_IT / "references"
ADVERSARIAL_TEST = ROOT / "plugins/adversarial-test/skills/adversarial-test/references"
ROUTINE_GUIDANCE = (
    SHIP_IT / "SKILL.md",
    *(
        REFERENCES / name
        for name in (
            "inputs.md",
            "authorization.md",
            "explore.md",
            "branch.md",
            "implementation.md",
            "publish.md",
            "review.md",
            "test.md",
            "pr-loop.md",
            "completion.md",
            "risk-policy.json",
            "release-policy.json",
            "convergence-policy.json",
        )
    ),
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ShipItEfficiencyContractTest(unittest.TestCase):
    def test_draft_pr_precedes_review_and_test(self) -> None:
        skill = read(SHIP_IT / "SKILL.md")
        self.assertLess(
            skill.index("Phase 5 — Publish draft PR"), skill.index("Phase 6 — Review")
        )
        self.assertLess(skill.index("Phase 6 — Review"), skill.index("Phase 7 — Test"))
        publish = read(REFERENCES / "publish.md")
        implementation = read(REFERENCES / "implementation.md")
        self.assertIn("create a **draft** PR", publish)
        self.assertIn("let review run concurrently", publish)
        self.assertIn("same batched fix", publish)
        self.assertIn("always advance to `phase: publish`", implementation)

    def test_manual_test_runs_once_after_clean_review(self) -> None:
        testing = read(REFERENCES / "test.md")
        orchestration = read(REFERENCES / "orchestration.md")
        self.assertIn("only after the selected review gate is CLEAN", testing)
        self.assertIn("Run exactly one broad pass", testing)
        self.assertIn("must not rerun, widen or override it", testing)
        self.assertIn("Rerun only the surviving reproductions", testing)
        self.assertIn(
            "manual-test adversary starts after a clean review", orchestration
        )

    def test_build_cache_is_revision_keyed_and_not_polled(self) -> None:
        workflow = read(ADVERSARIAL_TEST / "workflow.md")
        mandate = read(ADVERSARIAL_TEST / "test-adversary.md")
        for text in (workflow, mandate):
            self.assertIn("revision-keyed build cache", text)
            self.assertIn("20 GB", text)
            self.assertIn("blocking command", text)
            self.assertIn("60 seconds", text)
        self.assertIn("exempt from per-run cleanup", workflow)

    def test_guidance_is_read_once_and_stays_bounded(self) -> None:
        skill = read(SHIP_IT / "SKILL.md")
        self.assertIn("Read this entry once", skill)
        self.assertIn("Do not reread a reference on phase transitions", skill)
        self.assertIn("under 12k input tokens", skill)
        self.assertIn("read only the checkpoint and current phase reference", skill)
        self.assertIn("mandate by path or inline exactly once", skill)
        self.assertLessEqual(
            sum(path.stat().st_size for path in ROUTINE_GUIDANCE), 52_000
        )
        for conditional in (
            "capabilities.md",
            "roles.md",
            "checkpoint.md",
            "risk.md",
            "release.md",
            "convergence.md",
        ):
            self.assertIn(f"references/{conditional}", skill)

    def test_local_telemetry_defaults_on(self) -> None:
        checkpoint = read(REFERENCES / "checkpoint.md")
        self.assertIn('"claims": false', checkpoint)
        self.assertIn('"evidence": false', checkpoint)
        self.assertIn('"telemetry": true', checkpoint)
        self.assertIn("checkpoint itself is mandatory", checkpoint)
        self.assertIn("scripts/bookkeeping.py", checkpoint)
        self.assertIn("Never renew on a timer", read(REFERENCES / "claims.md"))
        self.assertIn("With evidence disabled", read(REFERENCES / "pr-loop.md"))
        self.assertIn("Legacy runs used mandatory bookkeeping", checkpoint)

    def test_waits_are_event_driven_and_rate_limited(self) -> None:
        skill = read(SHIP_IT / "SKILL.md")
        review = read(REFERENCES / "review.md")
        testing = read(REFERENCES / "test.md")
        loop = read(REFERENCES / "pr-loop.md")
        events = read(REFERENCES / "worker-events.md")
        for wake_reason in (
            "completion",
            "failure",
            "cancellation",
            "user input",
            "configured deadline",
        ):
            with self.subTest(wake_reason=wake_reason):
                self.assertIn(wake_reason, events)
        self.assertIn("No event means continue the same wait", events)
        self.assertIn("no progress message, agent listing, terminal read", events)
        self.assertIn("one bounded fallback waiter per dispatch", events)
        self.assertIn("no more than once per ten minutes", events)
        self.assertIn(
            "an explicit deadline for every implementation, review, test", events
        )
        self.assertIn("host-required progress update", events)
        self.assertIn("does not restart the waiter", events)
        self.assertIn("references/worker-events.md", skill)
        self.assertIn("worker-events.md", review)
        self.assertIn("worker-events.md", testing)
        self.assertIn("worker-events.md", loop)

    def test_worker_events_are_idempotent_and_context_bound(self) -> None:
        events = read(REFERENCES / "worker-events.md")
        orchestration = read(REFERENCES / "orchestration.md")
        worker_rules = read(REFERENCES / "worker-rules.md")
        self.assertIn("stable dispatch ID", events)
        self.assertIn("each fresh worker its applicable mandate exactly once", events)
        self.assertIn("only current-phase guidance missing", events)
        self.assertIn("A replacement handoff is a fresh context", events)
        self.assertIn("Scope cancellation and user-input controls to the run", events)
        self.assertIn("process them before filtering stale dispatch events", events)
        self.assertIn("forbids any later gate or delivery action", events)
        self.assertIn("Ignore duplicate worker events", events)
        self.assertIn("delayed terminal events", events)
        self.assertIn(
            "duplicate or delayed completion events never dispatch", orchestration
        )
        self.assertIn("stable event ID", worker_rules)

    def test_coordinator_never_implements_children(self) -> None:
        orchestration = read(REFERENCES / "orchestration.md")
        self.assertIn("never edits product source", orchestration)
        self.assertIn("prompt under 2 KB", orchestration)
        self.assertIn(
            "never repeat the rules or fork coordinator history", orchestration
        )
        self.assertIn("exactly one final hand-back", orchestration)
        self.assertIn("never spawn new gates", orchestration)
        self.assertIn("100,000 cumulative input tokens", orchestration)
        self.assertIn(
            "100,000 cumulative input tokens",
            read(REFERENCES / "worker-rules.md"),
        )
        self.assertTrue((REFERENCES / "worker-rules.md").is_file())

    def test_workers_never_hand_edit_checkpoint_or_relay_authority(self) -> None:
        worker_rules = read(REFERENCES / "worker-rules.md")
        orchestration = read(REFERENCES / "orchestration.md")
        self.assertIn("Never write the checkpoint file directly", worker_rules)
        self.assertIn("stop as blocked, name the missing command", worker_rules)
        self.assertIn(
            "`create --grant-json` when the checkpoint does not exist yet, otherwise `add-grant`",
            worker_rules,
        )
        self.assertIn("relayed approval", worker_rules)
        self.assertIn("never user authority", worker_rules)
        self.assertIn("original authorizing message verbatim", orchestration)
        self.assertIn("goes in a file whose path replaces it", orchestration)
        self.assertIn(
            "transition --phase <current phase> --status blocked", worker_rules
        )
        self.assertIn(
            "`create` on an existing checkpoint leaves the file untouched", worker_rules
        )
        self.assertIn("never records the same message under a new ID", worker_rules)

    def test_unserviceable_hosted_review_is_not_requested(self) -> None:
        release = read(REFERENCES / "release.md")
        loop = read(REFERENCES / "pr-loop.md")
        self.assertIn("quota, permission or service-unavailable", release)
        self.assertIn("send no request", release)
        self.assertIn("activate its configured fallback immediately", release)
        self.assertIn("Never retry a request", loop)
        self.assertIn("immediately changes `hostedReviewDecision`", loop)
        self.assertIn(
            "one permitted `serviceable` to `fallback|blocked`",
            read(REFERENCES / "checkpoint.md"),
        )

    def test_default_off_claims_are_guarded_through_completion(self) -> None:
        for reference in ("inputs.md", "branch.md", "review.md", "completion.md"):
            with self.subTest(reference=reference):
                content = read(REFERENCES / reference)
                self.assertIn("claims enabled", content)
        testing = read(REFERENCES / "test.md")
        self.assertNotIn("PR creation as `nextAction`", testing)
        completion = read(REFERENCES / "completion.md")
        self.assertIn("With evidence disabled", completion)

    def test_resume_reconciles_delivery_before_planning(self) -> None:
        checkpoint = read(REFERENCES / "checkpoint.md")
        self.assertIn("reconcile-delivery --pull-request-json", checkpoint)
        self.assertIn("stop before planning or delivery work", checkpoint)
        self.assertIn(
            "`merged` advances directly to completion verification", checkpoint
        )
        self.assertIn("`closed-unmerged` stops", checkpoint)
        self.assertIn("Issue closure never follows from `pullRequestState`", checkpoint)
        self.assertIn(
            "A different PR URL conflicts with the stored identity", checkpoint
        )
        completion = read(REFERENCES / "completion.md")
        self.assertIn("Query the source issue separately", completion)
        inputs = read(REFERENCES / "inputs.md")
        self.assertIn(
            "Retain a closed issue's state until the durable checkpoint is resolved and reconciled",
            inputs,
        )
        self.assertIn(
            "A reconciled merge continues directly to completion and audits",
            inputs,
        )


if __name__ == "__main__":
    unittest.main()
