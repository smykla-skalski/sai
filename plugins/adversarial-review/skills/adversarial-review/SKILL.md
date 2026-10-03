---
name: adversarial-review
description: Fast two-pass adversarial code review. A Code Adversary subagent red-teams a diff or PR to find the concrete bug, then a separate Findings Adversary subagent with a clean context tries to refute every finding to cut false positives. Use for routine changes where a full staff review is overkill, or as the review gate inside ship-issue.
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

1. **Code Adversary** - assumes the change is broken and hunts the concrete failure. Mandate: [references/code-adversary.md](references/code-adversary.md).
2. **Findings Adversary** - assumes the Code Adversary is wrong and tries to refute each finding against the source. Mandate: [references/findings-adversary.md](references/findings-adversary.md).

The second pass exists because an unrefuted adversary nit-bombs. It sees only the first pass's findings, never its reasoning, so it cannot inherit the same misread.

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

**Claude Code.** Use the Agent tool with the named agent type given in each phase; its mandate is already the agent's system prompt. If the type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and the mandate prepended.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.

- `spawn_agent` with the default agent type and the prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.

**opencode.** Use the `task` tool. Each call creates a fresh child session, which is the clean context this skill needs.

- If a `code-adversary` / `findings-adversary` subagent is installed (see the plugin README), use it and pass the Review assignment plus payload; the mandate is already its system prompt.
- Otherwise use the built-in `general` subagent with the mandate prepended.

**Copilot CLI.** The plugin registers the same named agents (`adversarial-review:code-adversary`, `adversarial-review:findings-adversary`); use them through its subagent tool when offered, otherwise a fresh generic subagent with the mandate prepended.

**Other agents** with a subagent tool: spawn a fresh generic subagent with the mandate prepended. Without a subagent tool, use the inline Fallback.

**Validation and retry.** If a reply is empty or lacks its required final verdict line, spawn a fresh subagent once more. If that fails too, run the pass inline (see Fallback).

## Phase 2 - Code Adversary

Spawn per [Spawning a clean-context subagent](#spawning-a-clean-context-subagent): named agent `adversarial-review:code-adversary`, mandate [references/code-adversary.md](references/code-adversary.md), payload *"Find the bug in this change and prove it. Read only; do not modify files."*

The reply must end with a `CODE_ADVERSARY_VERDICT:` line. If the verdict is `CLEAN` with no findings, skip Phase 3 and go to Output.

## Phase 3 - Findings Adversary

Spawn a **new** subagent - never resume, message, or reuse the Code Adversary: named agent `adversarial-review:findings-adversary`, mandate [references/findings-adversary.md](references/findings-adversary.md), payload `Findings to refute:` followed by **only** the numbered `F<n>` finding blocks (label, message, location) copied from Phase 2. Strip every other line of the Code Adversary's reply - the clean context is the point.

The reply must have one verdict line per input finding and end with a `FINDINGS_ADVERSARY_VERDICT:` line.

## Phase 4 - Apply verdicts

- UPHOLD → keep, mark high-confidence.
- DOWNGRADE / REWORD → replace with the corrected finding.
- REMOVE → drop; count it.
- Every `E<n>` escaped bug → a new finding in the output, tagged `(escaped)`. An `ESCAPED_BUG` verdict with no escaped finding in your output means you dropped one - go back and add it.
- Merge duplicates the adversary named.

## Output

The verdict comes **first**, on its own line - callers match the first line:

```
Review Verdict: CLEAN
```

or

```
Review Verdict: NEEDS_FIXES
```

- **CLEAN** - no surviving `blocking:` or `issue:`. Suggestions and questions alone stay CLEAN.
- **NEEDS_FIXES** - at least one surviving `blocking:` or `issue:`.

Then the surviving findings, strongest first, in conventional-comment format, high-confidence ones tagged `(verified)`:

```
**{label}:** {message}
*Location:* `{path/to/file}:{line}`
```

End with one line: `Adversaries: code <CODE_ADVERSARY_VERDICT> · findings <FINDINGS_ADVERSARY_VERDICT|skipped> · removed <N> · downgraded <N>`. Nothing after it. The findings verdict grades the findings, not the code - the `Review Verdict:` line is computed from the surviving findings alone.

## Fallback - no subagents

If the runtime has no subagent tool or both spawn attempts fail, run each pass inline as a separate labelled section, following the mandate files linked above. In the Findings pass you MUST re-open every cited `file:line` and re-derive the claim from the source - never verify from memory of having written it. Assume your own mistakes are there. Note `inline` in the final Adversaries line.

## Anti-patterns

- Passing the Code Adversary's reasoning to the Findings Adversary - it then shares the same blind spot
- Reusing one subagent for both passes, or forking the parent conversation into either
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
