---
name: council
description: Run native Codex reviewer-agent councils for code, design, architecture, UX, reliability, performance, AI, strategy, or tradeoff review. Use when the user asks for council review, multi-reviewer critique, debate, design review, code review, architecture feedback, UX review, or tradeoff analysis.
---

# Council of Experts

Use native Codex reviewer agents. Do not use Claude named subagents or nested `codex exec`.

Reviewer identity, dossier links, and output format live in `codex/agents/<agent-slug>.toml`. The parent only selects agent slugs, supplies bounded review material, enforces review-only scope, and synthesizes results. Never pass identity text or source paths in reviewer assignments.

## Paths

- Registry and rosters: `codex/council/references/personas.md`
- Agent descriptors: `codex/agents/<agent-slug>.toml` in source, loaded at runtime from `~/.codex/agents/` or `.codex/agents/`

## Mode Selection

If the request starts with `@<path>`, read that file first as problem context.

Parse the first token as mode when it is `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`; aliases: `eng`, `ux`, `mix`, `random`. Default to `core`.

- `core`: pick `core-eng`, `core-ux`, or `core-mix` from path and wording, then announce why.
- `auto`: read the registry, select exactly 6 best-fit reviewers, and include at least one bias-correction reviewer unless the request is narrow.
- fixed core modes and `all`: use the registry rosters.
- `debate`: pick 3-6 reviewers for hard tradeoff calls.

## Codex Workflow

**Parent Work**

- Resolve mode, read explicit files, and build a bounded bundle from exact paths, diffs, snippets, and directly relevant adjacent context.
- Select reviewer agent slugs from the registry. Merge/dedupe matches; drop reviewers that only add generic agreement.
- Spawn each reviewer with `spawn_agent(agent_type: "<agent-slug>", fork_turns: "none")` and a unique underscore-only task name. Do not pass `model` or `reasoning_effort` unless the user asks for an override.
- If a slug is unknown, skip it, continue with successful reviewers, and name the missing reviewer in the synthesis. Do not rebuild identity instructions in the assignment.

**Reviewer Assignment**

```text
<council-review-assignment>
Review summary: <problem context>
Primary review files:
- <absolute path 1>
- <absolute path 2>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>
Allowed extra reads:
- Only directly connected files needed to understand a concrete relationship already visible in the supplied material.

Rules:
- Read your dossier first, then the supplied review material.
- Treat the supplied review material as the full scope.
- Do not use broad repo discovery, tests/builds/linters, git history, file edits, or subagents.
- Do not report setup, AGENTS.md, RTK, tools, or readiness.
- If context is still missing after bounded reads, state the missing piece instead of exploring further.
- Return only your required review format.
</council-review-assignment>
```

**Result Handling**

- Wait for all reviewers with `wait_agent`, then `close_agent` every spawned reviewer.
- Extract `status.completed` from `<subagent_notification>` transport envelopes when present. Never show raw transport JSON or tags to the user.
- Reject setup/status replies, missing review shape, skipped dossier reads, non-review execution, repo-wide discovery, or ignored scope.
- Recover once with `followup_task(interrupt: true)` and the same compact assignment. If still invalid, close and respawn once with `fork_turns: "none"`. If the replacement fails, continue with successful reviewers and name the missing result.
- Synthesize convergence, real disagreement, and concrete next moves. Do not average reviewer output into bland consensus.

For debate mode, run opening positions, responses, and final positions before synthesis.

## Synthesis Shape

```markdown
# Council review: <topic>
## Convergence (high-confidence signals)
<2-5 bullets. Format: `- [finding] - [reviewer1, reviewer2, reviewer3]`.>
## Disagreement (real tradeoffs the user must decide)
<2-4 bullets. Format: `- [axis] - [reviewer A] argues X / [reviewer B] argues Y. Decision is yours because <constraint>.`>
## Per-reviewer top-3
<For each reviewer that returned, three concrete bullets.>
## What to do next
<3-7 numbered concrete actions, smallest first, tied back to reviewers.>
## What we did not address
<1-3 bullets naming gaps the council does not cover for this problem.>
```

## Privacy / Scope

Agent dossiers in `codex/agents/references/` are private aids. Do not republish them wholesale. For external use, strip named-reviewer framing and restate arguments in your own voice.
