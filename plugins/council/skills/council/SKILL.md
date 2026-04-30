---
name: council
description: >-
  Run installed Codex reviewer-agent councils. Use when asked for council review,
  multi-reviewer critique, debate, or design/code/UX feedback. Inline text is
  target unless @path/diff supplied: do not search repos, local SKILL.md, Claude
  assets, MEMORY.md, prior runs, or current implementation.
---

# Council of Experts

Use installed native Codex reviewer agents only. Do not use repo-local council skill files, Claude assets, Claude named subagents, nested `codex exec`, `MEMORY.md`, prior sessions, or git history unless requested.

Registry and rosters: `references/agents.md`. Agent definitions carry identity and format; the parent only selects slugs, supplies bounded material, validates text, and synthesizes.

## Mode Selection

If the request starts with `@<path>`, read that file first. Parse first token as mode: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`; aliases: `eng`, `ux`, `mix`, `random`. Default `core`.

- `core`: pick `core-eng`, `core-ux`, or `core-mix` from path and wording, then announce why.
- `auto`: read the registry, select exactly 6 best-fit reviewers, and include at least one bias-correction reviewer unless the request is narrow.
- fixed core modes: read exactly registry lines 1-12 for Mode Rosters; do not read beyond line 12.
- `all`: use every registry slug.
- `debate`: pick 3-6 reviewers for hard tradeoff calls.

## Codex Workflow

**Parent Work**

- Resolve mode, then read only explicit `@path`, exact path, diff, or snippet input. Inline text is the whole target; no repo trees, READMEs, plugin files, Claude variants, current implementation, broad context, or prior outputs.
- Select reviewer slugs from the registry. Merge/dedupe; drop reviewers that only add generic agreement. Do not pre-read agent definitions or dossiers.
- Capacity prep before any `spawn_agent`: `needed_slots = deduped slug count`; free capacity is proven only by a successful `list_agents` result.
- If `list_agents` exists, call it first and close only stale council-owned reviewers: terminal/prior reviewers, acknowledgement-only leftovers, old retry/debate agents, and previous council reviewers not needed now. Never close unrelated workers, explorers, or user-owned agents.
- Cleanup is incomplete while stale council-owned reviewers remain open. Start no council wave until they are closed or accounted for as unavailable.
- Spawn all reviewers at once only when `list_agents` proves at least `needed_slots` free slots after cleanup. If `list_agents` is unavailable or capacity is unproven, use one reviewer per wave. If capacity is known but limited, use waves that fit, max 3.
- Spawn each reviewer with `spawn_agent(agent_type: "<agent-slug>", fork_turns: "none")` and a task name using only lowercase letters, digits, and underscores. Do not pass `model` or `reasoning_effort` unless the user asks for an override.
- If a slug is unknown, skip it, continue with successful reviewers, and name the missing reviewer in the synthesis. Do not rebuild identity instructions in the assignment.
- Keep reviewers open for retries, debate rounds, or directly related follow-up work. Close every spawned reviewer after final result capture.

**Reviewer Assignment**

```text
Concrete review task. Review through your native lens and return only your required reviewer output now.

<council-review-assignment>
Review summary: <problem context>
Files: <absolute paths, or `inline material only`>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>

Rules:
- Supplied material is full scope; inline-only is valid.
- Extra reads only for directly connected files already implied by the material; state remaining gaps instead of exploring.
- No broad discovery, tests/builds/linters, git history, file edits, subagents, setup reports, AGENTS.md/RTK/tool summaries, readiness, or ack-only replies.
- First non-empty line is the reviewer heading. No generic `Findings:`, quotes, JSON/XML/status wrappers, or transport metadata.
</council-review-assignment>
```

**Result Handling**

- Per wave, run a health roundcheck loop before any closure:
  1. `wait_agent(timeout_ms: 30000)` to receive mailbox updates.
  2. Re-check each in-wave reviewer via `list_agents` / mailbox state.
  3. Continue polling until every reviewer is `completed`, `failed`, `cancelled`, or `timed_out`.
  4. Never close reviewers only because a poll interval ended.
- Reviewer wave timeout budget is `20m` wall-clock from first spawn in that wave. If budget is exceeded, mark remaining reviewers `missing` and continue synthesis with completed reviewers.
- Parse reviewer text only from `status.completed` or `close_agent.previous_status.completed`; all else is transport metadata. Never echo raw JSON, tags, envelopes, `status` objects, or tool payloads.
- Never answer with a single reviewer payload or mailbox item. If a draft starts with `{`, `{"author":`, `<subagent_notification>`, `## <one reviewer>`, or raw completed text, keep harvesting/closing and synthesize instead.
- Valid output has a reviewer-specific heading, required sections, and real review body. Runtime `completed` is enough; `failed`, `cancelled`, `timed_out`, or empty output is not a review.
- Reject setup/status replies, acknowledgement-only replies, "repo rules noted", "no task supplied", generic `## Review` or `Findings:` output, missing reviewer heading, non-review execution, repo-wide discovery, or ignored scope.
- For ack/status/no-task replies, close immediately and respawn once with `fork_turns: "none"`. For malformed near-reviews, recover once with `followup_task(interrupt: true)` or runtime `send_input`; repeat the full assignment and begin: "Concrete review task. Review through your native lens and return only your required reviewer output now. Do not acknowledge readiness or ask for another task."
- If the replacement/retry is invalid, continue and name the missing result.
- Drain mailbox until every reviewer is accepted or terminal. If a reviewer appears done but no text was captured, `close_agent` and harvest `previous_status.completed` before declaring it missing.
- Close reviewers only after they are terminal or explicitly invalid for retry handling. Do not perform blanket pre-synthesis closure of live reviewers.
- Before synthesis, ensure each selected reviewer has one final accounting state: `accepted`, `missing`, or `failed`.
- Before synthesis, account for every selected reviewer as `accepted`, `missing`, or `failed`; final answer must start with `# Council review:` and contain no raw notification tags, transport fields, or acknowledgement-only text.
- Synthesize convergence, real disagreement, and concrete next moves. Do not average reviewer output into bland consensus.

Debate mode: keep the same reviewers open across rounds, use `followup_task`, validate every round, close after synthesis.

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

Private dossiers are aids only; do not republish them wholesale.
