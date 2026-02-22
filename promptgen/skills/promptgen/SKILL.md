---
name: promptgen
description: Turn rough instructions into optimized, evidence-based AI prompts. For system prompts, task prompts, agent instructions, or any scenario where a well-structured prompt is needed. Copies to clipboard.
argument-hint: "<instructions> [--for claude|gpt|generic] [--verbose] [--no-copy] [--with-examples] [--raw]"
allowed-tools: Read, Bash, AskUserQuestion
user-invocable: true
---

# Promptgen

Generate optimized, evidence-based prompts from rough human instructions. Built on research from 35+ academic papers, Anthropic/OpenAI vendor docs, and Mollick/Wharton Prompting Science Reports.

## Arguments

Parse from `$ARGUMENTS`:

| Flag              | Default | Purpose                                          |
|:------------------|:--------|:-------------------------------------------------|
| (positional)      | -       | Rough instructions for what the prompt should do |
| `--for <model>`   | claude  | Target: claude, gpt, generic                     |
| `--verbose`       | off     | Show reasoning behind prompt decisions           |
| `--no-copy`       | off     | Output to chat only, skip clipboard              |
| `--with-examples` | off     | Include few-shot examples in generated prompt    |
| `--raw`           | off     | Skip opinionated formatting preferences          |

## Workflow

### Phase 1: Input parsing

1. Parse `$ARGUMENTS` for flags and positional instructions.
2. Extract `--for` value (default: claude). Accepted values: claude, gpt, generic.
3. Check for `--verbose`, `--no-copy`, `--with-examples`, `--raw` flags.
4. If no positional instructions provided, use AskUserQuestion to get what the prompt should do.

### Phase 2: Task analysis

Read `$SKILL_DIR/references/prompt-principles.md` in full.

1. Determine the task category from the instructions:
   - docs - documentation generation
   - investigation - research, analysis, debugging
   - refactoring - code restructuring
   - code-gen - writing new code
   - planning - architecture, design, roadmaps
   - security - security review, vulnerability analysis
   - testing - test creation, QA
   - debugging - bug identification, root cause analysis
   - general - anything else

2. Detect whether this is a system prompt or task prompt:
   - System prompt: defines an agent's persistent identity, constraints, and behavior
   - Task prompt: one-shot instructions for a specific task

3. Identify what tools or capabilities the agent needs based on the instructions.

4. If the task category is code-gen, refactoring, debugging, testing, or investigation involving code, read `$SKILL_DIR/references/code-for-agents.md` in full. Apply the "Rule for generated prompts" entries from each section that is relevant to the task.

5. If `--verbose`, note the category, prompt type, and reasoning.

### Phase 3: Security assessment

Read `$SKILL_DIR/references/security-patterns.md` in full.

1. Check whether the prompt's use case involves any of the lethal trifecta components:
   - Access to private data
   - Exposure to untrusted content
   - Ability to communicate externally

2. If the use case involves untrusted input, plan to include appropriate defensive patterns:
   - Sandwich defense (reminders after input)
   - Data labeling (mark untrusted content as DATA)
   - Role anchoring (constraints on identity changes)
   - Tool safety rules (if tools are involved)

3. If the use case is internal-only with no untrusted input path, skip security hardening. Don't add security overhead that wastes tokens.

4. If `--verbose`, explain the security assessment and which patterns apply.

### Phase 4: Prompt generation

Read `$SKILL_DIR/references/prompt-structure.md` in full.

Build the prompt using the appropriate template variant:
- `claude`: XML tags for data boundaries, Markdown for sections
- `gpt`: Markdown headers, final reminders section for recency effect
- `generic`: Markdown-only, no model-specific optimizations

Generation rules:

1. Identity section: exactly 2 lines. Name + scope. No adjective stacking.
2. Constraints before instructions. Stated positively where possible.
3. Instructions are specific and actionable. No generic quality statements like "be thorough" or "be accurate."
4. Token budget: task prompts under 500 tokens, system prompts under 1500 tokens.
5. Include security patterns from Phase 3 only when the threat model warrants them.
6. Add few-shot examples section only if `--with-examples` flag is set. Examples must perfectly match desired behavior.
7. For Claude target: soften tool-use language, no anti-laziness prompts.
8. For GPT target: add final reminders section repeating 1-2 critical constraints.
9. For generic target: no model-specific optimizations.
10. If the task involves adding or upgrading any dependency, library, package, GitHub Action, Docker image, Helm chart, or other versioned artifact: include an explicit instruction in the generated prompt requiring the agent to look up the latest stable version before using it. The instruction must cover the relevant ecosystems (npm, pip, go get, cargo, GitHub Actions, Helm, Docker, etc.) and must not let the agent assume or guess a version.

Opinionated formatting preferences (skip when `--raw` is set):

When the task involves markdown output (docs, reports, changelogs, READMEs, or any task where the generated prompt will produce markdown files), append these formatting rules to the generated prompt:

- Do not hard-wrap or break long lines. Keep each sentence or logical unit on a single line regardless of length. Let the editor or renderer handle wrapping.
- No trailing whitespace on lines.

When the task involves code changes (code-gen, refactoring, debugging, investigation with code edits, or any agentic workflow that writes or modifies files), append these rules to the generated prompt:

- Commit after each logical unit of work completes. Small, frequent commits make progress easier to track and mistakes easier to revert.
- Use descriptive, consistent names. Misleading names hurt agent comprehension more than terse ones.
- Write correct comments or none. An incorrect comment causes more damage than silence.
- Remove dead code, unreachable branches, and commented-out blocks.
- Add type annotations where the language supports them.
- Keep functions short enough to fit within a single context window chunk (roughly under 100 lines).
- Put the most important logic near the top of files. Agents front-load attention; content in the final quarter of a file is routinely missed.

These preferences reflect the prompt author's workflow and are backed by empirical research in `$SKILL_DIR/references/code-for-agents.md`. The `--raw` flag produces a clean prompt without them.

Writing style rules (applied to the generated prompt text):
- No sycophantic patterns, chatbot artifacts, or promotional language
- Sentence case headings, straight quotes
- Varied sentence rhythm - mix short and long
- State things plainly
- AI vocabulary and filler phrase rules are in `$SKILL_DIR/references/anti-patterns.md` items 10-11 - apply them during generation, not just during self-check

### Phase 5: Self-check

Read `$SKILL_DIR/references/anti-patterns.md` in full.

Verify the generated prompt against all 12 anti-pattern checks:

1. No adjective stacking in identity section
2. No generic quality instructions
3. No tipping or incentives
4. No anti-laziness directives
5. No aggressive emphasis on routine instructions
6. No contradictory instructions
7. No negative-only framing (rewrite as positive)
8. No emotional manipulation
9. No motivational language
10. No AI vocabulary
11. No filler phrases
12. No excessive emphasis (CAPS/bold on more than 2-3 items)

If any check fails, revise the prompt and re-check. Continue until all 12 pass.

Verify token budget: task prompts under 500, system prompts under 1500. If over budget, cut the lowest-priority content.

### Phase 6: Output

1. Display the generated prompt in a fenced code block (use `markdown` language tag).

2. If `--verbose`, show the reasoning after the prompt:
   - Task category and prompt type detected
   - Security assessment results
   - Anti-pattern checks passed
   - Token count estimate

3. Unless `--no-copy` is set, copy to clipboard:

```bash
echo '<generated_prompt>' | bash "$SKILL_DIR/scripts/clipboard.sh"
```

4. Report clipboard status:
   - Success: "Copied to clipboard."
   - Failure (no clipboard tool): "Clipboard not available - install pbcopy (macOS), xclip, or xsel (Linux)."
   - `--no-copy`: skip clipboard entirely.

## Example invocations

```
/promptgen write technical docs for the auth module API endpoints
/promptgen refactor the database layer to use connection pooling --for gpt
/promptgen --verbose investigate auth bypass vulnerabilities in the login flow
/promptgen --no-copy create a plan for migrating from REST to GraphQL
/promptgen build a customer support chatbot that handles returns --with-examples
/promptgen --for generic create a code review agent for Python PRs
/promptgen --raw write a migration guide for the new API version
```

## Error handling

- Missing instructions: ask via AskUserQuestion, don't guess
- Invalid `--for` value: default to claude, warn the user
- Clipboard failure: still display the prompt, report the clipboard error
- Token budget exceeded: trim lowest-priority content, warn in verbose mode
