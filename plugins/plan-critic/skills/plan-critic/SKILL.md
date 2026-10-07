---
name: plan-critic
description: Critique an implementation plan before approving execution. Runs three persona reviewers (Skeptic, Architect, Verifier) against the codebase, in parallel on Claude Code and one at a time on other agents, and returns an Approve/Reject/Refine verdict with concrete refinements. Use when a plan has been generated (Plan Mode output, ExitPlanMode, pasted plan text, or plan file path) and needs review before code is written. Triggers on "critique this plan", "review this plan", "is this plan good", "poke holes in this plan", "should I approve this plan", or sharing a plan for evaluation.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs read access to the codebase the plan targets; no scripts or network access.
argument-hint: "[plan file path | paste plan inline | --from-conversation]"
allowed-tools: Agent AskUserQuestion Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Critique implementation plans before coding starts
---


# Plan Critic

Critique a Claude implementation plan **before** any code is written. The cost of revising a plan is near-zero; the cost of revising executed code is hours of rework. This skill applies the plan-then-execute discipline rigorously: nothing gets approved until three independent personas have inspected it.

**Core principle:** A plan that names files generically has not been read. A plan that references `verify_jwt_token` at `auth/middleware.go:42` has been read. The job of this skill is to tell those apart and force the second.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Workflow
4. Grounding Brief
5. Verdict: [APPROVE | REFINE | REJECT]
6. Triage Notes
7. Grounding Brief
8. Verifier Findings
9. Architect Findings
10. Skeptic Findings
11. Cross-Cutting Issues
12. Refinement List
13. Rejection Rationale
14. Next Action
15. Calibration Guidance
16. When to Skip Plan Review (limitations and scope boundaries)
17. Troubleshooting
18. Anti-Patterns to Avoid
19. Example invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
