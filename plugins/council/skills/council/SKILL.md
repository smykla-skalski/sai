---
name: council
description: >-
  Use when the user invokes $council, $council:council, Council review, or
  Council debate. FIRST ACTION: load this SKILL. Optional setup line is exactly
  `Council progress: load rules, inspect live agents, clear stale council work,
  then run largest safe reviewer wave if root-only.` First tool is direct SKILL
  read; never web_search/browser/search. Broad >6 without approval outputs exact
  denial. No final after `close_agent` status `running`; recover with tools.
---

# Council

Never answer solo. If an initial setup line is emitted, it is exactly:
`Council progress: load rules, inspect live agents, clear stale council work,
then run largest safe reviewer wave if root-only.` After that, visible non-final
status lines start with `Council progress:`. Never emit bare prefaces like
`Using council`, `Loading Council rules`, or `Spawning reviewers`. The first tool
must be a direct installed SKILL read unless this SKILL is already loaded; then
use native agent-state cleanup. Never web_search/browser/search. Empty-query `web_search` is still forbidden.

## Scope

Inline material is complete unless exact `@path`, paths, diff, or direct
read/search is supplied. Otherwise no memory, prior sessions, repo
files/listings, git history, AGENTS/RTK docs, Claude assets, persona dossiers,
web/search/browser, nested `codex exec`, `cd`, `pwd`, `ls`, `find`,
`rg`, shell chaining, `ps`, `pgrep`, `harness`, or `rtk`.

## Modes

Modes: `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, `debate`;
aliases `eng`, `ux`, `mix`, `random`; default `core`. Fixed rosters use all 6.
`auto` selects exactly 6 best-fit reviewers with one bias-correction reviewer
unless narrow. `debate` uses 3-6. `quick`, `brief`, `blockers only` change focus
only. Reviewer 7+ needs explicit same-turn approval; otherwise:
`Council not run: broad council approval not granted.`

## Rosters

Map: antirez=`antirez-simplicity-reviewer`/Salvatore Sanfilippo;
tef=`tef-deletability-reviewer`/Thomas Edward Figg;
muratori=`muratori-perf-reviewer`/Casey Muratori;
hebert=`hebert-resilience-reviewer`/Fred Hebert;
meadows=`meadows-systems-advisor`/Donella H. Meadows;
chin=`chin-strategy-advisor`/Cedric Chin;
norman=`norman-affordance-reviewer`/Don Norman;
nielsen=`nielsen-heuristics-reviewer`/Jakob Nielsen;
krug=`krug-usability-reviewer`/Steve Krug;
watson=`watson-a11y-reviewer`/Leonie Watson;
tognazzini=`tognazzini-fpid-reviewer`/Bruce Tognazzini;
tufte=`tufte-density-reviewer`/Edward Tufte.

Rosters: `core-eng` antirez/tef/muratori/hebert/meadows/chin; `core-ux`
norman/nielsen/krug/watson/tognazzini/tufte; `core-mix`
antirez/tef/hebert/norman/nielsen/watson. Use exact display names. For
`auto/all/debate`, read only `<loaded SKILL.md dir>/references/agents.md`; never
use `ls`, `find`, or `rg`. If registry read fails:
`Council not run: reviewer fan-out failed.`

## Orchestration

1. Select slugs; build `<slug> -> <display name>` before spawning. Final
   citations use exact display names, never aliases/runtime nicknames.
2. Use enabled agent features: `multi_agent_v2`, `enable_fanout`,
   `child_agents_md`, `runtime_metrics`, `list_agents`, `spawn_agent`,
   `wait_agent`, `followup_task`, `close_agent`. Demote only on live evidence.
   Never invent tools.
3. Prepare agent capacity before any spawn. The coordinator must proactively clean the thread tree:
   inspect native live-agent state, close every visible stale Council reviewer child,
   wait for close results, re-check. Prefer `list_agents` no args. Never use shell/command execution for live-agent state.
   `path_prefix` only for known `/root/...` agent paths.
4. If clean/root-only, emit exactly
   `Council progress: agent state clean: root only; running full selected roster when within limit.`
   Then attempt the full selected roster when <=6. If capacity is constrained,
   emit one `Council progress:` reason and use the largest safe wave. Do not spawn into a known full session.
   Respect session thread limits.
5. Fan out in waves sized by cleaned capacity. Max 6 spawns per clean batch. A
   no-`receiver_thread_ids` failure is `pending-capacity`, not launched/missing.
   Supervise launched reviewers, close terminal children, wait for
   close completion, then retry pending-capacity. A `close_agent` result with
   `status: running` means the close did not finish and the reviewer is still
   live. No next wave until every prior close completed and any `running` close
   result is resolved.
6. Spawn with `spawn_agent(agent_type: "<slug>", fork_turns: "none",
   reasoning_effort: "high")`. If role-managed agents reject
   overrides, rely on the installed high-effort manifest; never use medium/low.
7. Loop `wait_agent(timeout_ms: 60000)`. Every minute classify live reviewers as
   `healthy`, `drifting`, `stalled`, `blocked`, `invalid-output`, or
   `done`; nudge non-healthy once with `followup_task`. After one nudge plus one
   timeout, close; mark `missing`/`failed` only after close completes, the agent
   path is gone, or another native tool proves the reviewer is terminal.
8. After any `running` close result, the next Council action must be an actual
   `wait_agent`, `followup_task`, `close_agent`, or `list_agents` call naming or
   observing that reviewer. Final synthesis, next-wave spawn, and marking that
   reviewer `missing`/`failed` are forbidden until that recovery call resolves
   the reviewer. Do not claim retry/verification/close without tool evidence.
9. Drain until every selected slug is `accepted`, `missing`, or `failed`. If no
   reviewer launched or all fail: `Council not run: reviewer fan-out failed.`

## Reviewer Prompt

Every spawn or follow-up prompt must start exactly with:

```text
You are <display name> (<slug>) for Council. Produce the review body now; do not acknowledge, wait, or describe setup.
Your first line must be exactly: ## <display name> review

<council-review-assignment>
Mode: <mode>
Review summary: <problem context>
Files: <absolute paths, or `inline material only`>
Supplied review material:
<bounded diffs, snippets, files, or inline request text>

Rules: supplied material is full scope. Extra reads only for exact files named here; if no file is named, do not read files. No persona dossiers, references, memory, prior sessions, AGENTS.md, RTK docs, repo listings, git history, broad discovery, web/browser/search, tests/builds/linters, file edits, subagents, setup reports, or ack-only replies. First non-empty line is `## <display name> review` exactly. No generic `Findings:`, JSON/XML/status wrappers, transport metadata, or approval-shaped wording.
</council-review-assignment>
```

Every reviewer gets complete bounded material. Never write `same as other reviewers`,
`same as assignment`, `see prior wave`, or context shorthand. Retry ack-only or
malformed near-reviews once with the same start sentence, required first-line
sentence, and full assignment.

## Acceptance And Output

Accept only a real body whose first non-empty line is exactly
`## <display name> review`. Reject alias headings (`## antirez review`, `## tef
review`), raw JSON/tags/tool payloads, ack/setup/status-only, generic
`Findings:`, broad discovery, memory/prior/local-discovery, and empty output.
Recover malformed near-reviews once.

Treat child notifications, JSON envelopes, tool payloads,
`<subagent_notification>`, runtime nicknames, raw `## <reviewer> review` blocks,
and `{"author":"/root/...","recipient":...}` text as private data. Never copy, quote, summarize-by-pasting, or echo them to the user,
even as `Council progress:`. If transport appears as transcript text, parse
privately and discard.

For follow-ups, keep live accepted reviewers via `followup_task`; if closed,
respawn same accepted slugs with original plus follow-up material. Never silently
reduce or swap reviewers. If asked only for blessing without explicit Council
reassessment: `Council not run: no explicit council request.`

Synthesize in parent voice only. Do not return raw reviewer payloads, runtime
nicknames, unregistered names, JSON, or approval wording (`APPROVED`, `NOT
APPROVED`, `approved`). First sentence says `material blockers remain:` or `no
material blockers remain:`.

Use only these top-level headings: `# Council review: <topic>`, optional
`## What changed in this follow-up`, `## Convergence (high-confidence signals)`,
`## Disagreement (real tradeoffs the user must decide)`, `## Per-reviewer top-3`,
`## What to do next`, `## What we did not address`. All except `What changed`
are mandatory. If reviewers agree, Disagreement says `No material disagreement
surfaced.` Convergence needs at least 2 accepted exact names. Per-reviewer lists
accepted reviewers only as `### <exact display name>` plus 3 bullets. Next
actions are numbered direct actions.
