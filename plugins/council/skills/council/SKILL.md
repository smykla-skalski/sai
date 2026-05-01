---
name: council
description: >-
  Use when user asks $council/review/debate. If all/broad>6 lacks approval: no
  tools/commentary; output only `Council not run: broad council approval not
  granted.` Else read SKILL, spawn reviewers, never solo. Inline complete unless
  @path/files/diff; no web/MEMORY/repo/git/prior/Claude/local lookup.
---

# Council

Run native Codex reviewer agents and synthesize accepted results. Never answer solo. Inline text is the complete target unless the user gives `@path`, exact paths, a diff, or an explicit read/search instruction. Otherwise do not use web/browser/search, Claude assets, nested `codex exec`, `MEMORY.md`, prior runs, repo search, git history, or local-file discovery.

Registry: `references/agents.md` beside this `SKILL.md`; resolve from the loaded skill directory and never search for it. For fixed modes read only the Mode Rosters section, not selection tables. Agent definitions carry identity and format; do not restate them.

## Modes

First token is mode: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`; aliases `eng`, `ux`, `mix`, `random`; default `core`. `core` chooses one fixed core roster from path/wording. `auto` selects exactly 6 best-fit reviewers and includes one bias-correction reviewer unless narrow. `debate` uses 3-6 reviewers. Fixed modes and `all` use registry rosters exactly.

Before spawning reviewer 7+, get explicit approval in this run. If an approval tool exists, use only choices `Approve full council (<N> reviewers)`, `Reduce to 6 reviewers`, `Cancel this council run`. If no approval/user-input is available, non-interactive, or uncertain, output exactly `Council not run: broad council approval not granted.` and stop. The original `$council all ...` request is never approval.

## Workflow

1. Bound input first. Read only explicit `@path`, exact path, supplied diff, or snippet; no broad discovery.
2. Select/dedupe slugs. Build `<slug> -> <display name>` before spawning; display name is the registry Person cell. Final names/headings use only those exact display names, never short aliases (`antirez`, `tef`, runtime nicknames).
3. Use all exposed Codex agent features, including under-development ones: `multi_agent_v2`, `enable_fanout`, `child_agents_md`, `runtime_metrics`, `list_agents`, `spawn_agent`, `wait_agent`, `followup_task`, `close_agent`. Demote only if the live loop proves harm. Never invent tools.
4. If available, call `list_agents` with no args. Use `path_prefix` only for known `/root/...` agent paths, never filesystem paths. Close only stale council reviewers. Respect `agents.max_threads`, `multi_agent_v2`, and session thread limits.
5. Fan out in waves. Never call more than 3 `spawn_agent`s in one batch; a six-reviewer roster is two waves of 3 even if capacity seems higher. Unknown capacity means one per wave. Spawn with `spawn_agent(agent_type: "<slug>", fork_turns: "none")`; lowercase task names; no model/reasoning override unless requested.
6. Each spawn/follow-up starts: `You are <display name> (<slug>) for Council. Produce the review body now; do not acknowledge, wait, or describe setup.` Then include the Assignment block. Ack retry starts: `Your previous response was ack-only and invalid. Produce the review body now.`
7. Supervise here. Any non-final status/commentary after skill load must start `Council progress:` and only mark fan-out, half returned, nudge, stall/fail, or minute tick. Loop `wait_agent(timeout_ms: 60000)`; classify reviewers as `healthy`, `drifting`, `stalled`, `blocked`, `invalid-output`, or `done`; nudge non-healthy once. Wave timeout 20m.
8. Accept only reviewer heading plus real body. Reject raw JSON/tags/tool payloads, ack/status/setup, generic `Findings:`, broad discovery, and empty output. Recover malformed near-reviews once. Drain until every selected reviewer is `accepted`, `missing`, or `failed`; close spawned reviewers after terminal handling.
9. If no reviewer launched or all fail, output exactly `Council not run: reviewer fan-out failed.` Otherwise synthesize one integrated result in your voice. Never return one reviewer payload, raw `## <reviewer> review`, runtime nickname, unregistered name, or approval-shaped wording (`APPROVED`, `NOT APPROVED`, `approved`). Say whether material blockers remain.

## Assignment

```text
<council-review-assignment>
Mode: <mode>
Review summary: <problem context>
Files: <absolute paths, or `inline material only`>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>

Rules: supplied material is full scope; inline-only is valid. Extra reads only for directly connected files already implied by the material; state gaps instead of exploring. No broad discovery, tests/builds/linters, git history, file edits, subagents, setup reports, AGENTS.md/RTK/tool summaries, readiness, or ack-only replies. First non-empty line is the reviewer heading. No generic `Findings:`, JSON/XML/status wrappers, quotes, or transport metadata.
</council-review-assignment>
```

Debate/follow-up challenges: keep same reviewers open when possible, use `followup_task`, validate every round, close after synthesis, answer one integrated addendum. If asked only for approval wording/final blessing without explicit council reassessment, output exactly `Council not run: no explicit council request.` For blocker/sign-off follow-ups, answer `material blockers remain` or `no material blockers remain`.

## Output

Use these headings exactly. Include `What changed in this follow-up` only for user-requested reruns, blocker checks, or challenges to an earlier council result; internal waves/retries/stalls are not follow-ups. No extra top-level sections.

```markdown
# Council review: <topic>
<One sentence: `material blockers remain:` or `no material blockers remain:`.>
## What changed in this follow-up
<Only for reruns, blocker checks, or challenges to a prior council claim.>
## Convergence (high-confidence signals)
<2-5 bullets, each ending with reviewer names.>
## Disagreement (real tradeoffs the user must decide)
<2-4 bullets comparing reviewer positions.>
## Per-reviewer top-3
<For each accepted reviewer, heading `### <exact display name>` plus 3 concrete bullets.>
## What to do next
<3-7 numbered actions, smallest first.>
## What we did not address
<1-3 explicit gaps.>
```

Private dossiers are aids only; never republish them wholesale.
