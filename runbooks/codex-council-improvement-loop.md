# Codex Council Improvement Loop Runbook

This is the canonical process for functional Codex Council changes under
`plugins/council/`, `codex/agents/`, or Codex marketplace metadata.

Do not validate through a local marketplace path. Do not rediscover equivalent
CLI syntax during the loop. Do not optimize plugin-eval score, brevity, token
footprint, or elegance until the installed-plugin working-proof phase passes.

Run all commands from the `sai` repo root.

## Phase 0: Set Variables

```sh
VERSION=$(./runbooks/codex_council_loop.py version)
: "${TARGET_REPO:?set absolute path to the real target repo}"
EVIDENCE_DIR=tmp/council-validation/$VERSION
```

Use the real target repository for live Codex validation, not `sai`, when behavior
depends on repo context.

## Phase 1: Baseline And Drift Check

```sh
./runbooks/codex_council_loop.py baseline
sed -n '1,180p' README.md CLAUDE.md CONTRIBUTING.md
```

Check version drift across `plugins/council/plugin.json`,
`plugins/council/.codex-plugin/plugin.json`, installed cache under
`~/.codex/plugins/cache/sai/council/`, and README references when behavior docs
change.

## Phase 2: Edit Complete Codex Surface

For functional Codex behavior changes, update the complete surface:

- `plugins/council/skills/council/SKILL.md`
- `plugins/council/.codex-plugin/plugin.json`
- `plugins/council/plugin.json`
- relevant `plugins/council/agents/*.agent.md`
- relevant `codex/agents/*.toml`
- marketplace metadata when applicable
- `AGENTS.md` or this runbook when the process changes

`plugins/council/skills/council/` is the only Codex skill root. Do not add a
parallel `codex-skills/` tree.

Keep strict bounded-context and stop-output rules in the first metadata Codex
sees, not only in the skill body. The skill frontmatter description and
`.codex-plugin/plugin.json` summary must say that inline text is complete, Council
must not search memory, repos, git history, prior sessions, Claude assets, or
local files unless the user supplied `@path`, exact files, a diff, or a direct
instruction, and broad runs above 6 without approval must output exactly:

```text
Council not run: broad council approval not granted.
```

## Phase 3: Static Validation Before Commit

```sh
./runbooks/codex_council_loop.py static
```

Functional Codex skill/plugin changes must bump the Codex plugin version in
`plugins/council/.codex-plugin/plugin.json` in the same commit. Keep package
versions aligned unless there is a documented reason not to.

## Phase 4: Commit Before Live Loop

```sh
git commit -sS -m "fix(council): <short behavior summary>"
git log -1 --show-signature --format=fuller --stat
git verify-commit HEAD
```

## Phase 5: Push And Install Real Marketplace Version

```sh
git push
codex plugin marketplace upgrade sai
```

Do not switch `sai` to a local marketplace path for validation. Local-path
registration can leave the versioned cache stale and cannot be upgraded with
`codex plugin marketplace upgrade`.

## Phase 6: Installed-Cache And Feature Proof

```sh
./runbooks/codex_council_loop.py installed "$VERSION"
codex --version
codex features list
```

Enabled under-development features are in scope, not optional. When
`multi_agent_v2`, `enable_fanout`, `child_agents_md`, or `runtime_metrics` are
enabled, install and test the skill with those paths active instead of only the
legacy single-agent path. Reviewer agents must run at high reasoning effort
wherever the agent surface supports it. Demote a feature or high reasoning only
when the live loop proves negative impact, and record the evidence.

## Phase 7: Live Working-Proof Smoke

```sh
./runbooks/codex_council_loop.py smoke "$TARGET_REPO" "$EVIDENCE_DIR"
./runbooks/codex_council_loop.py evidence "$EVIDENCE_DIR"
```

The smoke command writes `normal`, `prefixed`, `broad`, and `followup` JSONL/final
files under `$EVIDENCE_DIR`. It is fail-fast: each phase is validated immediately
after it runs, and the helper stops at the first evidence failure before spending
tokens on later phases. The helper also terminates a running `codex exec` early
when the JSONL stream exposes a first-order violation such as pre-skill chatter,
chained/discovery shell commands, forbidden search/browser tools, or raw child
transport leakage. It uses the regular fixed reviewer flow (`core-mix`, 6
reviewers). After stale-agent cleanup and a clean/root-only state, the normal path
attempts the 6-reviewer wave first, then retries no-receiver capacity misses in a
later wave if the runtime enforces a smaller effective child limit. The helper
resumes the normal smoke session by exact session id for the follow-up challenge;
do not replace that with `--last`.

The live smoke must exercise:

- normal `$council core-mix ...` with the regular fixed reviewer roster
- `$council:council core-mix ...` or equivalent plugin-prefixed alias with the regular fixed reviewer roster when available
- broad `$council all ...` stop/approval behavior
- follow-up challenge through actual Codex resume/thread continuation, not a fresh fake session
- stalled reviewer recovery, reviewer nudging, and raw reviewer output rejection when a change touches supervision

Required evidence:

- native `list_agents` capacity preflight happened before any reviewer spawn when the tool was available
- the coordinator proactively inspected the native thread tree, closed every visible stale Council reviewer child, re-checked state, and only then attempted the full 6-or-fewer roster from clean/root-only state
- any `spawn_agent` failure with no `receiver_thread_ids` was treated as pending capacity work with no slot to clean, then retried after launched reviewers closed
- native reviewer `spawn_agent` calls happened
- `wait_agent` and `followup_task` supervision happened when needed
- all selected reviewers were accepted, failed, or explicitly reported missing
- every visible non-final status line started with exact `Council progress:`
- no shell command was used for live-agent probing or Council orchestration
- every reviewer spawn/follow-up prompt started with the exact `You are ... for Council` sentence, one blank line, and then the assignment block
- every reviewer prompt carried complete bounded material
- no reviewer prompt used `same as other reviewers`, `same as assignment`, or `see prior wave`
- reviewer agents did not read memory, prior sessions, persona dossiers, git history, broad repo context, or local discovery surfaces outside exact assignment paths
- parent stayed alive after fan-out
- `list_agents` was not called with filesystem prefixes
- liveness chatter used `Council progress:`
- runtime child nicknames did not leak as reviewer identities
- raw reviewer blocks, `<subagent_notification>` text, JSON envelopes, and child payloads stayed out of authored progress/final output; Codex JSONL may still contain runtime transport envelopes used as private parse input
- visible progress lines that claim checking, verifying, retrying, closing, or waiting were immediately followed by the matching native tool call
- any `close_agent` result with status `running` was resolved by actual wait/follow-up/close/list evidence before synthesis or a next wave
- final output used every mandatory Council heading as integrated synthesis

## Phase 8: Patch, Bump, And Repeat On Failure

If validation exposes a prompt or packaging bug:

1. Patch the bug.
2. Bump the plugin version again.
3. Commit again with `git commit -sS`.
4. Push.
5. Run `codex plugin marketplace upgrade sai`.
6. Rerun installed-cache proof and the relevant live checks.

Treat Codex hooks as lifecycle guardrails only. Do not rely on hooks for council
orchestration or pre-tool enforcement.

## Phase 9: Score And Verbosity Optimization

Only after installed-cache proof and live working-proof pass may you run
plugin-eval or token-pressure iterations.

Those later commits may reduce verbosity to improve score, but they must preserve
the validated behavior and rerun the release, install, cache, and live checks in
this runbook.
