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

### Formal process rule: working before scoring

The first improvement-loop phase is to find a working solution. Do not optimize for
plugin-eval score, brevity, token footprint, or elegance until real installed-plugin
validation proves the Council behavior works. After that proof exists, later
iterations may improve score by reducing verbosity while preserving the validated
behavior.

### Canonical Codex council release commands

Use these commands for every Codex Council improvement loop. Do not rediscover
equivalent CLI syntax, do not validate through a local marketplace path, and do not
run score/verbosity optimization before the working-proof phase passes.

Set the version and target repository first:

```sh
VERSION=<bumped-version>
TARGET_REPO=/absolute/path/to/real/target/repo
```

Baseline and drift check from the `sai` repo:

```sh
git status -sb
sed -n '1,180p' README.md
sed -n '1,180p' CLAUDE.md
sed -n '1,180p' CONTRIBUTING.md
python3 -c 'import json,pathlib; p=pathlib.Path("."); paths=[p/"plugins/council/plugin.json",p/"plugins/council/.codex-plugin/plugin.json"]; [print(x, json.loads(x.read_text()).get("version")) for x in paths]; c=pathlib.Path.home()/".codex/plugins/cache/sai/council"; print("cache", sorted(d.name for d in c.glob("*") if d.is_dir()))'
```

Static validation before commit:

```sh
python3 -c 'import json,pathlib,tomllib; p=pathlib.Path("."); versions=[json.loads((p/"plugins/council/plugin.json").read_text())["version"],json.loads((p/"plugins/council/.codex-plugin/plugin.json").read_text())["version"]]; assert len(set(versions))==1, versions; agents=sorted((p/"codex/agents").glob("*.toml")); assert agents; bad=[a.name for a in agents if tomllib.loads(a.read_text()).get("model_reasoning_effort")!="high"]; assert not bad,bad; packaged=sorted((p/"plugins/council/agents").glob("*.agent.md")); assert len(packaged)==len(agents),(len(packaged),len(agents)); bad=[a.name for a in packaged if "model_reasoning_effort: high" not in a.read_text() or "tools: Read" not in a.read_text()]; assert not bad,bad; skill=(p/"plugins/council/skills/council/SKILL.md").read_text(); missing=[s for s in ["reasoning_effort: \"high\"","same as other reviewers","Council progress:","Council not run: broad council approval not granted."] if s not in skill]; assert not missing,missing; print("static council surface ok", versions[0], len(agents))'
git diff --check
```

Commit, push, release, and install the real marketplace version:

```sh
git commit -sS -m "fix(council): <short behavior summary>"
git push
codex plugin marketplace upgrade sai
```

Installed-cache proof:

```sh
python3 -c 'import json,pathlib,sys; version=sys.argv[1]; root=pathlib.Path.home()/".codex/plugins/cache/sai/council"/version; manifest=json.loads((root/".codex-plugin/plugin.json").read_text()); assert manifest["version"]==version, manifest.get("version"); agents=sorted((root/"agents").glob("*.agent.md")); assert len(agents)==27,len(agents); bad=[p.name for p in agents if "model_reasoning_effort: high" not in p.read_text() or "tools: Read" not in p.read_text()]; assert not bad,bad; skill=(root/"skills/council/SKILL.md").read_text(); missing=[s for s in ["reasoning_effort: \"high\"","same as other reviewers","Council progress:","Council not run: broad council approval not granted."] if s not in skill]; assert not missing,missing; print("installed cache ok", root)' "$VERSION"
codex --version
codex features list
```

Live smoke from the real target repository. Keep the under-development agent
features enabled when they are available:

```sh
codex exec --json --output-last-message /tmp/sai-council-normal-final.txt --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council core-mix Council validation smoke. Inline material only: review the rule "always run all selected reviewers with complete bounded material" and report only material blockers.'
codex exec --json --output-last-message /tmp/sai-council-prefixed-final.txt --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council:council core-mix Council validation smoke. Inline material only: verify the plugin-prefixed alias follows the same bounded-review behavior.'
codex exec --json --output-last-message /tmp/sai-council-broad-final.txt --cd "$TARGET_REPO" --model gpt-5.4-mini --enable multi_agent_v2 --enable enable_fanout --enable child_agents_md --enable runtime_metrics '$council all Council validation smoke. Inline material only: this broad run has no same-turn approval and must stop.'
python3 -c 'import pathlib; p=pathlib.Path("/tmp/sai-council-broad-final.txt"); assert p.read_text().strip()=="Council not run: broad council approval not granted.", p.read_text(); print("broad stop ok")'
codex exec resume --last --include-non-interactive --json --output-last-message /tmp/sai-council-followup-final.txt '$council follow-up challenge: using the prior council smoke result, verify the same accepted reviewer roster is preserved or explicitly reported missing.'
```

For each live run, keep the JSON event stream or session JSONL as evidence and
inspect it before deciding the loop passed. Required proof: native reviewer
`spawn_agent` calls happened, `wait_agent`/`followup_task` supervision happened
when needed, fixed six-reviewer rosters did not stop after the first wave, every
reviewer prompt carried complete bounded material, no reviewer prompt used
`same as other reviewers`, no reviewer read memory/prior sessions/repo discovery,
raw child payloads stayed internal, final output used the fixed Council headings,
and runtime child nicknames did not appear as reviewer identities.

Only after the installed-cache proof and live working-proof pass may you run
plugin-eval or token-pressure iterations. Those later commits must preserve the
same live smoke behavior and rerun the release, install, cache, and live checks
above.

## Codex council behavior contract

- Council is opt-in review work, not a generic commit, pre-commit, or approval gate.
- Codex Council uses native `spawn_agent` reviewer agents. Use all relevant current agent features, including enabled under-development agents-v2/fan-out features; do not run nested `codex exec`.
- Broad runs above 6 reviewers require explicit current-run approval. If approval is unavailable, stop with exactly `Council not run: broad council approval not granted.`
- Reviewer fan-out is not completion. The orchestrator must keep supervising until every selected reviewer is accepted, failed, or missing.
- Fixed-roster modes (`core`, `core-eng`, `core-ux`, `core-mix`) always run all 6 selected reviewers. Output-focus wording such as `blockers only` must not shrink the roster or skip the second wave.
- Every selected reviewer must receive the complete bounded material in its own spawn or follow-up prompt. Do not rely on child agents sharing context, and never send `same as other reviewers`, `same as assignment`, or `see prior wave`.
- Final synthesis must include every mandatory Council heading, including `## Disagreement (real tradeoffs the user must decide)` even when the section says no material disagreement surfaced.
- Follow-up challenge and blocker-check rounds keep the same accepted reviewer roster where possible. If agents are already closed, respawn the same slugs with the original material plus the follow-up diff/challenge; never silently reduce or swap the roster.
- At least once per minute, classify every live reviewer as `healthy`, `drifting`, `stalled`, `blocked`, or `done`; nudge non-healthy reviewers in that same pass.
- Sparse `Council progress:` updates are allowed when they prove the run is alive. Do not leak reviewer drafts, transport payloads, or raw `## <reviewer> review` blocks.

## Commit rules

- Use conventional commits: `type(scope): description`.
- Every commit must use `git commit -sS`.
- Verify signed commits when commit metadata is in scope.
- Do not edit `.github/workflows/`; those workflows are org-synced.
- Do not add inline linter suppressions or relax lint config without explicit user approval after first investigating a real fix.
