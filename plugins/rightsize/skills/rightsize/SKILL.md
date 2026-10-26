---
name: rightsize
description: "Use this skill to make work the right size. Audit: judge whether a diff, PR, files, architecture, plan, design doc, process or policy is overbuilt or oversimplified: overengineered, premature (microservices, queues or plugins before the need exists), \"justified or complexity for its own sake?\", or a simplification that dropped a safeguard. Write: draft a design doc, ADR or decision log entry, pitch, plan, proposal, spec, user stories, runbook, process, policy or message about work, in a file or the chat, that admits only complexity with a current reason, keeps required safeguards, reads plainly. Rewrite: rework such a document or message the same way, also one earlier in this chat, cutting what it does not need, adding what it lacks, keeping every needed fact. It infers the mode from the conversation and, with no target, uses this session's work, including code the agent wrote. Not for refactors, bug hunts, security reviews, commit messages, PR descriptions, release notes, tone-only edits or cloud sizing."
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. audit is read-only; write and rewrite change only the document. Uses git and gh only to read diffs and pull requests.
argument-hint: "[audit | write | rewrite] [path | PR | branch | pasted text | brief] [--dry-run]"
allowed-tools: AskUserQuestion Bash Edit Glob Grep Read Write
user-invocable: true
metadata:
  short-description: Audit, write and rewrite work at the right size
---

# Rightsize

Make work the minimum adequate system: it meets its required outcomes and constraints with the least burden. Overbuilt work has what it does not need; oversimplified work lacks what it does need. All three modes use the rules in [references/rules.md](references/rules.md):

- audit: check work, code or a document, and report the broken rules. Read only.
- write: write a new document or message, into a file or into this chat, whose content passes the rules and whose prose is plain.
- rewrite: rework an existing document or message the same way, a file, pasted text or a message earlier in this conversation, and keep every fact it needs.

Run in this conversation, never in a subagent: only this conversation holds the work, the material and your notes, and only it can ask the user.

## Agent compatibility

Paths are relative to this skill's directory. Outside Claude Code:

| Claude Code feature | Fallback |
| :-- | :-- |
| AskUserQuestion | Ask in plain text and wait for the answer |
| Edit and Write | Use the agent's file-edit tool (`apply_patch` in Codex). If the sandbox blocks the write, request escalation |
| Arguments | Take them from the user's request |

## Arguments

Invocation arguments: `$ARGUMENTS`

If that line is empty or still shows the literal placeholder, take the subcommand, target and flags from the user's request. An empty request is normal: the conversation then holds the work and the intent.

| Subcommand or flag | Purpose |
| :-- | :-- |
| `audit` | Audit the target and report broken rules, issues, gaps and suggestions |
| `write` | Write a new document or message from the brief and the material it names |
| `rewrite` | Rewrite the target document or message and report the content changes |
| `--dry-run` | write and rewrite: print the text in chat instead of writing the file |

If the first word is `audit`, `write` or `rewrite`, it is the subcommand, and the rest is the target or the brief. Otherwise infer the subcommand from the arguments, then from the user's latest messages in this conversation. Use the first case that applies:

1. `write`: they ask for a document or message that does not exist yet ("we need a design doc for this", "turn these notes into a plan", "write the announcement"), or they collected material for one and no draft exists.
2. `rewrite`: they ask to change an existing document or message, in a file, pasted or earlier in this conversation: shorten, simplify, slim down, clean up, restructure or fix it. A document or message that you just wrote is not a reason to rewrite it.
3. `audit`: they ask whether work is too complex, too simple or justified; the target is code, a diff, a PR or a branch; or nothing points to write or rewrite.

Two cases equally likely, one of which changes a file: ask once with AskUserQuestion. State the inferred subcommand in the first line of your reply only when the user named none and the case was not plain.

## Modes

Read the mode's file in full before you start, and follow it:

- audit: [references/audit.md](references/audit.md)
- write: [references/write.md](references/write.md)
- rewrite: [references/rewrite.md](references/rewrite.md)
