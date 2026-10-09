---
name: adversarial-test
description: Adversarial manual testing of a change. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) in isolated state, and attacks boundaries, malformed input, repetition, and adjacent flows; every reproduction is then rerun to drop hallucinated failures. Use to prove a branch or PR actually works before merging, or as the testing gate inside ship-it.
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
| Named agent `adversarial-test:test-adversary` | Claude Code and Copilot CLI register it from the plugin's `agents/` directory. Codex and opencode do not; there, or whenever the type is unknown, spawn a generic subagent with the full mandate from [references/test-adversary.md](references/test-adversary.md) prepended (see Phase 2) |
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
- **Evidence dir:** `${XDG_DATA_HOME:-$HOME/.local/share}/sai/adversarial-test/<short base or head sha>-<UTC timestamp>`; `mkdir -p` it. It outlives the run and holds the screenshots the verdict cites.

If the file list is empty, output `Test Verdict: PASS` followed by `Nothing to test: empty diff.` and stop.

If no context was given and none can be derived (no PR body), proceed; the subagent derives criteria from the diff and says so.

Assemble one **Test assignment** block:

```
Repository: <absolute repo root>
Run from: <absolute path of the checkout to run>
Evidence dir: <absolute path; outlives the run>
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
2. If the type is unknown (plugin loaded without agent registration), use `subagent_type: "general-purpose"` with the mandate prepended.

**Codex.** Use the native agent tools only (`spawn_agent` / `wait_agent` / `close_agent`); never nested `codex exec` or shell-based agent probing.

- `spawn_agent` with the default agent type and the mandate-prepended prompt as the message. Do not fork or inherit the parent conversation; if the tool offers a context-forking option, leave it off.
- `wait_agent` until it finishes, then `close_agent` immediately - completed agents do not free their thread slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)).
- Agents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Validate the reply (below) before using it.
- Starting servers, binding ports, and network access may need sandbox escalation. Request it with a concise justification rather than downgrading to static evidence.

**opencode.** Use the `task` tool; each call creates a fresh child session, which is the clean context this skill needs. If a `test-adversary` subagent is installed (see the plugin README), use it with the Test assignment and the instruction. Otherwise use the built-in `general` subagent with the mandate prepended.

**Validation and retry.** The reply must have a `Criteria:` list, an `Untested:` line whenever a criterion is UNTESTED, and end with a `TEST_ADVERSARY_VERDICT:` line. If it is empty or malformed, spawn a fresh subagent once more; if that fails too, run the pass inline (see Fallback).

Reject a `PASS` whose criteria cite only automated tests, lint, build, or grep while a runnable surface exists - spawn a fresh subagent once with *"Previous attempt used static evidence only. Run the real surface, or mark each criterion you cannot run UNTESTED with the named environmental blocker."* appended. A retry that names an environmental blocker makes that criterion UNTESTED. A retry that still cites only static evidence for a surface that runs is malformed test execution: discard it and run the inline fallback. If the inline fallback also returns static-only evidence without an environmental blocker, return no verdict and report that the test gate has no valid execution; never turn tester noncompliance into `BLOCKED`.

**Check the screenshot.** When the changed files include UI code (templates, components, stylesheets, view or pane sources), the `Evidence:` line must name a screenshot file that exists, its image pixel size, viewport dimensions of at least 2560x1440, and the capture command or window-measurement output that proves those viewport dimensions. Check the image pixels independently (`sips -g pixelWidth -g pixelHeight <file>` on macOS, `identify <file>` elsewhere); never infer viewport size from image pixels because device scaling can enlarge them. If the evidence omits any item and the `Untested:` line gives no environmental blocker for the capture (no display, no headless browser, an unreachable pane), spawn a fresh subagent once with *"Previous attempt did not prove a changed UI viewport of 2560x1440 or larger. Capture it and report the image dimensions, viewport dimensions and capture command or measurement, or name the environmental blocker."* appended. A retry with incomplete proof is malformed test execution: discard it and run the inline fallback. If the inline fallback also omits the runnable capture proof without an environmental blocker, return no verdict and report that the test gate has no valid execution.

**Reclassify a misfiled blocker.** A `BLOCKED` whose blocker is environmental - sandbox, network, package registry, a missing or fake tool, the build toolchain, a hook false positive, a stop directive, an unreachable display or pane - is not BLOCKED: tag each affected criterion UNTESTED with that blocker, and the verdict is `FAIL` when a reproduction survives Phase 3, otherwise `PASS (partial)`. `BLOCKED` stands only for a product precondition that a human must supply (credentials, hardware, an approval, data).

## Phase 3 - Reproduction check

For each `R<n>`:

1. Run its reproduction verbatim in a fresh shell from the run location, with a timeout.
2. **Reproduced** (actual matches the report) → keep, tag `(confirmed)`.
3. **Did not reproduce** → run it twice more. Fails at least once → keep, tag `(flaky)`; flakiness is a bug. Passes all three → drop as unreproducible and count it.
4. **Reproduction itself is broken** (typo, missing setup step) → fix only the harness, never the product, and rerun once; still broken → drop and count it.

Clean up any processes and temp state the reproductions left. Leave the evidence directory in place; it holds the screenshots the verdict cites.

## Output

The verdict comes **first**, on its own line - callers match the first line:

```
Test Verdict: PASS
```

```
Test Verdict: PASS (partial)
Untested: AC<n> - <blocker>; AC<m> - <blocker>
```

```
Test Verdict: FAIL
```

```
Test Verdict: BLOCKED
```

- **PASS** - every criterion passed on the real surface and no reproduction survived Phase 3.
- **PASS (partial)** - no reproduction survived and at least one criterion is UNTESTED for an environmental reason; the second line lists each with its blocker. Callers treat it as passing and carry the `Untested:` line into the PR.
- **FAIL** - at least one surviving reproduction, whatever else is UNTESTED.
- **BLOCKED** - a product precondition that only a human can supply is missing; the next line names the exact human action.

Then the criteria table from the subagent, the surface and evidence lines (screenshot paths with image pixels, viewport dimensions and capture proof), and the surviving reproductions, strongest first:

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
- Returning BLOCKED for a sandbox, tooling, or build failure - that is UNTESTED with the blocker, and the verdict is PASS (partial) or FAIL
- Screenshotting a UI change below 2560x1440, or passing a UI criterion without a screenshot
- Any prose above the `Test Verdict:` line

## Example invocations

```
/adversarial-test
/adversarial-test --base origin/release-1.4
/adversarial-test https://github.com/owner/repo/pull/123
/adversarial-test --context issue-42.md
```

In Codex invoke it as `$adversarial-test` with the same arguments.
