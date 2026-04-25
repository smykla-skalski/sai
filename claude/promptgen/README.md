# promptgen

Turn rough instructions into optimized, evidence-based AI prompts. Built on current Anthropic/OpenAI guidance, agent-prompt mechanics, prompt injection defenses, and empirical prompt research.

## What it does

You describe what you want a prompt to do in plain language. The skill generates a well-structured prompt with an outcome contract, success criteria, evidence rules, side-effect boundaries, fitting specificity, and no common anti-patterns. Output goes to clipboard by default.

Supports four target formats: Claude (XML tags), GPT (outcome-first Markdown), Codex (coding-agent contract), and generic (Markdown-only).

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

| Flag                     | Default | Purpose                                          |
|:-------------------------|:--------|:-------------------------------------------------|
| (positional)             | -       | Rough instructions for what the prompt should do |
| `--for <model>`          | claude  | Target: claude, gpt, codex, generic              |
| `--research light\|deep` | off     | Investigate codebase before generating           |
| `--verbose`              | off     | Show reasoning behind prompt decisions           |
| `--no-copy`              | off     | Output to chat only, skip clipboard              |
| `--examples`             | off     | Include few-shot examples in generated prompt    |
| `--raw`                  | off     | Skip opinionated formatting preferences          |

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

1. **Input parsing** - extracts flags and instructions from arguments
2. **Research** (optional) - `--research light` checks config files and directory structure; `--research deep` reads relevant source files and traces call paths
3. **Task analysis** - categorizes the task, detects system vs task prompt, reads evidence-based principles
4. **Security assessment** - checks if the use case involves untrusted input, applies defensive patterns only when warranted
5. **Prompt generation** - builds the prompt using the target template (Claude/GPT/Codex/generic), applies formatting preferences
6. **Self-check** - verifies against anti-pattern checks, revises if any fail
7. **Output** - displays in fenced code block, copies to clipboard

## Research basis

The reference materials are condensed from:
- 35+ academic papers (Mollick/Wharton Reports, EMNLP, NeurIPS, ICLR, TACL publications)
- Anthropic prompt engineering docs (Claude 4.7/4.6 best practices, XML tags, prompt templates, tool definitions)
- OpenAI prompting guides (GPT-5.5, GPT-5 reasoning models, Codex prompting, prompt optimizer, agent safety)
- Prompt injection defense research (OWASP, NIST, MITRE ATLAS)
- SPRIG genetic prompt optimization results
- Chroma context rot research

## Requirements

- macOS (pbcopy) or Linux (xclip/xsel) for clipboard support
- Clipboard is optional - prompts are always displayed in chat
