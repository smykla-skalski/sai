# SAI agent instructions

This repo packages agent skills and plugins for Claude Code, Copilot CLI, and Codex.

## Validation

There is no repo-level build, test, or lint entrypoint.
Do not add placeholder `mise`, `make`, or lint tasks.
Validate the exact runtime surface you changed.

- Claude plugin smoke: `claude --plugin-dir claude/{plugin-name}/`
- Copilot council smoke: `copilot plugin install /absolute/path/to/sai/plugins/council`, then run `/council ...`
- Codex council smoke: install the bumped local marketplace/plugin, then run `$council ...` from the real target repository
- Script-heavy changes: run the local checker/schema/smoke flow that belongs to that skill

## Codex council improvement loop

Use this loop for functional Codex changes under `plugins/council/`, `codex/agents/`, or Codex marketplace metadata:

1. Read `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and the Codex-facing files you are changing.
2. Check version drift before editing: `plugins/council/plugin.json`, `plugins/council/.codex-plugin/plugin.json`, installed cache under `~/.codex/plugins/cache/sai/council/`, and README references.
3. Change the complete Codex surface, not only one file: `plugins/council/skills/council/SKILL.md`, `plugins/council/.codex-plugin/plugin.json`, relevant `codex/agents/*.toml` or `plugins/council/agents/*.agent.md`, marketplace metadata, and README when behavior changes.
4. For functional Codex skill/plugin changes, bump the Codex plugin version in `plugins/council/.codex-plugin/plugin.json` in the same commit. Keep package versions intentionally aligned unless there is a documented reason not to.
5. Commit the implementation first with `git commit -sS` before starting the live improvement loop.
6. Install or upgrade the bumped local Codex plugin after that commit, then verify the installed cache contains the bumped version and the changed skill text.
7. Use the cheapest practical model for repeated validation and smoke loops. Escalate only when the cheap model cannot diagnose or reproduce a real failure.
8. Run Codex validations from the real target repository/cwd when behavior depends on repo context, not from `sai`.
9. Exercise the actual Council paths:
   - normal `$council ...`
   - `$council:council ...` or equivalent plugin-prefixed alias when available
   - broad `$council all ...` stop/approval behavior
   - follow-up challenge via actual Codex resume/thread continuation, not a fresh fake session
   - stalled reviewer recovery, reviewer nudging, and raw reviewer output rejection
10. Inspect Codex session artifacts and installed plugin files to prove what happened: subagents spawned, parent stayed alive after fan-out, `wait_agent`/`followup_task` supervision happened, raw reviewer blocks stayed internal, and final output was integrated synthesis.
11. Treat Codex hooks as lifecycle guardrails only. Do not rely on hooks for council orchestration or pre-tool enforcement.
12. If validation exposes a prompt or packaging bug, patch it, bump again, commit again with `git commit -sS`, reinstall that bumped version, and rerun the relevant live checks.

## Codex council behavior contract

- Council is opt-in review work, not a generic commit, pre-commit, or approval gate.
- Codex Council uses native `spawn_agent` reviewer agents. Do not run nested `codex exec`.
- Broad runs above 6 reviewers require explicit current-run approval. If approval is unavailable, stop with exactly `Council not run: broad council approval not granted.`
- Reviewer fan-out is not completion. The orchestrator must keep supervising until every selected reviewer is accepted, failed, or missing.
- At least once per minute, classify every live reviewer as `healthy`, `drifting`, `stalled`, `blocked`, or `done`; nudge non-healthy reviewers in that same pass.
- Sparse `Council progress:` updates are allowed when they prove the run is alive. Do not leak reviewer drafts, transport payloads, or raw `## <reviewer> review` blocks.

## Commit rules

- Use conventional commits: `type(scope): description`.
- Every commit must use `git commit -sS`.
- Verify signed commits when commit metadata is in scope.
- Do not edit `.github/workflows/`; those workflows are org-synced.
- Do not add inline linter suppressions or relax lint config without explicit user approval after first investigating a real fix.
