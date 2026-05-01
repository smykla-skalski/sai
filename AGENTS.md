# SAI agent instructions

This repo packages agent skills and plugins for Claude Code, Copilot CLI, and Codex.

## Validation

There is no repo-level build, test, or lint entrypoint.
Do not add placeholder `mise`, `make`, or lint tasks.
Validate the exact runtime surface you changed.

- Claude plugin smoke: `claude --plugin-dir claude/{plugin-name}/`
- Copilot council smoke: `copilot plugin install /absolute/path/to/sai/plugins/council`, then run `/council ...`
- Codex council smoke: push/release the bumped Git marketplace plugin, run `codex plugin marketplace upgrade sai`, then run `$council ...` from the real target repository
- Script-heavy changes: run the local checker/schema/smoke flow that belongs to that skill

## Codex council improvement loop

Use this loop for functional Codex changes under `plugins/council/`, `codex/agents/`, or Codex marketplace metadata:

1. Read `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and the Codex-facing files you are changing.
2. Check version drift before editing: `plugins/council/plugin.json`, `plugins/council/.codex-plugin/plugin.json`, installed cache under `~/.codex/plugins/cache/sai/council/`, and README references.
3. Change the complete Codex surface, not only one file: `plugins/council/skills/council/SKILL.md`, `plugins/council/.codex-plugin/plugin.json`, relevant `plugins/council/agents/*.agent.md`, marketplace metadata, and README when behavior changes. `plugins/council/skills/council/` is the only Codex skill root; do not add a parallel `codex-skills/` tree.
4. Keep the strict bounded-context and stop-output rules in the first metadata Codex sees, not only in the SKILL body. The skill frontmatter description and `.codex-plugin/plugin.json` summary must say that inline text is complete, Council must not search memory, repos, git history, prior sessions, Claude assets, or local files unless the user supplied `@path`, exact files, a diff, or a direct instruction, and broad runs above 6 without approval must output exactly `Council not run: broad council approval not granted.`
5. For functional Codex skill/plugin changes, bump the Codex plugin version in `plugins/council/.codex-plugin/plugin.json` in the same commit. Keep package versions intentionally aligned unless there is a documented reason not to.
6. Commit the implementation first with `git commit -sS` before starting the live improvement loop.
7. Release through the real marketplace path: push the signed commit, keep the `sai` marketplace configured as a Git marketplace, run `codex plugin marketplace upgrade sai`, then verify `~/.codex/plugins/cache/sai/council/<version>/` contains the bumped version and the changed skill text. Do not switch `sai` to a local marketplace path for validation; local-path registration can leave the versioned cache stale and cannot be upgraded with `codex plugin marketplace upgrade`.
8. Check the local Codex feature surface before live validation: `codex --version` and `codex features list`. Enabled under-development features are in scope, not optional. When `multi_agent_v2`, `enable_fanout`, `child_agents_md`, or `runtime_metrics` are enabled, install and test the skill with those paths active instead of only the legacy single-agent path. Reviewer agents must run at high reasoning effort wherever the agent surface supports it; do not leave Council reviewer definitions at `medium` unless the live improvement loop proves high has a negative impact and the evidence is recorded. Demote a feature only when the improvement loop proves a negative impact, and record the evidence.
9. Use the cheapest practical model for repeated validation and smoke loops. Escalate only when the cheap model cannot diagnose or reproduce a real failure.
10. Run Codex validations from the real target repository/cwd when behavior depends on repo context, not from `sai`.
11. Exercise the actual Council paths:
   - normal `$council ...`
   - `$council:council ...` or equivalent plugin-prefixed alias when available
   - broad `$council all ...` stop/approval behavior
   - follow-up challenge via actual Codex resume/thread continuation, not a fresh fake session
   - stalled reviewer recovery, reviewer nudging, and raw reviewer output rejection
12. Inspect Codex session artifacts and installed plugin files to prove what happened: agents-v2/fan-out path was used when available, subagents spawned, every fixed-roster mode ran all 6 selected reviewers rather than stopping after the first wave, every reviewer received the full bounded material rather than shorthand such as `same as other reviewers`, reviewer agents did not read memory, prior sessions, persona dossiers, git history, broad repo context, or local discovery surfaces outside exact assignment paths, parent stayed alive after fan-out, `wait_agent`/`followup_task` supervision happened without invalid `list_agents` filesystem prefixes, liveness chatter used `Council progress:`, runtime child nicknames did not leak as reviewer identities, raw reviewer blocks stayed internal, and final output used every mandatory Council heading as integrated synthesis.
13. Treat Codex hooks as lifecycle guardrails only. Do not rely on hooks for council orchestration or pre-tool enforcement.
14. If validation exposes a prompt or packaging bug, patch it, bump again, commit again with `git commit -sS`, reinstall that bumped version, and rerun the relevant live checks.
15. Improvement-loop order is correctness first, score second. First find a working Council behavior even if the skill is verbose, token-expensive, or scores worse in plugin-eval. Only after live validation proves the behavior works should you run score/token-pressure passes that make the skill less verbose.

### Canonical Codex council runbook

For every Codex Council improvement loop, open and follow
`runbooks/codex-council-improvement-loop.md`. That runbook is the canonical
process for release, installed-cache proof, live smoke checks, evidence capture,
and the formal working-before-scoring rule. Do not rediscover equivalent CLI
syntax, validate through a local marketplace path, or run score/verbosity
optimization before the runbook's working-proof phase passes.

## Codex council behavior contract

- Council is opt-in review work, not a generic commit, pre-commit, or approval gate.
- Codex Council uses native `spawn_agent` reviewer agents. Use all relevant current agent features, including enabled under-development agents-v2/fan-out features; do not run nested `codex exec`.
- Broad runs above 6 reviewers require explicit current-run approval. If approval is unavailable, stop with exactly `Council not run: broad council approval not granted.`
- Reviewer fan-out is not completion. The orchestrator must keep supervising until every selected reviewer is accepted, failed, or missing.
- Fixed-roster modes (`core`, `core-eng`, `core-ux`, `core-mix`) always run all 6 selected reviewers. Output-focus wording such as `blockers only` must not shrink the roster or skip the second wave.
- Wave boundaries are hard barriers. Close every terminal reviewer from the current wave and observe the close results before spawning any next-wave reviewer, so the run does not hit thread limits.
- Every selected reviewer must receive the complete bounded material in its own spawn or follow-up prompt. The prompt starts with `You are <display name> (<slug>) for Council...`, then the assignment block; do not put reviewer headings or metadata before that. Do not rely on child agents sharing context, and never send `same as other reviewers`, `same as assignment`, or `see prior wave`.
- Final synthesis must include every mandatory Council heading, including `## Disagreement (real tradeoffs the user must decide)` even when the section says no material disagreement surfaced.
- Follow-up challenge and blocker-check rounds keep the same accepted reviewer roster where possible. If agents are already closed, respawn the same slugs with the original material plus the follow-up diff/challenge; never silently reduce or swap the roster.
- At least once per minute, classify every live reviewer as `healthy`, `drifting`, `stalled`, `blocked`, or `done`; nudge non-healthy reviewers in that same pass. After one nudge plus one more wait timeout, close or mark the reviewer missing/failed instead of spinning indefinitely.
- Sparse `Council progress:` updates are allowed when they prove the run is alive. Do not leak reviewer drafts, transport payloads, raw `<subagent_notification>` text, raw JSON envelopes, or raw `## <reviewer> review` blocks.

## Commit rules

- Use conventional commits: `type(scope): description`.
- Every commit must use `git commit -sS`.
- Verify signed commits when commit metadata is in scope.
- Do not edit `.github/workflows/`; those workflows are org-synced.
- Do not add inline linter suppressions or relax lint config without explicit user approval after first investigating a real fix.
