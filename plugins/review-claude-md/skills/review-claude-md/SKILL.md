---
name: review-claude-md
description: Audit and fix CLAUDE.md files using a tiered binary checklist based on official Anthropic best practices and community guidelines. Use when the user asks to "review CLAUDE.md", "audit CLAUDE.md", "score CLAUDE.md", "improve CLAUDE.md", or "fix CLAUDE.md". Not for generic markdown cleanup or for reviewing skills and agents.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. The bundled validation scripts need bash, grep, sed and awk.
argument-hint: "[path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: Agent Bash Edit Glob Read Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Audit and fix CLAUDE.md files
---

<!-- justify: CF-side-effect Edit/Write fix detected issues in CLAUDE.md with user approval -->

# Review CLAUDE.md

Evaluate any CLAUDE.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix all failing checks and re-evaluate.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the repo path and flags from the user's request |
| `${CLAUDE_SKILL_DIR}` | If the script paths in Phase 3 show an unreplaced placeholder, resolve `scripts/` relative to this skill directory |
| Subagent tool (Agent) | Run the Phase 2 scan and Phase 3 script run inline yourself, with the same outputs. Do this whenever no subagent tool is available, including in Claude Code inside a forked skill. On Codex, opencode and Copilot CLI always run them inline: the steps are sequential and share context, so fan-out only adds failure modes |
| Named agent `review-claude-md:claude-md-evaluator` | Phase 8 only; see [Phase 8](#phase-8-re-evaluate-and-iterate) for the per-agent fallback |
| AskUserQuestion | Not used |
| `context: fork` | Ignored elsewhere; the skill runs in the main agent loop |

On Codex, use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`), never nested `codex exec` or shell-based agent probing. If the sandbox blocks a script or an edit, rerun it with escalation and a short reason.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to repo root (default: current working directory)
- `--score-only` — Report verdict without fixing; do not modify any file
- `--fix` — Fix all failing checks (default behavior)
- `--verbose` — Show chain-of-thought reasoning for each check
- `--thorough` — Include Polish tier in the report

## Verdict logic

Read [references/rubric.md](references/rubric.md) for the full tiered checklist and verdict thresholds (Critical, Important, Polish tiers). Summary: any Critical fail → **FAIL**; 3+ Important fails → **NEEDS WORK**; otherwise **PASS**.

## Workflow

### Phase 1: Discovery

1. Identify target repo root (from argument or cwd)
2. Find all CLAUDE.md files: root, `.claude/CLAUDE.md`, `CLAUDE.local.md`, subdirectories
3. Find [.claude/rules/](.claude/rules/) `*.md` files
4. Note git-tracked vs gitignored status

If no CLAUDE.md exists under the target, say so and stop; do not invent one.

### Phase 2: Codebase Context

Spawn an `Explore` agent to scan the target repository (inline fallback: see [Agent compatibility](#agent-compatibility)). Pass the agent: the repo root path.

Agent reads: Makefile, package.json, Cargo.toml, go.mod, pyproject.toml, CI configs (.github/workflows/, .gitlab-ci.yml), README.md, test configs (jest.config, pytest.ini, vitest.config), lint configs (.eslintrc, biome.json, .prettierrc, rustfmt.toml).
Also reads: top-level directory structure, `git log --oneline -20`, [.claude/rules/](.claude/rules/) contents.

Agent returns ONLY a structured summary with these fields:

- Build system and commands found
- Test framework and test commands
- Lint/format tool and commands
- CI provider and workflow names
- Existing [.claude/rules/](.claude/rules/) files and their topics
- Commit message convention observed
- README sections that overlap with CLAUDE.md content

Use this summary to inform Phase 3-4 checks. Do not re-read any files the agent already summarized.

### Phase 3: Automated Checks

Spawn a `general-purpose` agent to run validation scripts (inline fallback: see [Agent compatibility](#agent-compatibility)). Pass the agent: target CLAUDE.md path, `$TARGET_DIR`, and paths to both scripts:

```bash
"${CLAUDE_SKILL_DIR}/scripts/validate-claudemd.sh" "$TARGET_DIR"
"${CLAUDE_SKILL_DIR}/scripts/validate-commands.sh" "$TARGET_DIR"
```

Run both scripts, parse the JSON output, and return ONLY an array of `{check, pass, detail}` results. Each `pass: false` result maps to the corresponding checklist criterion.

Use these results directly in Phase 5 (Synthesize Verdict). Do not re-run the scripts in the main context.

### Phase 4: Manual Evaluation

Re-read [references/rubric.md](references/rubric.md) in full before starting this phase to prevent drift from the checklist criteria.

For each criterion not already covered by automated scripts, evaluate as binary pass/fail:

1. Read the check description and source reference
2. Examine the relevant section of the CLAUDE.md
3. Record the result with specific evidence (quote the line or describe the absence)
4. If `--verbose`, show chain-of-thought reasoning for each check
5. If `--thorough`, also evaluate Polish tier checks

Read [references/sources.md](references/sources.md) for authoritative source URLs when citing findings.

### Phase 5: Synthesize Verdict

Think step by step before declaring the verdict:

1. List all Critical results — any FAIL?
2. Count Important FAILs — 3 or more?
3. Apply the verdict logic above
4. Write a 2-3 sentence chain-of-thought explaining the reasoning

### Phase 6: Report

Read [references/output-format.md](references/output-format.md) for the verdict template. Output the verdict per this template before applying any fix.

### Phase 7: Fix

If `--score-only` was NOT passed (`--fix` mode, the default):

1. Address every failing Critical and Important check
2. Re-read [references/sources.md](references/sources.md) for rewriting principles before editing because fixes that violate source guidelines create new failures
3. Create [.claude/rules/](.claude/rules/) files if root exceeds 150 lines
4. Target: under 150 lines (ideally 50-100 for root)

With `--score-only`, stop after Phase 6.

### Phase 8: Re-evaluate and iterate

Re-run both validation scripts from Phase 3 against the fixed file, then get a clean-room verdict from the evaluator. Its mandate is [references/claude-md-evaluator.md](references/claude-md-evaluator.md). Pass it: the fixed CLAUDE.md path, the path to [references/rubric.md](references/rubric.md), the fresh validation-script JSON, the Phase 2 codebase summary, the repo root, and whether `--thorough` is set. Pass nothing else. Its reply starts with `## CLAUDE.md evaluation`.

- **Claude Code:** the skill normally runs forked (`context: fork`), where no subagent tool exists, so use the inline bullet below. When a subagent tool is available, spawn the named agent `review-claude-md:claude-md-evaluator`; if the type is unknown, spawn a `general-purpose` agent with the mandate prepended.
- **Copilot CLI:** spawn the named agent `review-claude-md:claude-md-evaluator`, or a generic subagent with the mandate prepended if it is not registered.
- **Codex:** one `spawn_agent` call with the mandate prepended and no forked parent context; `wait_agent`, then `close_agent` right away.
- **opencode:** the `task` tool with an installed `claude-md-evaluator` agent, or the built-in `general` subagent with the mandate prepended.
- **No subagent tool, or the reply is empty or lacks its first line:** evaluate inline yourself, following the mandate, and re-open the file instead of judging from memory of your edits.

Produce the post-fix report per [references/output-format.md](references/output-format.md) from that verdict. If the verdict is still not PASS, fix the remaining issues using Edit, then re-evaluate again. Stop at PASS or when no further high-value fix remains; if you stop short of PASS, list the checks that still fail and why.

## Good vs Bad Examples

Read [references/examples.md](references/examples.md) for good vs bad comparison pairs covering commands, architecture, gotchas, and format sections.

## Example Invocations

In Codex use `$review-claude-md` in place of `/review-claude-md`.

<example>
Default audit (current directory):

```bash
/review-claude-md
```
</example>

<example>
Specific repo with verbose output:

```bash
/review-claude-md /path/to/repo --verbose
```
</example>

<example>
Score-only and thorough modes:

```bash
/review-claude-md --score-only
/review-claude-md --thorough
/review-claude-md /path/to/repo --verbose --thorough
```
</example>
