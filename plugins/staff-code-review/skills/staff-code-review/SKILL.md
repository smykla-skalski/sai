---
name: staff-code-review
description: Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, performance, scalability, backward compatibility, observability, security, and cross-team impact. Use when reviewing a PR (URL or diff), analyzing code changes for architectural fitness, or when the user asks for a thorough/staff-level/senior review of code changes. Triggers on "review this PR", "review these changes", "staff review", "thorough code review", sharing a GitHub PR URL for review, or asking about the architectural impact of changes.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and python3; gh (authenticated) for PR targets and posting. The council and humanize plugins are optional.
argument-hint: "<pr-url|file-paths|diff> [--no-adversary]"
allowed-tools: Agent Bash Read Write
user-invocable: true
metadata:
  short-description: Review changes at staff level
---

# Staff-Level Code Review

Review whether a change should exist, fits the system, survives failure, and remains operable at scale. Do not stop at line-level correctness.

## Required guidance

Before reviewing, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure for input resolution, research, every review lens, synthesis, adversarial verification, humanization, persistence, GitHub posting, output format, and severity calibration. Follow its phases in order and load every deeper reference it names at the stated gate.

Paths in the guidance are relative to this skill directory. On agents without Claude features, use the compatibility fallbacks in its `Agent compatibility` section. Take an unresolved `$ARGUMENTS` value from the user's request.

## Core flow

1. Resolve a GitHub PR, file paths, or pasted diff; strip `--no-adversary` before resolving the target.
2. Triage necessity, problem fit, failure tolerance, comprehensibility, architectural fit, stakeholder impact, scope, size, description quality, and tests. Stop before deep review when the approach itself is wrong.
3. Build one time-bounded Research Brief covering callers, patterns, tests, history, and architecture. Give the same brief and diff to every lens.
4. Run all seven dimension reviews plus the Code Adversary. Claude Code may run them in parallel; other agents follow the sequential fallbacks in the detailed workflow.
5. Translate council-persona output when needed, synthesize and deduplicate findings, then run the independent Findings Adversary unless `--no-adversary` was given.
6. Apply the adversary verdicts, correct invalid locations and severities, and recompute the final verdict.
7. Humanize the final comments, save the artifact, and post only when the user explicitly asked for GitHub posting.

## Persona dispatch

Keep these exact dimension-to-reviewer mappings. Bundled mandates live in `references/agents/`; pass absolute deep-reference paths to subagents.

| Dimension | Claude Code persona | Bundled reviewer (`staff-code-review:` prefix) | Deep reference |
|---|---|---|---|
| Architecture & Design | `council:evans-ddd-reviewer` | `architecture-design-reviewer` | - |
| Reliability & Operations | `council:hebert-resilience-reviewer` | `reliability-operations-reviewer` | - |
| Security & Dependencies | `council:ai-quality-advisor` | `security-dependencies-reviewer` | - |
| Performance & Scalability | `council:gregg-perf-reviewer` | `performance-scalability-reviewer` | `references/performance-scalability.md` |
| Backward Compatibility | `council:siracusa-mac-critic` | `backward-compatibility-reviewer` | `references/backward-compatibility.md` |
| Convention Conformance & Code Reuse | `council:antirez-simplicity-reviewer` | `convention-conformance-reviewer` | `references/convention-conformance.md` |
| Dead Code | `council:tef-deletability-reviewer` | `dead-code-reviewer` | `references/dead-code.md` |

Run `staff-code-review:code-adversary` after the seven dimensions. After synthesis, run `staff-code-review:review-adversary`. When named agents are unavailable, prepend the identical mandate from `references/agents/<name>.md` to a generic subagent or execute it inline as the detailed fallback specifies.

## Invariants

- Ground every finding in the diff and surrounding repository evidence; include a valid changed `file:line` for GitHub comments.
- Never invent a target, caller, failure, or location.
- Preserve each council persona's native voice until translation.
- Do not let constructive reviewers validate their own findings.
- Apply REMOVE, DOWNGRADE, and REWORD verdicts before output.
- Never post without explicit user intent; a review request alone returns the review in chat.
