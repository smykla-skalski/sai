---
name: adversarial-review
description: Fast two-pass adversarial code review. A Code Adversary subagent red-teams a diff or PR to find the concrete bug, then a separate Findings Adversary subagent with a clean context tries to refute every finding to cut false positives. Use for routine changes where a full staff review is overkill, or as the review gate inside ship-it.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git; the gh CLI for PR reviews.
argument-hint: "[<pr-url> | <diff-file> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Two-pass adversarial code review in clean-context subagents
---


# Adversarial Review

Find the bug, then try to prove the bug report wrong. It answers one question - **is this change correct?** - and answers it hard. It does not evaluate architecture, conventions, dead code, or taste; that is `/staff-code-review`.

Two subagents, opposed, each with a clean context:

1. **Code Adversary** - assumes the change is broken and hunts the concrete failure. A `blocking:` finding carries an executed reproduction or an explicit interleaving trace; anything less is an `issue:` or a `question:`. Mandate: [references/code-adversary.md](references/code-adversary.md).
2. **Findings Adversary** - assumes the Code Adversary is wrong and tries to refute each finding against the source, stripping `blocking:` from findings without proof. Runs only when the first pass found a `blocking:` or `issue:`. Mandate: [references/findings-adversary.md](references/findings-adversary.md).

The second pass exists because an unrefuted adversary nit-bombs. It sees only the first pass's findings, never its reasoning, so it cannot inherit the same misread. Each adversary lives for exactly one verdict: it starts in a fresh context with no forked or inherited history, is closed once its reply is validated, and is never reused for a fix, a re-check or another change.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Phase 1 - Build the review assignment
4. Spawning a clean-context subagent
5. Phase 2 - Code Adversary
6. Phase 3 - Findings Adversary
7. Phase 4 - Apply verdicts
8. Output
9. Fallback - no subagents
10. Anti-patterns
11. Example invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Check every adversary's final verdict line against the workflow's documented format: one retry with a fresh subagent, then `Review Verdict: FAILED`.
- Never dispatch the Findings Adversary when no finding is labelled `blocking:` or `issue:`, and never reuse an adversary after its verdict.
- Stop at every hard stop named by the workflow and state the required next action.
