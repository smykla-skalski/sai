---
name: generate-claude-md
description: Generate a lean, high-signal CLAUDE.md for a repository from codebase analysis. Grounded in Anthropic best practices and empirical studies; built to pass review-claude-md (a bundled validator enforces the same critical checks). Use when the user asks to "generate CLAUDE.md", "create a CLAUDE.md", "write a CLAUDE.md", "init CLAUDE.md", "scaffold CLAUDE.md", or "bootstrap CLAUDE.md" for a project.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs python3 for the bundled validator; no network access.
argument-hint: "[path/to/repo] [--output PATH] [--update] [--force] [--rules] [--dry-run]"
allowed-tools: Agent Bash Edit Glob Grep Read Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Generate a lean CLAUDE.md for a repo
---


# Generate CLAUDE.md

Build a project-specific CLAUDE.md that earns every line: exact commands, an
architecture map, real gotchas, and enforced boundaries — and nothing Claude
already knows. The goal is the inverse of naive `/init` output: short, specific,
and free of README duplication, directory trees, and generic filler.

This skill is the generator counterpart to the `review-claude-md` plugin. It
targets the same rubric the reviewer audits against. The bundled validator
(Phase 7) deterministically gates the mechanical checks — commands present,
length, no README duplication, no generic advice, no directory tree, bullets —
which are all of the reviewer's Critical checks, so a passing file cannot earn a
review FAIL verdict. The remaining quality (architecture as relationships, domain
mapping, real gotchas, style deltas) is your job during synthesis. Read
[references/principles.md](references/principles.md) in full before synthesizing —
it is the source of truth for every rule below.

Not for auditing an existing CLAUDE.md against a checklist (that is
`review-claude-md`) or for generic markdown authoring.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Write safety (read first)
4. Workflow
5. Error handling
6. Example invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
