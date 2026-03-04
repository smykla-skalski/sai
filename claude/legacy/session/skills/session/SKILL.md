---
name: session
description: Captures session context for continuity between Claude Code sessions. Use when ending a session, approaching context limits, or transitioning between distinct tasks. Prevents re-investigation and failed approach retries in the next session.
argument-hint: "[session-focus]"
allowed-tools: Read, Write, Bash, Grep, Glob, AskUserQuestion
user-invocable: true
---

# Session Handover

Capture all critical context from the current session so the next session can continue without re-investigation or retrying failed approaches. Produces a dense handover document saved to `.claude/sessions/` and copied to clipboard.

## Arguments

Parse from `$ARGUMENTS`:

| Argument     | Default | Purpose                                       |
|:-------------|:--------|:----------------------------------------------|
| (positional) | —       | Optional session focus to narrow the handover |

If multiple task threads exist and no focus is provided, use AskUserQuestion to let the user choose which thread to capture.

## Constraints

- **Preserve original prompt verbatim** — if work stems from a user prompt, include exact wording
- **Zero context loss** — capture everything that would waste time if rediscovered
- **Maximum density** — technical terms, pseudocode, repo-relative paths, no prose
- **Never include derivable content** — if findable in <2min from code/git/docs, skip it
- **Never assume** — if uncertain about priorities or scope, ask the user
- **No progress tracking** — this is context transfer, not status reporting
- **No code blocks** — pseudocode one-liners only, non-obvious insights only
- **No absolute paths** — repo-relative paths only
- **Omit empty sections** — do not leave blank section headers
- **Always save to file AND copy to clipboard** — both are required

## What to Capture vs Skip

```text
Need this to avoid wasting time?
├─ YES → Derivable in <2min from code? → NO: CAPTURE / YES: SKIP
└─ NO  → SKIP
```

**Always capture:**

- Skills invoked via the Skill tool during the session (with context of how/why)
- Original user prompt verbatim (cannot be reconstructed from code)
- Pending/in-progress todos (not derivable from code state)
- Failed approaches with elimination rationale
- Architectural decisions with trade-off reasoning
- Environment constraints (versions, configs, platform gotchas)

**Skip:**

- Obvious file locations ("authenticate function in src/auth/authenticate.ts")
- Vague entries ("issues", "problems", "stuff")
- Progress metrics ("completed 3 of 5 tasks")
- Full function bodies (use pseudocode signatures instead)

## Density Rules

- "We attempted X but unfortunately..." → "Tried X: failed due to Y"
- 20-line function body → "`func(a,b)` iterates, transforms, returns filtered"
- "Using Redis" → "Chose Redis over in-memory: survives restarts"
- Always include "why" and elimination rationale for failed paths

## Workflow

### Phase 1: Context Collection

1. Parse `$ARGUMENTS` for optional session focus.
2. Gather current directory and git status via Bash (`pwd` and `git status --porcelain`).
3. Review conversation history for Skill tool invocations. Record each skill name and brief context of how/why it was used. Skills are only those invoked via the Skill tool — not general tools like Read/Write/Bash.
4. Identify the original user prompt that initiated the current work (if applicable).
5. Check for active todo lists with incomplete tasks.

### Phase 2: Session Review

1. Review what was investigated, attempted, and learned during the session.
2. Extract failed approaches — for each, record what was tried, why it failed, and what it eliminates.
3. Capture environment constraints discovered (versions, configs, platform issues).
4. Document architectural decisions — what was chosen over what, and why.
5. Record investigation findings: key files, function signatures, data flows, dependencies.
6. Define the precise stopping point and any blockers.
7. List concrete next steps (3-5 actions with file paths).

### Phase 3: Build Handover Document

Read `references/template.md` in full before starting this phase.

Populate the template following these rules:

- **Skill Activation section**: Include ONLY if skills were used or mentioned. List "Required" (actually invoked) and "Recommended" (mentioned but not invoked). Omit entirely if no skills.
- **Original Request section**: Include ONLY if work stems from a specific user prompt. Preserve verbatim. Omit if continuation/follow-up.
- **Pending Todos section**: Include ONLY if incomplete todos exist. Omit if none or all completed.
- **Failed Approaches, Environment Constraints, Architectural Decisions, Investigation Findings**: Include only if non-empty.
- **Current State and Next Steps**: Always include.

### Phase 4: Verify

Re-read the handover document and check against constraints:

1. No empty sections remain (every heading has content below it).
2. No absolute paths — all paths are repo-relative.
3. No prose filler — every line passes the "need this to avoid wasting time?" test.
4. No derivable content — nothing reconstructable in <2min from code/git/docs.
5. Original prompt (if included) is verbatim, not paraphrased.
6. Next steps are concrete actions with file paths, not vague intentions.

If any check fails, revise the affected sections and re-verify.

### Phase 5: Save and Deliver

1. Generate filename: `.claude/sessions/YYMMDD-handover-{slug}.md` where `{slug}` is a short kebab-case summary.
2. Write the handover document to that path. If the directory doesn't exist, create it with `mkdir -p .claude/sessions` and retry.
3. Copy to clipboard: detect the platform clipboard command via Bash (`command -v pbcopy || command -v xclip || command -v xsel`). Use the first available (`pbcopy`, `xclip -selection clipboard`, or `xsel --clipboard --input`). If none are available, skip clipboard and inform the user.
4. Report the file location and clipboard status to the user.

## Edge Cases

- **Multiple task threads, no focus given**: Ask the user which thread to capture via AskUserQuestion.
- **Session just started**: Minimal handover — stopping point + next steps only.
- **No failed approaches**: Omit that section entirely.
- **No skills used**: Omit Skill Activation section entirely — do not include "No skills required" text.

## Example

```bash
/session plugin-migration
```

Produces `.claude/sessions/260219-handover-plugin-migration.md`:

```markdown
# Session Handover: Plugin migration to XDG paths: 4 of 6 migrated

## Skill Activation

**MANDATORY FIRST ACTION**: Before proceeding with ANY task, you MUST use the Skill tool to learn the following skills:

**Required (used in previous session):**
- `review-skill` — validated migrated plugins passed checklist

## Original Request

> migrate all plugins to use XDG persistent data paths instead of relative ./data dirs

## Failed Approaches

- Tried symlinking `./data` → XDG path: broke plugin cache updates, symlink target deleted on reinstall
- Tried env var in plugin.json: not supported, plugin.json is static metadata only

## Current State

**Stopped At:** `git/skills/worktree/SKILL.md` — mid-migration, DATA_DIR resolved but read/write calls not updated
**Blockers:** None
**Open Questions:** Should `session` plugin also migrate? It writes to `.claude/sessions/` which is project-local, not plugin state

## Next Steps

1. Finish `git/skills/worktree/SKILL.md` — update file ops to use `$DATA_DIR`
2. Migrate `git/skills/clean-gone/SKILL.md` — same pattern
3. Run `/review-skill` on each migrated plugin
```
