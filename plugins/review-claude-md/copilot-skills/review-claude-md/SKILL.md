---
name: review-claude-md
description: >-
  Audit and fix a CLAUDE.md against a structured tiered checklist from a normal
  Copilot session when the user asks to review, score, audit, or improve a
  CLAUDE.md. Scans the target repo, runs the bundled validation scripts, reports a
  PASS / NEEDS WORK / FAIL verdict with evidence, then fixes failing checks and
  re-evaluates against the rubric. Not for generic markdown cleanup, and not for
  reviewing Copilot or Codex skills/agents.
allowed-tools:
  - agent
  - read
  - shell
---

# Review CLAUDE.md (Copilot)

Evaluate any CLAUDE.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix the failing checks and re-evaluate until it passes. The current session agent is the orchestrator and runs the whole workflow.

## Orchestration rule (read first)

**Run the steps inline in the main session by default - they are sequential and share context, so inline is simpler and more reliable than fan-out. Only delegate the re-evaluation to the claude-md-evaluator agent when a clean-room second opinion helps; do not fan out one agent per step.**

The source Claude workflow spawned helper agents (an Explore agent to scan the repo, a general-purpose agent to run the scripts, and a re-evaluation agent) but it ran them strictly sequentially and they shared the same context. On Copilot there is nothing to gain from re-spawning that chain as separate agents: do the scan, the scripts, the report, the fixes, and the re-check yourself in one session. The only sanctioned delegation is the optional `claude-md-evaluator` agent (bundled under `agents/`, invoked via the `agent` tool) for an independent post-fix verdict.

## Arguments

Parse from the user's request:

- First path-like token: the target repo root (default: current working directory).
- `--score-only` — report the verdict without applying fixes.
- `--fix` — fix all failing checks (this is the default behavior).
- `--verbose` — show the reasoning for each check.
- `--thorough` — also evaluate and report the Polish tier.

If no CLAUDE.md is resolvable under the target, say so and ask which repo/file to review - do not invent one.

## Verdict logic

Read [references/rubric.md](references/rubric.md) for the full tiered checklist (Critical, Important, Polish) and the verdict thresholds. Summary: any Critical fail → **FAIL**; 3+ Important fails → **NEEDS WORK**; otherwise **PASS**.

## Workflow

### Phase 1 - Discovery (inline)

1. Identify the target repo root (from the argument or cwd).
2. Find all CLAUDE.md files: root, `.claude/CLAUDE.md`, `CLAUDE.local.md`, subdirectory CLAUDE.md files.
3. Find `.claude/rules/*.md` files.
4. Note git-tracked vs gitignored status.

### Phase 2 - Codebase context (inline)

Scan the target repo yourself with `read` and `shell` (grep/find). Gather a compact summary - do not re-read these files again later:

- Build system + commands (Makefile, package.json scripts, Cargo.toml, go.mod, pyproject.toml).
- Test framework + test commands (jest/vitest/pytest configs, etc.).
- Lint/format tool + commands (.eslintrc, biome.json, .prettierrc, rustfmt.toml, golangci config).
- CI provider + workflow names (`.github/workflows/`, `.gitlab-ci.yml`).
- Existing `.claude/rules/` files and their topics.
- Commit message convention (`git log --oneline -20`).
- README sections that overlap with CLAUDE.md content.

### Phase 3 - Automated checks (inline, via `shell`)

Run both bundled validation scripts via the `shell` tool against the target repo root and parse the JSON (`{check, pass, detail}`, one object per line):

```bash
scripts/validate-claudemd.sh "<repo-root>"
scripts/validate-commands.sh "<repo-root>"
```

(Resolve `scripts/` relative to this skill directory.) Each `pass: false` maps to the corresponding checklist criterion. Use these results directly in Phase 5; do not re-run them.

### Phase 4 - Manual evaluation (inline)

Re-read [references/rubric.md](references/rubric.md) in full before this phase to avoid drifting from the criteria. For each criterion not already settled by the scripts, judge binary pass/fail:

1. Read the check description and its source reference.
2. Examine the relevant section of the CLAUDE.md.
3. Record the result with specific evidence (quote the line, or describe the absence).
4. If `--verbose`, show the reasoning per check.
5. If `--thorough`, also evaluate the Polish tier.

Read [references/sources.md](references/sources.md) for authoritative source URLs when citing findings.

### Phase 5 - Synthesize verdict (inline)

Think step by step before declaring:

1. List all Critical results - any FAIL?
2. Count Important FAILs - 3 or more?
3. Apply the verdict logic.
4. Write 2-3 sentences explaining the reasoning.

### Phase 6 - Report findings before fixes

Read [references/output-format.md](references/output-format.md) and emit the verdict using that template, scored against [references/rubric.md](references/rubric.md). **Report findings before applying any fixes**, unless the user explicitly asked for immediate remediation - then go straight to Phase 7 and report after.

### Phase 7 - Fix (unless `--score-only`)

In `--fix` mode (the default):

1. Address every failing Critical and Important check.
2. Re-read [references/sources.md](references/sources.md) for rewriting principles first - fixes that violate the source guidelines just create new failures.
3. Create `.claude/rules/*.md` files if the root file exceeds 150 lines.
4. Target: under 150 lines (ideally 50-100 for the root).

Editing is a side effect the user opted into by asking to fix/improve their CLAUDE.md; in `--score-only` mode, do not modify any files.

### Phase 8 - Re-evaluate and iterate

After fixing, re-evaluate the file against the rubric. Two paths:

- **Inline (default):** re-run both validation scripts, re-check the manual criteria, re-apply the verdict logic, and produce a post-fix report per [references/output-format.md](references/output-format.md).
- **Delegated (optional):** when a clean-room second opinion is worthwhile (e.g. a borderline verdict, or the user wants an independent check), invoke the `claude-md-evaluator` agent via the `agent` tool. Pass it: the fixed CLAUDE.md path, the rubric (and `references/rubric.md` path), the latest validation-script output, the Phase 2 codebase summary, and the repo root. It returns a PASS / NOT-PASS report with failing items and concrete fixes; its first line is `## CLAUDE.md evaluation`.

If the result is not PASS, apply the remaining fixes inline and re-evaluate again. Iterate until PASS or no further high-value fixes remain; if you stop short of PASS, say which checks remain and why they were left.

## Good vs bad examples

Read [references/examples.md](references/examples.md) for good-vs-bad pairs covering commands, architecture, gotchas, and format sections.

## Scope

This skill audits CLAUDE.md operational-context files. It is not for generic markdown cleanup, prose editing, or reviewing Copilot/Codex skills and agents. For those, use a different tool.
