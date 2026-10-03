---
name: adversarial-test
description: Adversarial manual testing of a change. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) in isolated state, and attacks boundaries, malformed input, repetition, and adjacent flows; every reproduction is then rerun to drop hallucinated failures. Use to prove a branch or PR actually works before merging, or as the testing gate inside ship-issue.
argument-hint: "[<pr-url> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent, Bash, Glob, Grep, Read
user-invocable: true
---

# Adversarial Test

Prove the change does **not** do what the task says - by running it. It answers one question - **does this change work for a user?** - and answers it with commands and output, not by reading code. Code correctness review is `/adversarial-review`.

One subagent with a clean context, then a check by you:

1. **Test Adversary** - derives acceptance criteria, runs the real surface, attacks it, and reports self-contained reproductions.
2. **Reproduction check** - you rerun each reproduction verbatim in a fresh shell. A failure that never happened does not survive.

The subagent gets a clean context so it tests the task, not the implementer's belief about the task.

## Arguments

Parse `$ARGUMENTS`:

| Argument | Meaning |
| :-- | :-- |
| `<pr-url>` | Test a GitHub PR's head |
| `--base <ref>` | Test the working tree; the change is everything since the merge-base with `<ref>` |
| (none) | Same as `--base origin/<default-branch>` |
| `--context <file\|text>` | Task context: issue body, acceptance criteria, PR description. A path is read; anything else is used verbatim |

## Phase 1 - Build the test assignment

Do not run or read the product yourself; the subagent does. Resolve only what it needs:

- **Local (`--base` or none):** resolve the default branch with `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback `origin/main`). `BASE=$(git merge-base <ref> HEAD)`. Run location: the repository root. Diff command: `git diff $BASE`. Files: `git diff --name-only $BASE` plus untracked files (`git ls-files --others --exclude-standard`).
- **PR URL:** `gh pr view <url> --json number,headRefOid,baseRefName,title,body`. If local `HEAD` is `headRefOid` and the tree is clean, run from the repository root. Otherwise `git fetch origin pull/<number>/head` and `git worktree add --detach <tmpdir> <headRefOid>`; run from that worktree and remove it after Phase 3. Diff command: `gh pr diff <url>`. Use the PR title and body as context when `--context` is absent.

If the file list is empty, output `Test Verdict: PASS` followed by `Nothing to test: empty diff.` and stop.

If no context was given and none can be derived (no PR body), proceed; the subagent derives criteria from the diff and says so.

Assemble one **Test assignment** block:

```
Repository: <absolute repo root>
Run from: <absolute path of the checkout to run>
Diff command: <command>
Changed files:
<one per line>
Task context:
<context, or "none">
```

## Phase 2 - Test Adversary (subagent)

Spawn one subagent:

1. Try `subagent_type: "adversarial-test:test-adversary"`.
2. If the type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and prepend the full mandate from [../../agents/test-adversary.md](../../agents/test-adversary.md) (skip its frontmatter).

Prompt: the Test assignment plus *"Prove this change does not satisfy the task by running it. Do not edit tracked files."* Pass nothing else - not your own reading of the code, not what you expect to work.

Validate the reply: it must have a `Criteria:` list and end with a `TEST_ADVERSARY_VERDICT:` line. If not, spawn a fresh subagent once more; if it fails again, run the pass inline (see Fallback).

Reject a `PASS` whose criteria cite only automated tests, lint, build, or grep while a runnable surface exists - respawn once with *"Your evidence was static. Run the real surface."* appended. If it still cannot run the surface, treat it as `BLOCKED`.

## Phase 3 - Reproduction check

For each `R<n>`:

1. Run its reproduction verbatim in a fresh shell from the run location, with a timeout.
2. **Reproduced** (actual matches the report) → keep, tag `(confirmed)`.
3. **Did not reproduce** → run it twice more. Fails at least once → keep, tag `(flaky)`; flakiness is a bug. Passes all three → drop as unreproducible and count it.
4. **Reproduction itself is broken** (typo, missing setup step) → fix only the harness, never the product, and rerun once; still broken → drop and count it.

Clean up any processes and temp state the reproductions left.

## Output

The verdict comes **first**, on its own line - callers match the first line:

```
Test Verdict: PASS
```

```
Test Verdict: FAIL
```

```
Test Verdict: BLOCKED
```

- **PASS** - every criterion passed on the real surface and no reproduction survived Phase 3.
- **FAIL** - at least one surviving reproduction.
- **BLOCKED** - the real surface could not be exercised; the next line names the blocker and the exact human action that unblocks it.

Then the criteria table from the subagent, the surface line, and the surviving reproductions, strongest first:

```
**{blocking|issue}:** <criterion or flow>, expected <X>, got <Y> (confirmed|flaky)
Reproduction:
<commands>
```

End with one line: `Tester: <subagent verdict value, e.g. FAIL (2)> · confirmed <N> · flaky <N> · dropped <N>`. Nothing after it.

## Fallback - no subagents

If the `Agent` tool is unavailable or both spawn attempts fail, run the pass inline following the mandate file. Derive the criteria from the task context **before** reading the diff, so the implementation does not shape them. Assume your own mistakes are there. Phase 3 still applies. Note `inline` in the final Tester line.

## Anti-patterns

- Passing the implementer's reasoning or test plan to the subagent - it then tests what was built, not what was asked
- Accepting a PASS backed only by unit tests, lint, or build output
- Fixing product code inside this skill - report, the caller fixes
- Running against the user's real config, data, or shared services
- Leaving servers, containers, or worktrees running after the verdict
- Any prose above the `Test Verdict:` line

## Example invocations

```
/adversarial-test
/adversarial-test --base origin/release-1.4
/adversarial-test https://github.com/owner/repo/pull/123
/adversarial-test --context issue-42.md
```
