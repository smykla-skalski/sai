---
name: adversarial-review
description: Fast two-pass adversarial code review for Codex and OpenCode. A Code Adversary subagent red-teams a diff or PR to find the concrete bug, then a separate Findings Adversary subagent with a clean context tries to refute every finding to cut false positives. Use for routine changes where a full staff review is overkill, or as the review gate inside ship-issue.
metadata:
  short-description: Two-pass adversarial code review in clean-context subagents
---

# Adversarial Review

Find the bug, then try to prove the bug report wrong. It answers one question - **is this change correct?** - and answers it hard. It does not evaluate architecture, conventions, dead code, or taste; that is staff-code-review.

Two subagents, opposed, each with a clean context:

1. **Code Adversary** - assumes the change is broken and hunts the concrete failure. Mandate: [references/code-adversary.md](references/code-adversary.md).
2. **Findings Adversary** - assumes the Code Adversary is wrong and tries to refute each finding against the source. Mandate: [references/findings-adversary.md](references/findings-adversary.md).

The second pass exists because an unrefuted adversary nit-bombs. It sees only the first pass's findings, never its reasoning, so it cannot inherit the same misread.

This skill is self-contained and runs on Codex and OpenCode. The Claude Code plugin lives in `claude/adversarial-review/` and uses named agents with the same mandates.

## Arguments

Parse from the user request:

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

Each pass is one subagent whose prompt is: the full mandate file content, then the Review assignment, then the pass-specific payload. Nothing else - not your own reading of the code, not hypotheses, not this conversation.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.
- `spawn_agent` with the default agent type and the prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.
- The two passes are sequential, so this never needs more than one extra thread.

**OpenCode.** Use the `task` tool. Each call creates a fresh child session, which is the clean context this skill needs.
- If a `code-adversary` / `findings-adversary` subagent is installed (see Installation), use it and pass the Review assignment plus payload; the mandate is already its system prompt.
- Otherwise use the built-in `general` subagent with the full mandate prepended.

**Validation and retry.** If a reply is empty or lacks its required final verdict line, spawn a fresh subagent once more. If that fails too, run the pass inline (see Fallback).

## Phase 2 - Code Adversary

Spawn per "Spawning a clean-context subagent" with [references/code-adversary.md](references/code-adversary.md) and the payload *"Find the bug in this change and prove it. Read only; do not modify files."*

The reply must end with a `CODE_ADVERSARY_VERDICT:` line. If the verdict is `CLEAN` with no findings, skip Phase 3 and go to Output.

## Phase 3 - Findings Adversary

Spawn a **new** subagent - never reuse or follow up with the Code Adversary - with [references/findings-adversary.md](references/findings-adversary.md) and the payload `Findings to refute:` followed by **only** the numbered `F<n>` finding blocks (label, message, location) copied from Phase 2. Strip every other line of the Code Adversary's reply - the clean context is the point.

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

If the runtime has no subagent tool or both spawn attempts fail, run each pass inline as a separate labelled section using the same mandate files. In the Findings pass you MUST re-open every cited `file:line` and re-derive the claim from the source - never verify from memory of having written it. Assume your own mistakes are there. Note `inline` in the final Adversaries line.

## Installation

- **Codex:** install `adversarial-review@sai` from the SAI marketplace (`plugins/adversarial-review/`), or symlink this directory to `~/.agents/skills/adversarial-review`. Invoke with `$adversarial-review`.
- **OpenCode:** symlink this directory to `~/.config/opencode/skills/adversarial-review` (OpenCode also scans `~/.agents/skills/`). For read-only named subagents, create `~/.config/opencode/agents/code-adversary.md` and `findings-adversary.md` with frontmatter `description`, `mode: subagent`, and `permission: { edit: deny }`, followed by the matching mandate file body.

## Anti-patterns

- Passing the Code Adversary's reasoning to the Findings Adversary - it then shares the same blind spot
- Reusing one subagent for both passes, or forking the parent conversation into either
- Padding a clean review - CLEAN is a real, useful verdict
- Reviewing architecture, naming, or dead code - wrong skill
- Any prose above the `Review Verdict:` line
