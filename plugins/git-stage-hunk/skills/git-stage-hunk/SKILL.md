---
name: git-stage-hunk
description: Stage only specific hunks from the working tree for selective commits. Use when a file has changes from multiple sessions, parallel AI agents, or mixed user and agent edits and you need to commit only the changes made by the current session. Use when git add -p is unavailable or when you need non-interactive partial staging. Lists hunks with IDs, stages by hunk ID, file, regex pattern, or line range.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and python3; patchutils is optional. Writes the git index of the current repository.
argument-hint: "[--list [--file PATH] [--split] [--table]] [--hunk H1,H3.1,H5:5-10] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--verify] [--dry-run] [--table]"
allowed-tools: AskUserQuestion Bash
user-invocable: true
metadata:
  short-description: Stage selected diff hunks safely
---


# git-stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Replaces `git add -p` in scripted and multi-agent environments. Use when only some changes in a file belong in the current commit, when multiple sessions or agents modified the same file and you need to commit selectively, or when `git add -p` is unavailable because there is no TTY.

The heavy lifting happens in the Python script. Your first action MUST be Bash - call the script directly, then present the output. Do not re-implement git diff/apply logic yourself.

`<skill-dir>` in every command below is the absolute path of this skill's directory (the one holding this SKILL.md). In Claude Code it is `${CLAUDE_SKILL_DIR}`. Run the commands from the root of the user's repository and call the script by that absolute path, keeping the double quotes: the script stages changes in the repository of the current working directory, so never `cd` into the skill directory.

```
"<skill-dir>/scripts/git-stage-hunk.py" --list --table
```

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Quick workflow
2. Agent compatibility
3. Preprocessed context
4. Arguments
5. Workflow
6. Hunk ID scheme
7. Error handling
8. Dependencies
9. Example invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
