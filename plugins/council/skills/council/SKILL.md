---
name: council
description: >-
  Run native Codex reviewer-agent councils. Use when the user explicitly asks for
  $council, council review, multi-reviewer critique, debate, or code/design/UX
  feedback. Broad runs above 6 reviewers need current-run approval.
---

# Council of Experts

Use native Codex reviewer agents only. Do not use Claude assets, nested `codex exec`, `MEMORY.md`, prior runs, or git history unless the user explicitly asks.

You are the orchestrator and synthesizer. Fan-out is not completion: final output must be based on accepted reviewer results and integrated in your voice.

Registry: `references/agents.md`. Read it only for rosters, slugs, and selection hints. Agent definitions carry identity and format; do not recreate them in the parent.

## Modes

Parse first token as mode: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`; aliases: `eng`, `ux`, `mix`, `random`. Default `core`. If input starts with `@<path>`, read exactly that file first.

- `core`: choose `core-eng`, `core-ux`, or `core-mix` from path and wording.
- `auto`: read the registry, select exactly 6 best-fit reviewers, and include at least one bias-correction reviewer unless the request is narrow.
- fixed core modes: use the exact roster from registry Mode Rosters.
- `all`: use every registry slug.
- `debate`: pick 3-6 reviewers for hard tradeoff calls.

For any roster above 6, get explicit current-run approval before spawning reviewer 7+. If approval/user-input is unavailable, the session is non-interactive, or there is doubt the user can answer now, output exactly `Council not run: broad council approval not granted.` and stop. The original `$council all ...` request is not approval.

## Workflow

1. Resolve mode and bounded material. Inline text is full scope. Read only explicit `@path`, exact path, supplied diff, or snippet. No broad repo discovery.
2. Select/dedupe slugs from the registry. Do not pre-read agent definitions or dossiers.
3. If available, call `list_agents`; close only stale council-owned reviewers. Never close unrelated workers/explorers/user agents. Unknown capacity means one reviewer per wave; known limited capacity means waves that fit, max 3. Respect `agents.max_threads`, `multi_agent_v2`, and live `max_concurrent_threads_per_session`.
4. Spawn each reviewer with `spawn_agent(agent_type: "<slug>", fork_turns: "none")`; task names use lowercase letters, digits, and underscores. Do not pass model or reasoning overrides unless requested. Unknown slug: skip and account for it.
5. After spawn, supervise in this same run. Use sparse `Council progress:` lines only for real liveness: fan-out started, about half returned, a nudge happened, or another minute passed.
6. Per wave, loop on `wait_agent(timeout_ms: 60000)`. At least once per minute classify every live reviewer as `healthy`, `drifting`, `stalled`, `blocked`, or `done`; immediately `followup_task` non-healthy reviewers with the bounded task and output shape. Wave timeout is 20m.
7. Accept only completed reviewer text with a reviewer-specific heading and real review body. Reject raw JSON/tags/tool payloads, ack-only/status/setup replies, generic `Findings:`, broad discovery, and empty output. Retry ack/no-task once with `fork_turns: "none"`; recover malformed near-reviews once with `followup_task`.
8. Drain until every selected reviewer is `accepted`, `missing`, or `failed`. Close spawned reviewers only after terminal/invalid/retry handling; harvest `close_agent.previous_status.completed` if needed.
9. Synthesize one integrated result. Never answer with a single reviewer payload or raw `## <reviewer> review`. Avoid approval-shaped language such as `APPROVED`, `NOT APPROVED`, or `approved`; say whether material blockers remain.

## Assignment

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

Debate/follow-up challenges: keep the same reviewers open when available, use `followup_task`, validate every round, close after synthesis, and answer with one integrated addendum.

## Output

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
