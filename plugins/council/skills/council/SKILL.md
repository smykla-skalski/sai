---
name: council
description: >-
  Use when user asks $council/review/debate. Inline means no MEMORY/prior/repo
  lookup before SKILL. If all/broad>6 lacks approval: no tools/commentary; output
  only `Council not run: broad council approval not granted.` Else read SKILL,
  spawn reviewers, never solo.
---

# Council

Run native Codex reviewer agents and synthesize accepted results. Never answer solo. Inline text is complete unless user gives `@path`, exact paths, a diff, or explicit read/search. Otherwise no web/browser/search, Claude assets, nested `codex exec`, `MEMORY.md`, prior runs, repo search, git history, local discovery, `pwd`, or shell command chaining.

Fixed modes use keys below; do not read registry or agent files. For `auto/all/debate`, registry is `<loaded SKILL.md dir>/references/agents.md`; never try plugin-root `/references`, `ls`, `find`, or `rg`. If that read fails: `Council not run: reviewer fan-out failed.`

## Modes

First token is mode: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`; aliases `eng`, `ux`, `mix`, `random`; default `core`. `core` chooses one fixed roster. `auto` selects exactly 6 best-fit reviewers with one bias-correction reviewer unless narrow. `debate` uses 3-6.

Before reviewer 7+, get explicit approval in this run. Approval choices only: `Approve full council (<N> reviewers)`, `Reduce to 6 reviewers`, `Cancel this council run`. If no approval/user-input, non-interactive, or uncertain: `Council not run: broad council approval not granted.` Original `$council all ...` is never approval.

## Fixed Rosters

Keys: `antirez-simplicity-reviewer=Salvatore Sanfilippo`; `tef-deletability-reviewer=Thomas Edward Figg`; `muratori-perf-reviewer=Casey Muratori`; `hebert-resilience-reviewer=Fred Hebert`; `meadows-systems-advisor=Donella H. Meadows`; `chin-strategy-advisor=Cedric Chin`; `norman-affordance-reviewer=Don Norman`; `nielsen-heuristics-reviewer=Jakob Nielsen`; `krug-usability-reviewer=Steve Krug`; `watson-a11y-reviewer=Leonie Watson`; `tognazzini-fpid-reviewer=Bruce Tognazzini`; `tufte-density-reviewer=Edward Tufte`.

Rosters: `core-eng` = antirez, tef, muratori, hebert, meadows, chin. `core-ux` = norman, nielsen, krug, watson, tognazzini, tufte. `core-mix` = antirez, tef, hebert, norman, nielsen, watson. Expand names to full slugs from Keys.

## Workflow

1. Bound input first. Read only explicit `@path`, exact path, supplied diff, or snippet; no broad discovery.
2. Select/dedupe slugs. Build `<slug> -> <display name>` before spawning from Fixed Rosters or registry Person cells. Final headings and every citation in Convergence/Disagreement use only exact display names, never short aliases (`antirez`, `tef`) or runtime nicknames.
3. Use all exposed current/under-development agent features: `multi_agent_v2`, `enable_fanout`, `child_agents_md`, `runtime_metrics`, `list_agents`, `spawn_agent`, `wait_agent`, `followup_task`, `close_agent`. Demote only if the live loop proves harm. Never invent tools.
4. If available and schema permits, call `list_agents` with no args; if that errors, skip it. `path_prefix` only for known `/root/...` agent paths, never filesystem paths. Close only stale council reviewers. Respect session thread limits.
5. Fan out in waves. Max 3 `spawn_agent`s per batch; six-reviewer roster is two waves of 3. Wave order is strict: spawn wave N, wait until every wave-N reviewer is `accepted/missing/failed`, close every wave-N reviewer, then and only then spawn wave N+1. Unknown capacity means one per wave. Spawn with `spawn_agent(agent_type: "<slug>", fork_turns: "none")`; lowercase task names; no model/reasoning override unless requested.
6. Each spawn/follow-up starts: `You are <display name> (<slug>) for Council. Produce the review body now; do not acknowledge, wait, or describe setup.` Then include the Assignment block. Ack retry starts: `Your previous response was ack-only and invalid. Produce the review body now.`
7. Supervise here. Non-final status after skill load must start `Council progress:`. Never write prefaces like `Using council`, `Fan-out starting`, or `Checking live agents`. Status only marks fan-out, half returned, nudge, stall/fail, or minute tick. Loop `wait_agent(timeout_ms: 60000)`; classify reviewers as `healthy`, `drifting`, `stalled`, `blocked`, `invalid-output`, or `done`; nudge non-healthy once. Wave timeout 20m.
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

Debate/follow-up challenges: keep same reviewers when possible, use `followup_task`, validate every round, close after synthesis, answer one integrated addendum. If asked only for approval wording/final blessing without explicit council reassessment: `Council not run: no explicit council request.` For blocker/sign-off follow-ups, answer `material blockers remain` or `no material blockers remain`.

## Output

Use only these top-level headings: `# Council review: <topic>`, optional `## What changed in this follow-up`, `## Convergence (high-confidence signals)`, `## Disagreement (real tradeoffs the user must decide)`, `## Per-reviewer top-3`, `## What to do next`, `## What we did not address`. All headings except `What changed` are mandatory. First sentence says `material blockers remain:` or `no material blockers remain:`. Include `What changed` only for user-requested reruns/blocker checks/challenges; internal waves/retries/stalls are not follow-ups. Convergence bullets end with exact display names. Per-reviewer uses `### <exact display name>` plus 3 bullets. Next actions are numbered.

Private dossiers are aids only.
