# Codex Council Improvement Loop Runbook

This is the canonical process for functional Codex Council changes under
`plugins/council/`, `codex/agents/`, or Codex marketplace metadata.

Do not validate through a local marketplace path. Do not rediscover equivalent
CLI syntax during the loop. Do not optimize plugin-eval score, brevity, token
footprint, or elegance until the installed-plugin working-proof phase passes.

## Phase 0: Set Variables

Set the version and real target repository first:

```sh
VERSION=<bumped-version>
TARGET_REPO=/absolute/path/to/real/target/repo
EVIDENCE_DIR=tmp/council-validation/$VERSION
mkdir -p "$EVIDENCE_DIR"
```

Use the real target repository for live Codex validation, not `sai`, when behavior
depends on repo context.

## Phase 1: Baseline And Drift Check

Run from the `sai` repo before editing:

```sh
git status -sb
sed -n '1,180p' README.md
sed -n '1,180p' CLAUDE.md
sed -n '1,180p' CONTRIBUTING.md
python3 -c 'import json,pathlib; p=pathlib.Path("."); paths=[p/"plugins/council/plugin.json",p/"plugins/council/.codex-plugin/plugin.json"]; [print(x, json.loads(x.read_text()).get("version")) for x in paths]; c=pathlib.Path.home()/".codex/plugins/cache/sai/council"; print("cache", sorted(d.name for d in c.glob("*") if d.is_dir()))'
```

Check version drift across:

- `plugins/council/plugin.json`
- `plugins/council/.codex-plugin/plugin.json`
- installed cache under `~/.codex/plugins/cache/sai/council/`
- README references when behavior docs change

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

Run from the `sai` repo:

```sh
python3 -c 'import json,pathlib,tomllib; p=pathlib.Path("."); versions=[json.loads((p/"plugins/council/plugin.json").read_text())["version"],json.loads((p/"plugins/council/.codex-plugin/plugin.json").read_text())["version"]]; assert len(set(versions))==1, versions; agents=sorted((p/"codex/agents").glob("*.toml")); assert agents; bad=[a.name for a in agents if tomllib.loads(a.read_text()).get("model_reasoning_effort")!="high"]; assert not bad,bad; packaged=sorted((p/"plugins/council/agents").glob("*.agent.md")); assert len(packaged)==len(agents),(len(packaged),len(agents)); bad=[a.name for a in packaged if "model_reasoning_effort: high" not in a.read_text() or "tools: Read" not in a.read_text()]; assert not bad,bad; skill=(p/"plugins/council/skills/council/SKILL.md").read_text(); missing=[s for s in ["reasoning_effort: \"high\"","same as other reviewers","Council progress:","Council not run: broad council approval not granted."] if s not in skill]; assert not missing,missing; print("static council surface ok", versions[0], len(agents))'
git diff --check
```

Functional Codex skill/plugin changes must bump the Codex plugin version in
`plugins/council/.codex-plugin/plugin.json` in the same commit. Keep package
versions aligned unless there is a documented reason not to.

## Phase 4: Commit Before Live Loop

Commit the implementation before starting live validation:

```sh
git commit -sS -m "fix(council): <short behavior summary>"
```

Verify the signed commit when commit metadata is in scope:

```sh
git log -1 --show-signature --format=fuller --stat
git verify-commit HEAD
```

## Phase 5: Push And Install Real Marketplace Version

Release through the real marketplace path:

```sh
git push
codex plugin marketplace upgrade sai
```

Do not switch `sai` to a local marketplace path for validation. Local-path
registration can leave the versioned cache stale and cannot be upgraded with
`codex plugin marketplace upgrade`.

## Phase 6: Installed-Cache Proof

Verify the exact installed version:

```sh
python3 -c 'import json,pathlib,sys; version=sys.argv[1]; root=pathlib.Path.home()/".codex/plugins/cache/sai/council"/version; manifest=json.loads((root/".codex-plugin/plugin.json").read_text()); assert manifest["version"]==version, manifest.get("version"); agents=sorted((root/"agents").glob("*.agent.md")); assert len(agents)==27,len(agents); bad=[p.name for p in agents if "model_reasoning_effort: high" not in p.read_text() or "tools: Read" not in p.read_text()]; assert not bad,bad; skill=(root/"skills/council/SKILL.md").read_text(); missing=[s for s in ["reasoning_effort: \"high\"","same as other reviewers","Council progress:","Council not run: broad council approval not granted."] if s not in skill]; assert not missing,missing; print("installed cache ok", root)' "$VERSION"
```

Check the local Codex feature surface before live validation:

```sh
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

Run the actual Council paths from the real target repository. Use the cheapest
practical model for repeated smoke loops; escalate only when the cheap model
cannot diagnose or reproduce a real failure.

Keep under-development agent features enabled when they are available:

```sh
codex exec --json --output-last-message "$EVIDENCE_DIR/normal-final.txt" --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council core-mix Council validation smoke. Inline material only: review the rule "always run all selected reviewers with complete bounded material" and report only material blockers.' > "$EVIDENCE_DIR/normal.jsonl"
codex exec --json --output-last-message "$EVIDENCE_DIR/prefixed-final.txt" --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council:council core-mix Council validation smoke. Inline material only: verify the plugin-prefixed alias follows the same bounded-review behavior.' > "$EVIDENCE_DIR/prefixed.jsonl"
codex exec --json --output-last-message "$EVIDENCE_DIR/broad-final.txt" --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council all Council validation smoke. Inline material only: this broad run has no same-turn approval and must stop.' > "$EVIDENCE_DIR/broad.jsonl"
python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); assert p.read_text().strip()=="Council not run: broad council approval not granted.", p.read_text(); print("broad stop ok")' "$EVIDENCE_DIR/broad-final.txt"
codex exec resume --last --include-non-interactive --json --output-last-message "$EVIDENCE_DIR/followup-final.txt" '$council follow-up challenge: using the prior council smoke result, verify the same accepted reviewer roster is preserved or explicitly reported missing.' > "$EVIDENCE_DIR/followup.jsonl"
```

The live smoke must exercise:

- normal `$council ...`
- `$council:council ...` or equivalent plugin-prefixed alias when available
- broad `$council all ...` stop/approval behavior
- follow-up challenge through actual Codex resume/thread continuation, not a fresh fake session
- stalled reviewer recovery, reviewer nudging, and raw reviewer output rejection when a change touches supervision

## Phase 8: Evidence Review

Keep the JSON event stream or session JSONL as evidence and inspect it before
deciding the loop passed.

Minimum evidence commands:

```sh
rg -n 'spawn_agent|wait_agent|followup_task|Council progress:|multi_agent_v2|enable_fanout|child_agents_md|runtime_metrics' "$EVIDENCE_DIR"
rg -n 'Council not run: broad council approval not granted.' "$EVIDENCE_DIR/broad-final.txt"
rg -n '# Council review:|## Convergence \(high-confidence signals\)|## Disagreement \(real tradeoffs the user must decide\)|## Per-reviewer top-3|## What to do next|## What we did not address' "$EVIDENCE_DIR"/*.txt
```

Required proof:

- native reviewer `spawn_agent` calls happened
- `wait_agent` and `followup_task` supervision happened when needed
- fixed six-reviewer rosters did not stop after the first wave
- every reviewer prompt carried complete bounded material
- no reviewer prompt used `same as other reviewers`, `same as assignment`, or `see prior wave`
- reviewer agents did not read memory, prior sessions, persona dossiers, git history, broad repo context, or local discovery surfaces outside exact assignment paths
- parent stayed alive after fan-out
- `list_agents` was not called with filesystem prefixes
- liveness chatter used `Council progress:`
- runtime child nicknames did not leak as reviewer identities
- raw reviewer blocks and child payloads stayed internal
- final output used every mandatory Council heading as integrated synthesis

## Phase 9: Patch, Bump, And Repeat On Failure

If validation exposes a prompt or packaging bug:

1. Patch the bug.
2. Bump the plugin version again.
3. Commit again with `git commit -sS`.
4. Push.
5. Run `codex plugin marketplace upgrade sai`.
6. Rerun installed-cache proof and the relevant live checks.

Treat Codex hooks as lifecycle guardrails only. Do not rely on hooks for council
orchestration or pre-tool enforcement.

## Phase 10: Score And Verbosity Optimization

Only after installed-cache proof and live working-proof pass may you run
plugin-eval or token-pressure iterations.

Those later commits may reduce verbosity to improve score, but they must preserve
the validated behavior and rerun the release, install, cache, and live checks in
this runbook.
