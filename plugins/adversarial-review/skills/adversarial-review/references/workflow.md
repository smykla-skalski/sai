---
name: adversarial-review
description: Fast two-pass adversarial code review. A Code Adversary subagent red-teams a diff or PR to find the concrete bug, then a separate Findings Adversary subagent with a clean context tries to refute every finding to cut false positives. Use for routine changes where a full staff review is overkill, or as the review gate inside ship-it.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git; the gh CLI for PR reviews.
argument-hint: "[<pr-url> | <diff-file> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Two-pass adversarial code review in clean-context subagents
---

# Adversarial Review

Find the bug, then try to prove the bug report wrong. It answers one question - **is this change correct?** - and answers it hard. It does not evaluate architecture, conventions, dead code, or taste; that is `/staff-code-review`.

Two subagents, opposed, each with a clean context:

1. **Code Adversary** - assumes the change is broken and hunts the concrete failure. A `blocking:` finding carries an executed reproduction or an explicit interleaving trace; anything less is an `issue:` or a `question:`. Mandate: [references/code-adversary.md](references/code-adversary.md).
2. **Findings Adversary** - assumes the Code Adversary is wrong and tries to refute each finding against the source, stripping `blocking:` from findings without proof. Runs only when the first pass found a `blocking:` or `issue:`. Mandate: [references/findings-adversary.md](references/findings-adversary.md).

The second pass exists because an unrefuted adversary nit-bombs. It sees only the first pass's findings, never its reasoning, so it cannot inherit the same misread. Each adversary lives for exactly one verdict: it starts in a fresh context with no forked or inherited history, is closed once its reply is validated, and is never reused for a fix, a re-check or another change.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the PR URL, diff file, `--base` and `--context` from the user's request |
| Named agents `adversarial-review:code-adversary` / `findings-adversary` | Spawn a generic subagent with the matching mandate file from `references/` prepended (see [Spawning a clean-context subagent](#spawning-a-clean-context-subagent)) |
| Subagent tool (Agent) | Codex: `spawn_agent`; opencode: `task`; Copilot CLI: its task/subagent tool. With no subagent tool at all, run both passes inline (see [Fallback](#fallback---no-subagents)) |
| AskUserQuestion, `context: fork` | Not used |

The two passes always run sequentially, so the skill never needs more than one extra subagent at a time.

## Arguments

Parse from `$ARGUMENTS`:

| Argument | Meaning |
| :-- | :-- |
| `<pr-url>` | Review a GitHub PR |
| `<diff-file>` | Review a saved patch file |
| `--base <ref>` | Review the working tree (committed + uncommitted) against the merge-base with `<ref>` |
| (none) | Same as `--base origin/<default-branch>` |
| `--context <file\|text>` | Task context: issue body, acceptance criteria, PR description. A path is read; anything else is used verbatim |

## Phase 1 - Build the review assignment

Do not read the full diff into your own context; the subagents fetch it themselves. Resolve only what they need:

- **Local (`--base` or none):** resolve the default branch with `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback `origin/main`). `BASE=$(git merge-base <ref> HEAD)`. Diff command: `git diff <BASE sha>`. Files: `git diff --name-only <BASE sha>`. Untracked files (`git ls-files --others --exclude-standard`) are not in the diff; list them separately so the subagents read them whole.
- **PR URL:** `gh pr view <url> --json number,headRefOid,baseRefName,title,body`. Diff command: `gh pr diff <url>`. If local `HEAD` is not `headRefOid`, run `git fetch origin pull/<number>/head` and tell the subagents to read changed files with `git show <headRefOid>:<path>` instead of the working tree. Use the PR title and body as context when `--context` is absent.
- **Diff file:** diff command `cat <file>`; files from its `+++ b/` headers.

If the file list is empty, output `Review Verdict: CLEAN` followed by `Nothing to review: empty diff.` and stop.

Assemble one **Review assignment** block, reused verbatim in both phases:

```
Repository: <absolute repo root>
Diff command: <command>
File reads: <working tree | git show <sha>:<path>>
Changed files:
<one per line>
Untracked files (new, read whole):
<one per line, or "none">
Task context:
<context, or "none">
```

## Spawning a clean-context subagent

Each pass is one fresh subagent whose prompt is the Review assignment plus the pass-specific payload. When the subagent is generic rather than a named adversary agent, prepend the full content of the pass's mandate file. Pass nothing else - not your own reading of the code, not hypotheses, not this conversation.

An adversary lives for exactly one verdict. Start it with no forked or inherited history, close it as soon as its reply is validated, and never resume, message or reuse it afterwards - not for a fix, not for a re-check, not for the next revision. A later pass or a later change always gets a new subagent.

**Claude Code.** Use the Agent tool with the named agent type given in each phase; its mandate is already the agent's system prompt. Never pass `subagent_type: "fork"` and never continue the agent with SendMessage after its verdict. If the type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and the mandate prepended.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.

- `spawn_agent` with the default agent type and the prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.

**opencode.** Use the `task` tool. Each call creates a fresh child session, which is the clean context this skill needs.

- If a `code-adversary` / `findings-adversary` subagent is installed (see the plugin README), use it and pass the Review assignment plus payload; the mandate is already its system prompt.
- Otherwise use the built-in `general` subagent with the mandate prepended.

**Copilot CLI.** The plugin registers the same named agents (`adversarial-review:code-adversary`, `adversarial-review:findings-adversary`); use them through its subagent tool when offered, otherwise a fresh generic subagent with the mandate prepended.

**Other agents** with a subagent tool: spawn a fresh generic subagent with the mandate prepended. Without a subagent tool, use the inline Fallback.

**Verdict check and retry.** Validate every reply before using it. The last non-empty line must match the pass's documented format exactly:

- Code Adversary: `^CODE_ADVERSARY_VERDICT: (FOUND BLOCKING \(\d+\)|FOUND ISSUES \(\d+\)|MINOR ONLY \(\d+\)|CLEAN)$`, where the count equals the number of `F<n>` findings in the reply.
- Findings Adversary: `^FINDINGS_ADVERSARY_VERDICT: (SOUND|CORRECTED|ESCAPED_BUG)$`, preceded by one `F<n> —` line for every input finding.

An empty reply, a missing or malformed verdict line, a count that does not match, or a missing `F<n>` line is a malformed verdict. Close that subagent, spawn one fresh subagent for the same pass, and validate again. A second malformed reply is a gate failure: output `Review Verdict: FAILED` (see Output) and stop. Do not run the pass inline to rescue it. The inline Fallback is only for a runtime with no subagent tool or a spawn call that itself errors twice.

## Phase 2 - Code Adversary

Spawn per [Spawning a clean-context subagent](#spawning-a-clean-context-subagent): named agent `adversarial-review:code-adversary`, mandate [references/code-adversary.md](references/code-adversary.md), payload *"Find the bug in this change and prove it. Read only; do not modify files."*

Validate the reply with the verdict check, then close the subagent; nothing else is ever sent to it. The Findings Adversary exists to filter findings that would trigger a fix, so it runs only on a result that needs fixes: when the verdict is `CLEAN` or `MINOR ONLY` (no `blocking:` or `issue:` finding), skip Phase 3 and go to Output with `findings skipped`. Never dispatch the Findings Adversary to refute a clean result.

## Phase 3 - Findings Adversary

Spawn a **new** subagent - never resume, message, or reuse the Code Adversary: named agent `adversarial-review:findings-adversary`, mandate [references/findings-adversary.md](references/findings-adversary.md), payload `Findings to refute:` followed by **only** the numbered `F<n>` finding blocks (label, message, location and, when present, the `*Proof:*` or `*Trace:*` line) copied verbatim from Phase 2. Strip every other line of the Code Adversary's reply - the clean context is the point.

Validate the reply with the verdict check (one `F<n> —` line per input finding, then the final verdict line), then close the subagent.

## Phase 4 - Apply verdicts

- UPHOLD → keep, mark high-confidence.
- DOWNGRADE / REWORD → replace with the corrected finding.
- REMOVE → drop; count it.
- Every `E<n>` escaped bug → a new finding in the output, tagged `(escaped)`. An `ESCAPED_BUG` verdict with no escaped finding in your output means you dropped one - go back and add it.
- Merge duplicates the adversary named.
- A surviving `blocking:` with no `*Proof:*` or `*Trace:*` line did not earn the label: report it as `issue:` and count it as downgraded.

## Output

The verdict comes **first**, on its own line - callers match the first line:

```
Review Verdict: CLEAN
```

or

```
Review Verdict: NEEDS_FIXES
```

or, only after a pass returned a malformed verdict twice,

```
Review Verdict: FAILED
```

- **CLEAN** - no surviving `blocking:` or `issue:`. Suggestions and questions alone stay CLEAN.
- **NEEDS_FIXES** - at least one surviving `blocking:` or `issue:`.
- **FAILED** - a gate failure, never a pass: the second line is `Gate failure: <Code|Findings> Adversary returned no valid verdict after one retry`, no findings follow, and callers treat it as a failed gate rather than as CLEAN.

Then the surviving findings, strongest first, in conventional-comment format, high-confidence ones tagged `(verified)`; a `blocking:` keeps its proof line:

```
**{label}:** {message}
*Location:* `{path/to/file}:{line}`
*Proof:* `{command}` → {observed output}
```

End with one line: `Adversaries: code <CODE_ADVERSARY_VERDICT|malformed> · findings <FINDINGS_ADVERSARY_VERDICT|skipped|malformed> · removed <N> · downgraded <N>`. Nothing after it. The findings verdict grades the findings, not the code - the `Review Verdict:` line is computed from the surviving findings alone.

## Fallback - no subagents

If the runtime has no subagent tool, or the spawn call itself errors on both attempts, run each pass inline as a separate labelled section, following the mandate files linked above. A malformed verdict is not a spawn error and is never rescued inline. Run the inline Findings pass only when the inline Code pass found a `blocking:` or `issue:`. In the Findings pass you MUST re-open every cited `file:line` and re-derive the claim from the source - never verify from memory of having written it. Assume your own mistakes are there. Note `inline` in the final Adversaries line.

## Anti-patterns

- Passing the Code Adversary's reasoning to the Findings Adversary - it then shares the same blind spot
- Reusing one subagent for both passes, or forking the parent conversation into either
- Resuming an adversary after its verdict - for a fix, a re-check or the next revision
- Dispatching the Findings Adversary on a `CLEAN` or `MINOR ONLY` result
- Keeping a `blocking:` that has no executed reproduction or interleaving trace
- Rescuing a malformed verdict with a third attempt or an inline pass
- Padding a clean review - CLEAN is a real, useful verdict
- Reviewing architecture, naming, or dead code - wrong skill, use `/staff-code-review`
- Any prose above the `Review Verdict:` line

## Example invocations

In Codex use `$adversarial-review` in place of `/adversarial-review`.

```
/adversarial-review
/adversarial-review --base origin/release-1.4
/adversarial-review https://github.com/owner/repo/pull/123
/adversarial-review --context issue-42.md
```
