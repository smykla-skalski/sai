---
name: adversarial-test
description: Adversarial manual testing of a change. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) in isolated state, and attacks boundaries, malformed input, repetition, and adjacent flows; every reproduction is then rerun to drop hallucinated failures. Use to prove a branch or PR actually works before merging, or as the testing gate inside ship-issue.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git, a shell that can run the product under test, and gh for PR targets.
argument-hint: "[<pr-url> | --base <ref>] [--context <file|text>]"
allowed-tools: Agent Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Adversarial manual testing in a clean-context subagent
---

# Adversarial Test

Prove the change does **not** do what the task says - by running it. It answers one question - **does this change work for a user?** - and answers it with commands and output, not by reading code. Code correctness review is the `adversarial-review` skill.

One subagent with a clean context, then a check by you:

1. **Test Adversary** - derives acceptance criteria, runs the real surface, attacks it, and reports self-contained reproductions. Mandate: [references/test-adversary.md](references/test-adversary.md).
2. **Reproduction check** - you rerun each reproduction verbatim in a fresh shell. A failure that never happened does not survive.

The subagent gets a clean context so it tests the task, not the implementer's belief about the task.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the PR URL and flags from the user's request |
| AskUserQuestion | Not used; the skill never stops for input |
| Named agent `adversarial-test:test-adversary` | Claude Code and Copilot CLI register it from the plugin's `agents/` directory. Elsewhere, or when the type is unknown, spawn a generic subagent with the full mandate from [references/test-adversary.md](references/test-adversary.md) prepended (see Phase 2) |
| Subagent tool (Agent) | Codex: one `spawn_agent` call, waited on and closed before Phase 3. opencode: the `task` tool. No subagent tool, or both spawn attempts fail: run the pass inline yourself (see Fallback) |
| `context: fork` | Not used |

The skill spawns at most one subagent at a time, so it runs sequentially on every agent.

## Arguments

Parse from `$ARGUMENTS`:

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

## Phase 2 - Test Adversary (subagent)

The instruction for the subagent is: *"Prove this change does not satisfy the task by running it. Do not edit tracked files."* Pass the Test assignment and the instruction, nothing else - not your own reading of the code, not what you expect to work, not this conversation. When the mandate is not already the subagent's system prompt, prepend the full content of [references/test-adversary.md](references/test-adversary.md).

**Claude Code and Copilot CLI.**

1. Try `subagent_type: "adversarial-test:test-adversary"`; its system prompt is the mandate.
2. If the type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and the mandate prepended.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.

- `spawn_agent` with the default agent type and the mandate-prepended prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.
- Starting servers, binding ports, and network access may need sandbox escalation. Request it with a concise justification rather than downgrading to static evidence.

**opencode.** Use the `task` tool; each call creates a fresh child session, which is the clean context this skill needs. If a `test-adversary` subagent is installed (see the plugin README), use it with the Test assignment and the instruction. Otherwise use the built-in `general` subagent with the mandate prepended.

**Validation and retry.** The reply must have a `Criteria:` list and end with a `TEST_ADVERSARY_VERDICT:` line. If it is empty or malformed, spawn a fresh subagent once more; if that fails too, run the pass inline (see Fallback).

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

If the agent has no subagent tool or both spawn attempts fail, run the pass inline following [references/test-adversary.md](references/test-adversary.md). Derive the criteria from the task context **before** reading the diff, so the implementation does not shape them. Assume your own mistakes are there. Phase 3 still applies. Note `inline` in the final Tester line.

## Anti-patterns

- Passing the implementer's reasoning or test plan to the subagent - it then tests what was built, not what was asked
- Forking the parent conversation into the subagent
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

In Codex invoke it as `$adversarial-test` with the same arguments.
