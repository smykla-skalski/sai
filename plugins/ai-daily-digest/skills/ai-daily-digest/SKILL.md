---
name: ai-daily-digest
description: Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters. Use daily for staying current on AI developments. Depends on current sources, so it browses and verifies dates before drafting and never writes from memory. Not for timeless explanations of how a model or technique works.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs web search or fetch, a shell, and write access to the XDG data directory. Notion publishing needs a Notion MCP server.
argument-hint: "[--focus technical|business|engineering|leadership|all] [--notion-page-id ID] [--no-notion] [--obsidian-vault PATH]"
allowed-tools: Agent AskUserQuestion Bash Read Task ToolSearch WebFetch WebSearch Write
user-invocable: true
disable-model-invocation: true
metadata:
  short-description: Assemble a daily AI news digest
---


# AI Daily Digest Skill

Generate comprehensive daily AI news digest with technical, business, and engineering coverage.

This is a current-events skill: its value is dated, verifiable sources. Always browse before drafting and never fabricate a date, URL, or headline. For "how does X work" questions, answer directly instead of running this workflow.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Configuration
4. Preprocessed context
5. Persistent Data Directory
6. State Files
7. Workflow
8. Output Requirements
9. Error Handling
10. Newsletter Integration
11. Example Invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
