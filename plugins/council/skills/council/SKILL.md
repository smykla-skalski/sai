---
name: council
description: >-
  Run installed Codex reviewer-agent councils. Use when asked for council review,
  multi-reviewer critique, debate, or design/code/UX feedback. Inline text is
  target unless @path/diff supplied: do not search repos, local SKILL.md, Claude
  assets, MEMORY.md, prior runs, or current implementation.
---

# Council of Experts

Use native Codex reviewer agents from this installed skill. Do not use repo-local council skill files, Claude assets, Claude named subagents, or nested `codex exec`.

Native agent definitions carry identity, dossier links, and formats. Parent only selects slugs, supplies bounded material, validates text, and synthesizes. Never pass identity text/source paths; never read `MEMORY.md`, prior sessions/outputs, or git history unless requested.

Agent registry and rosters: `references/agents.md`.

## Mode Selection

If the request starts with `@<path>`, read that file first as problem context.

Parse the first token as mode when it is `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`; aliases: `eng`, `ux`, `mix`, `random`. Default to `core`.

- `core`: pick `core-eng`, `core-ux`, or `core-mix` from path and wording, then announce why.
- `auto`: read the registry, select exactly 6 best-fit reviewers, and include at least one bias-correction reviewer unless the request is narrow.
- fixed core modes: read only Mode Rosters, using `rg` or the first 12 lines; never print full registry tables.
- `all`: use every registry slug.
- `debate`: pick 3-6 reviewers for hard tradeoff calls.

## Codex Workflow

**Parent Work**

- Resolve mode, then read only explicit `@path`, exact path, diff, or snippet input.
- Inline prompts are the whole target; do not inspect repo trees, plugin/skill files, READMEs, Claude variants, current implementation, `MEMORY.md`, prior outputs, or broad context.
- Select reviewer agent slugs from the registry. Merge/dedupe matches; drop reviewers that only add generic agreement.
- Do not pre-read native agent definitions or dossiers. Reviewers load their own identity and canon.
- Slot prep: if `list_agents` is available, immediately after the final slug list call it before any `spawn_agent`; close stale council reviewers first: terminal/prior reviewers, acknowledgement-only leftovers, and old debate/retry agents not needed now. Never close unrelated workers, explorers, or user-owned agents.
- If `list_agents` is unavailable, do not fake cleanup; run bounded waves and close each wave before the next.
- If slot pressure remains, run waves: spawn what fits, harvest+close, then continue. Never leave old council reviewers open while starting a new council.
- Spawn each reviewer with `spawn_agent(agent_type: "<agent-slug>", fork_turns: "none")` and a task name using only lowercase letters, digits, and underscores. Do not pass `model` or `reasoning_effort` unless the user asks for an override.
- If a slug is unknown, skip it, continue with successful reviewers, and name the missing reviewer in the synthesis. Do not rebuild identity instructions in the assignment.
- Keep reviewers open for retries, debate rounds, or directly related follow-up work. Close every spawned reviewer after final result capture.

**Reviewer Assignment**

```text
This is the concrete review task. Review the supplied material through your native lens and return only your required reviewer output now.

<council-review-assignment>
Review summary: <problem context>
Primary review files:
- <absolute path 1, or `inline material only` when no file path was supplied>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>
Allowed extra reads:
- Only directly connected files needed to understand a concrete relationship already visible in the supplied material.

Rules:
- Complete this task now. Load native dossier if required, then review; do not report setup, AGENTS.md, RTK, tools, or readiness.
- Supplied material is full scope; `inline material only` is a valid target.
- No broad repo discovery, tests/builds/linters, git history, file edits, or subagents.
- Extra reads only for directly connected files; if still missing context, state the gap instead of exploring.
- Return required reviewer format; first non-empty line is the reviewer heading. No generic `Findings:`, quotes, JSON/XML/status wrapper, or ack-only reply.
</council-review-assignment>
```

**Result Handling**

- Wait with `wait_agent`; finished content may arrive as `<subagent_notification>`.
- Parse reviewer text only from `status.completed` or `close_agent.previous_status.completed`; all else is transport metadata. Never echo raw JSON, tags, notification envelopes, `status` objects, or tool payloads.
- Valid output has a reviewer-specific heading naming that reviewer, required sections, and real review body. Runtime `completed` is enough; `failed`, `cancelled`, `timed_out`, or empty output is not a review.
- Reject setup/status replies, acknowledgement-only replies, "repo rules noted", "no task supplied", generic `## Review` or `Findings:` output, missing reviewer heading, non-review execution, repo-wide discovery, or ignored scope.
- Recover once with `followup_task(interrupt: true)` on the same agent. Repeat the full assignment and begin: "This is the concrete review task. Review the supplied material through your native lens and return only your required reviewer output now. Do not acknowledge readiness or ask for another task." No short reminders.
- If the retry is still invalid, close and respawn once with `fork_turns: "none"` using the same strengthened full assignment. If the replacement fails, continue with successful reviewers and name the missing result.
- Drain mailbox until every reviewer is accepted or terminal. If a reviewer appears done but no text was captured, `close_agent` and harvest `previous_status.completed` before declaring it missing.
- Before final synthesis, call `close_agent` once for every spawned reviewer; process shutdown is not cleanup. Ignore session-recording warnings during close only if harvested review text is valid.
- Before final synthesis, check that every selected reviewer is accounted for as `accepted`, `missing`, or `failed`; the final answer must contain no raw notification tags, transport fields, or acknowledgement-only text.
- Synthesize convergence, real disagreement, and concrete next moves. Do not average reviewer output into bland consensus.

For debate mode, keep the same reviewer agents open across opening positions, responses, and final positions. Use `followup_task` for later rounds, require the same result validation each round, and close agents only after synthesis.

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

Agent dossiers are private aids. Do not republish them wholesale.
