---
name: promptgen
description: Use when turning rough instructions into optimized, evidence-based AI prompts for system prompts, task prompts, coding-agent instructions, tools, eval graders, subagent briefings, or prompt-improvement work. Copies to clipboard.
argument-hint: "<prompt-description> [--for claude|gpt|codex|generic] [--research light|deep] [--verbose] [--no-copy] [--examples] [--raw]"
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Clipboard copy needs bash plus pbcopy (macOS), clip (Windows), or wl-copy, xclip, xsel or clip.exe (Linux, WSL); without one the prompt is only printed.
allowed-tools: AskUserQuestion Bash Read Task
user-invocable: true
metadata:
  short-description: Turn rough asks into strong prompts
---


# Promptgen

Generate optimized, evidence-based prompts from rough human instructions. Built on Anthropic / OpenAI guidance through April 2026, the 2025-2026 academic literature (Mollick / Wharton Prompting Science Reports 1-4, Chroma context-rot research, GEPA, IFScale, "Reasoning Models Struggle to Control CoT"), Simon Willison's lethal trifecta and Meta's Rule of Two, and current agent / coding-agent patterns (AGENTS.md, SKILL.md, three-agent harness, ACI design).

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Responsibility boundary
4. Workflow
5. Example invocations
6. Error handling

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
