---
name: adversarial-test
description: Adversarial manual testing of a change. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) in isolated state, and attacks boundaries, malformed input, repetition, and adjacent flows; every reproduction is then rerun to drop hallucinated failures. Use to prove a branch or PR actually works before merging, or as the testing gate inside ship-it.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git, a shell that can run the product under test, and gh for PR targets.
argument-hint: "[<pr-url> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Adversarial manual testing in a clean-context subagent
---


# Adversarial Test

Prove the change does **not** do what the task says - by running it. It answers one question - **does this change work for a user?** - and answers it with commands and output, not by reading code. Code correctness review is the `adversarial-review` skill.

One subagent with a clean context, then a check by you:

1. **Test Adversary** - derives acceptance criteria, runs the real surface, attacks it, and reports self-contained reproductions. Mandate: [references/test-adversary.md](references/test-adversary.md).
2. **Reproduction check** - you rerun each reproduction verbatim in a fresh shell. A failure that never happened does not survive.

The subagent gets a clean context so it tests the task, not the implementer's belief about the task.

Verdicts: `PASS`; `PASS (partial)` when a criterion stayed `UNTESTED` because the environment (sandbox, tooling, build, an unreachable pane) could not exercise it - callers treat it as passing and list the untested criteria; `FAIL`; `BLOCKED` only for a product precondition a human must supply. A UI change needs a screenshot of the changed surface at a viewport of at least 2560x1440 in the evidence directory. A tester that twice declines a runnable surface triggers the inline fallback, not `BLOCKED`.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Phase 1 - Build the test assignment
4. Phase 2 - Test Adversary (subagent)
5. Phase 3 - Reproduction check
6. Output
7. Fallback - no subagents
8. Anti-patterns
9. Example invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
