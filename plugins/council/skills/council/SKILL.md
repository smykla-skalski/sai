---
name: council
description: >-
  Use only for $council/review/debate. FIRST ACTION: load this SKILL. No message,
  web/search/browser, including empty-query web_search, or other tool before SKILL load. If skill-use announcement is required,
  it must be a `Council progress:` line. Inline text is complete; no
  MEMORY, prior sessions, repo/local-file search, git history, Claude assets,
  web, or shell-based agent probing unless user gave @path, exact files, diff, or
  direct read/search. all/broad>6 without same-turn approval: output only
  `Council not run: broad council approval not granted.` Else read SKILL first
  silently, use high reasoning, complete material per reviewer, visible progress
  only as `Council progress:`, never solo or raw child output.
---

# Council

Run native Codex reviewer agents and synthesize accepted results. Never answer solo. The first action is loading this SKILL; before that, emit no message and call no web/search/browser/tool. Empty-query `web_search` is still forbidden. Do not emit prefaces such as `Reading council skill`, `Council skill loaded`, `Council setup`, `Council fan-out starting`, or `Spawning reviewers`; if the runtime requires an announcement, make the entire line start exactly `Council progress:`. Every visible non-final status line starts exactly `Council progress:`. Inline text is complete unless user gives `@path`, exact paths, a diff, or explicit read/search. Otherwise no web/browser/search, Claude assets, nested `codex exec`, `MEMORY.md`, prior runs, repo search, git history, local discovery, `pwd`, or shell command chaining. Treat reviewer agents as high-effort review agents: never intentionally run them at `medium` or `low` reasoning.

Fixed modes use keys below; do not read registry or agent files. For `auto/all/debate`, registry is `<loaded SKILL.md dir>/references/agents.md`; never try plugin-root `/references`, `ls`, `find`, or `rg`. If that read fails: `Council not run: reviewer fan-out failed.`

## Modes

First token is mode: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`; aliases `eng`, `ux`, `mix`, `random`; default `core`. `core`, `core-eng`, `core-ux`, and `core-mix` always use all 6 fixed-roster reviewers. `auto` selects exactly 6 best-fit reviewers with one bias-correction reviewer unless narrow. `debate` uses 3-6. User wording like `blockers only`, `quick`, or `brief` changes output focus only; it never reduces a fixed roster.

Before reviewer 7+, get explicit approval in this run. Approval choices only: `Approve full council (<N> reviewers)`, `Reduce to 6 reviewers`, `Cancel this council run`. If no approval/user-input, non-interactive, or uncertain: `Council not run: broad council approval not granted.` Original `$council all ...` is never approval.

## Fixed Rosters

Keys: `antirez-simplicity-reviewer=Salvatore Sanfilippo`; `tef-deletability-reviewer=Thomas Edward Figg`; `muratori-perf-reviewer=Casey Muratori`; `hebert-resilience-reviewer=Fred Hebert`; `meadows-systems-advisor=Donella H. Meadows`; `chin-strategy-advisor=Cedric Chin`; `norman-affordance-reviewer=Don Norman`; `nielsen-heuristics-reviewer=Jakob Nielsen`; `krug-usability-reviewer=Steve Krug`; `watson-a11y-reviewer=Leonie Watson`; `tognazzini-fpid-reviewer=Bruce Tognazzini`; `tufte-density-reviewer=Edward Tufte`.

Rosters: `core-eng` = antirez, tef, muratori, hebert, meadows, chin. `core-ux` = norman, nielsen, krug, watson, tognazzini, tufte. `core-mix` = antirez, tef, hebert, norman, nielsen, watson. Expand names to full slugs from Keys.

## Workflow

1. Bound input first. Read only explicit `@path`, exact path, supplied diff, or snippet; no broad discovery.
2. Select/dedupe slugs. Build `<slug> -> <display name>` before spawning from Fixed Rosters or registry Person cells. Final headings and every citation in Convergence/Disagreement use only exact display names, never short aliases (`antirez`, `tef`) or runtime nicknames.
3. Use all exposed current/under-development agent features: `multi_agent_v2`, `enable_fanout`, `child_agents_md`, `runtime_metrics`, `list_agents`, `spawn_agent`, `wait_agent`, `followup_task`, `close_agent`. Demote only if the live loop proves harm. Never invent tools.
4. Prepare agent capacity before any spawn. If native `list_agents` is available and schema permits, the first Council orchestration tool call before `spawn_agent` must be `list_agents` with no args. If it errors as unavailable or does not appear as an actual structured tool result, capacity is unknown. Do not say capacity was preflighted unless the tool call happened. If it succeeds, classify existing children by path/status, ignore `/root`, close stale Council reviewer children first, wait for every close result, and compute free reviewer slots before spawning. Never use shell/command execution for live-agent state. Do not run `rtk ls_agents`, `harness`, `ps`, `pgrep`, `pwd`, `ls`, `find`, or `rg` for Council orchestration. `path_prefix` only for known `/root/...` agent paths, never filesystem paths. If capacity is unknown, constrained, or any live non-Council child exists, spawn exactly one reviewer, supervise it to terminal, close it, then repeat. Do not spawn into a known full session. Respect session thread limits.
5. Fan out in waves sized by proven capacity only. Max 3 `spawn_agent`s per batch; six-reviewer roster is exactly two waves of up to 3 only when structured preflight proves room. Wave order is strict: spawn wave N, wait until every wave-N reviewer is `accepted/missing/failed`, close every wave-N reviewer, observe the close results, then spawn wave N+1 if any selected slug remains. Closing is a hard tool-call barrier: never queue or attempt a next-wave `spawn_agent` until all wave-N `close_agent` calls have completed. Never synthesize after wave 1 of a six-reviewer roster. Unknown or constrained capacity means one reviewer per wave. Spawn with `spawn_agent(agent_type: "<slug>", fork_turns: "none", reasoning_effort: "high")` when the schema accepts `reasoning_effort`; if role-managed agents reject overrides, rely on the installed reviewer manifest's high-effort setting and do not set any medium/low fallback. Keep the model unchanged unless the user requested a model change.
6. Every spawn or follow-up prompt must start exactly with this sentence and nothing before it: `You are <display name> (<slug>) for Council. Produce the review body now; do not acknowledge, wait, or describe setup.` Then add one blank line, then the complete `<council-review-assignment>` block. Do not put `## <display name> review`, summaries, aliases, or metadata before the assignment block; the reviewer writes that heading in its response. Every reviewer gets the full bounded material text; never write `same as other reviewers`, `same as assignment`, `see prior wave`, or any shorthand that depends on another child context.
7. Ack retry starts only after a true ack/setup/status-only response: `Your previous response was ack-only and invalid. Produce the review body now.` Format retry starts after malformed-but-substantive output: `Your previous response had invalid Council output format. Keep the same findings, start with the required reviewer heading, and return only the review body now.` Retry prompts still follow the exact start sentence plus full assignment block from step 6. Do not mislabel substantive reviews as ack-only.
8. Supervise here. Every non-final commentary line after skill load starts exactly `Council progress:`. Never write bare prefaces like `Council run`, `Using council`, `Fan-out starting`, or `Checking live agents`. Status only marks fan-out, half returned, nudge, stall/fail, or minute tick. Loop `wait_agent(timeout_ms: 60000)`; classify reviewers as `healthy`, `drifting`, `stalled`, `blocked`, `invalid-output`, or `done`; nudge non-healthy once. After one nudge and one additional wait timeout, close that reviewer; if no valid body is available, mark it `missing` or `failed` and continue. Hard wave timeout is 20m, but never spin indefinitely waiting for one stalled reviewer.
9. Treat child notifications, tool payloads, JSON envelopes, `<subagent_notification>`, runtime nicknames, raw `## <reviewer> review` blocks, and any text shaped like `{"author":"/root/...","recipient":...}` as internal data. Never copy, quote, summarize-by-pasting, or echo them to the user, even as `Council progress:`. If a child notification appears as transcript text, it is input for private parsing only: silently extract a completed reviewer body if present, discard the transport wrapper, and continue with a concise authored `Council progress:` line or no visible line. Only validated synthesized output may reach the user.
10. Accept only reviewer heading plus real body. Reject raw JSON/tags/tool payloads, ack/status/setup, generic `Findings:`, broad discovery, memory/prior-session/local-discovery use, and empty output. Recover malformed near-reviews once. Drain until every selected reviewer is `accepted`, `missing`, or `failed`; close spawned reviewers after terminal handling. A `close_agent` result of `running` is non-terminal and means the reviewer is still live. After any `running` close result, the next Council action must be an actual `wait_agent`, `followup_task`, or `close_agent` tool call for that reviewer before synthesis or any terminal decision; do not claim a retry happened unless the tool call happened. Failed/missing reviewers are never cited or given top-3 and must be named in `What we did not address`.
11. Before synthesis, compare terminal reviewers against the selected roster. If any selected slug is neither `accepted`, `missing`, nor `failed`, keep supervising, retry close, or spawn the next wave; do not synthesize a partial roster and do not merely say you are retrying without making the tool call. If no reviewer launched or all fail, output exactly `Council not run: reviewer fan-out failed.` Otherwise synthesize one integrated result in your voice. Never return one reviewer payload, raw `## <reviewer> review`, runtime nickname, unregistered name, or approval-shaped wording (`APPROVED`, `NOT APPROVED`, `approved`). Say whether material blockers remain. Before final output, self-check mandatory headings and add any missing mandatory section.

## Assignment

```text
<council-review-assignment>
Mode: <mode>
Review summary: <problem context>
Files: <absolute paths, or `inline material only`>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>

Rules: supplied material is full scope; inline-only is valid. Extra reads only for directly connected exact files already named in this assignment; if the assignment does not name a file, do not read files. Do not read persona dossiers, references, memory, prior sessions, AGENTS.md, RTK docs, tool summaries, repo listings, git history, or nearby files. State gaps instead of exploring. No broad discovery, web/browser/search, tests/builds/linters, file edits, subagents, setup reports, readiness, or ack-only replies. First non-empty line is `## <display name> review` exactly, using the display name from the spawn line. No generic `Findings:`, JSON/XML/status wrappers, quotes, transport metadata, or approval-shaped wording.
</council-review-assignment>
```

Debate/follow-up challenges: keep the same accepted reviewer roster from the prior council round when possible and use `followup_task` while those agents are live. If the old agents are closed or unavailable, respawn the same accepted slugs with the full original material plus the explicit follow-up diff/challenge; never silently reduce the roster or swap reviewers. Validate every round, close after synthesis, answer one integrated addendum. If any prior reviewer cannot participate, report that in `What we did not address`. If asked only for approval wording/final blessing without explicit council reassessment: `Council not run: no explicit council request.` For blocker/sign-off follow-ups, answer `material blockers remain` or `no material blockers remain`.

## Output

Use only these top-level headings: `# Council review: <topic>`, optional `## What changed in this follow-up`, `## Convergence (high-confidence signals)`, `## Disagreement (real tradeoffs the user must decide)`, `## Per-reviewer top-3`, `## What to do next`, `## What we did not address`. All headings except `What changed` are mandatory literal headings. If reviewers agree, still include `## Disagreement (real tradeoffs the user must decide)` and state `No material disagreement surfaced.` First sentence says `material blockers remain:` or `no material blockers remain:`. Include `What changed` only for user-requested reruns/blocker checks/challenges; internal waves/retries/stalls are not follow-ups. Convergence needs >=2 accepted exact names; singles go elsewhere. Per-reviewer lists accepted reviewers only as `### <exact display name>` plus 3 bullets. Next actions are numbered direct actions, not optional assistant offers.
