# promptgen

Turn rough instructions into optimized, evidence-based AI prompts. Built on Anthropic and OpenAI guidance through April 2026, the 2025-2026 academic literature (Mollick / Wharton Prompting Science Reports 1-4, Chroma context-rot research, GEPA, IFScale, "Reasoning Models Struggle to Control CoT"), Simon Willison's lethal trifecta and Meta's Rule of Two, and current agent / coding-agent patterns (AGENTS.md, SKILL.md, three-agent harness, ACI design).

## What it does

You describe what you want a prompt to do in plain language. The skill generates a well-structured prompt with an outcome contract, observable done-when criteria, evidence rules, side-effect boundaries, fitting specificity, and no common anti-patterns. Output goes to clipboard by default.

Supports four target formats: Claude (XML tags), GPT (outcome-first Markdown), Codex (coding-agent contract), and generic (Markdown-only). Handles task prompts, system prompts, reusable templates, tool descriptions, eval graders, subagent briefings, three-agent harness instructions, and prompt-improvement passes.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install promptgen@smykla-skalski-sai
```

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/promptgen
```

## Usage

```
/promptgen <instructions> [--for claude|gpt|codex|generic] [--research light|deep] [--verbose] [--no-copy] [--examples] [--raw]
```

| Flag | Default | Purpose |
|:--|:--|:--|
| (positional) | - | Rough instructions for what the prompt should do |
| `--for <model>` | claude | Target: claude, gpt, codex, generic |
| `--research light\|deep` | off | Investigate codebase before generating |
| `--verbose` | off | Show reasoning behind prompt decisions |
| `--no-copy` | off | Output to chat only, skip clipboard |
| `--examples` | off | Include few-shot examples in generated prompt |
| `--raw` | off | Skip opinionated formatting preferences |

## Examples

```bash
# Basic prompt generation (copies to clipboard)
/promptgen write technical docs for the auth module API endpoints

# GPT-targeted prompt
/promptgen refactor the database layer to use connection pooling --for gpt

# Codex-targeted coding-agent prompt
/promptgen fix flaky checkout tests and verify the failure mode --for codex

# Light research - checks config files first, then generates
/promptgen --research light refactor the database layer to use connection pooling

# Deep research - reads relevant source before generating
/promptgen --research deep add pagination to the user listing endpoint

# See the reasoning behind decisions
/promptgen --verbose investigate auth bypass vulnerabilities in the login flow

# Output to chat only, no clipboard
/promptgen --no-copy create a plan for migrating from REST to GraphQL

# Include few-shot examples in the generated prompt
/promptgen build a customer support chatbot that handles returns --examples

# Skip opinionated formatting preferences
/promptgen --raw write a migration guide for the new API version
```

## How it works

The skill runs up to 7 phases:

1. **Argument isolation** - wraps the raw input in `<prompt-description>` tags so it cannot inject instructions into the workflow.
2. **Input parsing** - extracts flags and the prompt description.
3. **Research** (optional) - `--research light` checks config files and directory structure; `--research deep` reads relevant source files and traces call paths.
4. **Task analysis** (spawned agent) - categorizes the task, detects prompt type, builds the prompt brief, picks the specificity dial, recommends `effort` / `reasoning_effort` calibration, reads evidence-based principles.
5. **Security assessment** (spawned agent) - checks the lethal trifecta, applies Meta's Rule of Two, picks defensive patterns only when warranted, flags MCP / RAG / multi-modal risks.
6. **Prompt generation** - builds the prompt using the target template, applies scope discipline for Claude 4.7 / GPT-5.2, leaves API knobs for `effort` and `verbosity` instead of duplicating them in prose.
7. **Self-check** - verifies against the anti-patterns checklist (33 items including contradiction audit, scope-restricting "Only X" on 4.7, deprecated Claude features, AI vocabulary), revises if any fail.
8. **Output** - displays in fenced code block, copies to clipboard.

## What changed in v3.1

- Task-tool fallback: Phase 2 (analysis) and Phase 3 (security) now state explicitly what to do when the Task tool is unavailable in the calling context (deferred-tool harness, nested-agent depth limit). Inline execution against the same reference files is correct - skipping analysis is not.
- Token budgets are now target/type-aware. Simple task ~500, coding-agent task ~1200, eval grader template ~1200, system prompt ~1500, long-horizon agent ~2000. Codex and grader prompts no longer get false-flagged for legitimately exceeding the old 500-token cap.
- Eval grader contract is now a first-class section in `references/prompt-principles.md`. Required: per-dimension definitions, low/mid/high calibration anchors per dimension, independence rule, input contract that forbids outside knowledge, strict JSON schema, edge-case behavior. Phase 5 self-check now verifies anchors are present.
- Specificity-dial table in `references/prompt-mechanics.md` adds an `Eval grader` row with the contract above.

## What changed in v3.0

- Done-when contract: outcome contract now requires observable success criteria, not just a desired result.
- Reasoning-effort and verbosity calibration: prompts now recommend `effort` / `reasoning_effort` tuning at the API level (Claude `low | medium | high | xhigh | max`; OpenAI `none | minimal | low | medium | high | xhigh`) instead of writing prose that approximates them.
- Scope discipline: explicit out-of-scope guidance for Claude Opus 4.7 and GPT-5.2, both of which follow scope literally and over-deliver without it.
- Final-reminders pattern dropped as routine boilerplate (GPT-5.2 instruction adherence makes it redundant; can cause overtriggering on Claude 4.6 / 4.7).
- Subagent briefing template added: parent must include file paths, prior decisions, output shape; subagent context starts empty.
- Three-agent harness (planner / generator / evaluator) template added for multi-hour autonomous work.
- Six architectural isolation patterns (Action-Selector, Plan-Then-Execute, LLM Map-Reduce, Dual LLM, Code-Then-Execute, Context-Minimization) plus CaMeL added to security patterns.
- Meta Rule of Two and Microsoft Spotlighting added to security patterns.
- MCP-specific risks (tool description poisoning, rug pulls, ToolCommander) and RAG poisoning (PoisonedRAG, 5-document attacks) added.
- New anti-patterns: "think step by step" on reasoning models, deprecated `budget_tokens`, prefilled responses on 4.7, scope-restricting "Only X" on 4.7, routine final reminders on GPT-5.2, "Maximize" / "thoroughly" tool-use language on GPT-5.
- Updated evidence: 13 new 2025-2026 papers including Mollick PSR4 (expert personas drop MMLU 71.6%→68.0%), GEPA (ICLR 2026 Oral, new SOTA optimizer), "Reasoning Models Struggle to Control CoT" (controllability mostly <10%).

## Research basis

Reference materials are condensed from:

- 50+ academic papers (Mollick / Wharton Reports 1-4, EMNLP, NeurIPS, ICLR, TACL, USENIX Security, ACM CCS publications 2022-2026).
- Anthropic prompt engineering docs (Claude Opus 4.7 / Sonnet 4.6 best practices, XML tags, prompt templates, tool definitions, context engineering, multi-agent research, long-running harnesses, Agent Skills).
- OpenAI prompting guides (GPT-5 / 5.1 / 5.2, GPT-5.3-Codex, reasoning best practices, AGENTS.md, instruction hierarchy, Model Spec Dec 2025).
- Prompt injection defense research (OWASP LLM Top 10 2025, NIST AI 600-1 / 100-2e2025, MITRE ATLAS, Simon Willison's lethal trifecta, Meta Agents Rule of Two, CaMeL, six architectural isolation patterns, Microsoft Spotlighting).
- Automated prompt optimization (GEPA, MetaSPO, PromptWizard, OPRO, APE, SAMMO).
- Chroma context-rot research (18 frontier models, 20-50% accuracy drops at 100K tokens).
- Production system prompt patterns (Claude Code, ChatGPT, GitHub Copilot, Cursor, Replit Agent, Codex CLI).

## Requirements

- macOS (pbcopy) or Linux (xclip / xsel) for clipboard support.
- Clipboard is optional - prompts are always displayed in chat.
