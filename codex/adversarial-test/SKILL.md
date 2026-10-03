---
name: adversarial-test
description: Adversarial manual testing of a change for Codex and OpenCode. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) in isolated state, and attacks boundaries, malformed input, repetition, and adjacent flows; every reproduction is then rerun to drop hallucinated failures. Use to prove a branch or PR actually works before merging, or as the testing gate inside ship-issue.
metadata:
  short-description: Adversarial manual testing in a clean-context subagent
---

# Adversarial Test

Prove the change does **not** do what the task says - by running it. It answers one question - **does this change work for a user?** - and answers it with commands and output, not by reading code. Code correctness review is adversarial-review.

One subagent with a clean context, then a check by you:

1. **Test Adversary** - derives acceptance criteria, runs the real surface, attacks it, and reports self-contained reproductions. Mandate: [references/test-adversary.md](references/test-adversary.md).
2. **Reproduction check** - you rerun each reproduction verbatim in a fresh shell. A failure that never happened does not survive.

The subagent gets a clean context so it tests the task, not the implementer's belief about the task.

This skill is self-contained and runs on Codex and OpenCode. The Claude Code plugin lives in `claude/adversarial-test/` and uses a named agent with the same mandate.

## Arguments

Parse from the user request:

| Argument | Meaning |
| :-- | :-- |
| `<pr-url>` | Test a GitHub PR's head |
| `--base <ref>` | Test the working tree; the change is everything since the merge-base with `<ref>` |
| (none) | Same as `--base origin/<default-branch>` |
| `--context <file\|text>` | Task context: issue body, acceptance criteria, PR description. A path is read; anything else is used verbatim |

## Phase 1 - Build the test assignment

Do not run or read the product yourself; the subagent does. Resolve only what it needs:

- **Local (`--base` or none):** resolve the default branch with `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback `origin/main`). `BASE=$(git merge-base <ref> HEAD)`. Run location: the repository root. Diff command: `git diff <BASE sha>`. Files: `git diff --name-only <BASE sha>` plus untracked files (`git ls-files --others --exclude-standard`).
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

## Spawning a clean-context subagent

The subagent prompt is: the full mandate file content, then the Test assignment, then *"Prove this change does not satisfy the task by running it. Do not edit tracked files."* Nothing else - not your own reading of the code, not what you expect to work, not this conversation.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.
- `spawn_agent` with the default agent type and the prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.
- Starting servers, binding ports, and network access may need sandbox escalation. Request it with a concise justification rather than downgrading to static evidence.

**OpenCode.** Use the `task` tool. Each call creates a fresh child session, which is the clean context this skill needs.
- If a `test-adversary` subagent is installed (see Installation), use it and pass the Test assignment plus the instruction; the mandate is already its system prompt.
- Otherwise use the built-in `general` subagent with the full mandate prepended.

**Validation and retry.** The reply must have a `Criteria:` list and end with a `TEST_ADVERSARY_VERDICT:` line. If it is empty or malformed, spawn a fresh subagent once more. If that fails too, run the pass inline (see Fallback).

## Phase 2 - Test Adversary

Spawn per "Spawning a clean-context subagent".

Reject a `PASS` whose criteria cite only automated tests, lint, build, or grep while a runnable surface exists - spawn a fresh subagent once with *"Previous attempt used static evidence only. Run the real surface."* appended. If it still cannot run the surface, treat it as `BLOCKED`.

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

If the runtime has no subagent tool or both spawn attempts fail, run the pass inline following the mandate file. Derive the criteria from the task context **before** reading the diff, so the implementation does not shape them. Assume your own mistakes are there. Phase 3 still applies. Note `inline` in the final Tester line.

## Installation

- **Codex:** install `adversarial-test@sai` from the SAI marketplace (`plugins/adversarial-test/`), or symlink this directory to `~/.agents/skills/adversarial-test`. Invoke with `$adversarial-test`.
- **OpenCode:** symlink this directory to `~/.config/opencode/skills/adversarial-test` (OpenCode also scans `~/.agents/skills/`). For a named subagent, create `~/.config/opencode/agents/test-adversary.md` with frontmatter `description` and `mode: subagent`, followed by the mandate file body. Leave bash allowed - the tester must run the product.

## Anti-patterns

- Passing the implementer's reasoning or test plan to the subagent - it then tests what was built, not what was asked
- Forking the parent conversation into the subagent
- Accepting a PASS backed only by unit tests, lint, or build output
- Fixing product code inside this skill - report, the caller fixes
- Running against the user's real config, data, or shared services
- Leaving servers, containers, or worktrees running after the verdict
- Any prose above the `Test Verdict:` line
