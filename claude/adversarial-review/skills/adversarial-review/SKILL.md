---
name: adversarial-review
description: Fast two-pass adversarial code review. A Code Adversary subagent red-teams a diff or PR to find the concrete bug, then a separate Findings Adversary subagent with a clean context tries to refute every finding to cut false positives. Use for routine changes where a full staff review is overkill, or as the review gate inside ship-issue.
argument-hint: "[<pr-url> | <diff-file> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent, Bash, Glob, Grep, Read
user-invocable: true
---

# Adversarial Review

Find the bug, then try to prove the bug report wrong. It answers one question - **is this change correct?** - and answers it hard. It does not evaluate architecture, conventions, dead code, or taste; that is `/staff-code-review`.

Two subagents, opposed, each with a clean context:

1. **Code Adversary** - assumes the change is broken and hunts the concrete failure.
2. **Findings Adversary** - assumes the Code Adversary is wrong and tries to refute each finding against the source.

The second pass exists because an unrefuted adversary nit-bombs. It sees only the first pass's findings, never its reasoning, so it cannot inherit the same misread.

## Arguments

Parse `$ARGUMENTS`:

| Argument | Meaning |
| :-- | :-- |
| `<pr-url>` | Review a GitHub PR |
| `<diff-file>` | Review a saved patch file |
| `--base <ref>` | Review the working tree (committed + uncommitted) against the merge-base with `<ref>` |
| (none) | Same as `--base origin/<default-branch>` |
| `--context <file\|text>` | Task context: issue body, acceptance criteria, PR description. A path is read; anything else is used verbatim |

## Phase 1 - Build the review assignment

Do not read the full diff into your own context; the subagents fetch it themselves. Resolve only what they need:

- **Local (`--base` or none):** resolve the default branch with `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback `origin/main`). `BASE=$(git merge-base <ref> HEAD)`. Diff command: `git diff $BASE`. Files: `git diff --name-only $BASE`. Untracked files (`git ls-files --others --exclude-standard`) are not in the diff; list them separately so the subagents read them whole.
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

## Phase 2 - Code Adversary (subagent)

Spawn one subagent:

1. Try `subagent_type: "adversarial-review:code-adversary"`.
2. If the type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and prepend the full mandate from [../../agents/code-adversary.md](../../agents/code-adversary.md) (skip its frontmatter).

Prompt: the Review assignment plus *"Find the bug in this change and prove it. Read only; do not modify files."* Pass nothing else - not your own reading of the code, not hypotheses.

Validate the reply: it must end with a `CODE_ADVERSARY_VERDICT:` line. If it does not, re-spawn once; if it fails again, run the pass inline (see Fallback).

If the verdict is `CLEAN` with no findings, skip Phase 3 and go to Output.

## Phase 3 - Findings Adversary (fresh subagent)

Spawn a **new** subagent - never resume or message the Code Adversary:

1. Try `subagent_type: "adversarial-review:findings-adversary"`.
2. Fallback: `general-purpose` with the mandate from [../../agents/findings-adversary.md](../../agents/findings-adversary.md) prepended.

Prompt: the Review assignment, then `Findings to refute:` followed by **only** the numbered `F<n>` finding blocks (label, message, location) copied from Phase 2. Strip every other line of the Code Adversary's reply - the clean context is the point.

Validate: one verdict line per input finding and a final `FINDINGS_ADVERSARY_VERDICT:` line. Re-spawn once on a malformed reply, then fall back to inline.

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

If the `Agent` tool is unavailable or both spawn attempts fail, run each pass inline as a separate labelled section, reading the mandate files linked above. In the Findings pass you MUST re-open every cited `file:line` and re-derive the claim from the source - never verify from memory of having written it. Assume your own mistakes are there. Note `inline` in the final Adversaries line.

## Anti-patterns

- Passing the Code Adversary's reasoning to the Findings Adversary - it then shares the same blind spot
- Reusing one subagent for both passes
- Padding a clean review - CLEAN is a real, useful verdict
- Reviewing architecture, naming, or dead code - wrong skill, use `/staff-code-review`
- Any prose above the `Review Verdict:` line

## Example invocations

```
/adversarial-review
/adversarial-review --base origin/release-1.4
/adversarial-review https://github.com/owner/repo/pull/123
/adversarial-review --context issue-42.md
```
