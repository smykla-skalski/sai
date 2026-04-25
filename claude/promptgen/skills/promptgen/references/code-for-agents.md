# Code format and style for AI agent comprehension

Condensed from 21+ empirical studies (2022-2026), Anthropic's "Writing tools for AI agents" guidance, and the agent-loop / context-engineering pattern guides.

# Contents

- [Naming](#naming)
- [Comments and docstrings](#comments-and-docstrings)
- [Dead code](#dead-code)
- [Type annotations](#type-annotations)
- [Function length](#function-length)
- [File length and position effects](#file-length-and-position-effects)
- [Whitespace and formatting consistency](#whitespace-and-formatting-consistency)
- [Code chunking for RAG](#code-chunking-for-rag)
- [Coding-agent prompt rules](#coding-agent-prompt-rules)
- [Tool design for coding agents](#tool-design-for-coding-agents)
- [The agent loop](#the-agent-loop)
- [Long-running coding harness](#long-running-coding-harness)

## Naming

Identifier names are the single most influential surface feature for agent code comprehension.

Fully anonymizing names collapsed retrieval MRR from 70% to 17% for Java and 68% to 24% for Python on CodeBERT / GraphCodeBERT (arXiv:2307.12488).

Misleading names (shuffled to create wrong associations) hurt more than random names - models learn spurious correlations and apply them confidently.

On class-level summarization: GPT-4o dropped 29 points (87.3% to 58.7%) after alpha-renaming; DeepSeek V3 dropped 11 points (arXiv:2510.03178).

Casing changes caused 100% worst-case accuracy drop for Java with smaller models (TokDrift arXiv:2510.14972).

**Rule for generated prompts:** use descriptive, consistent names. Misleading names are worse than terse ones.

## Comments and docstrings

Missing comments are neutral; incorrect comments actively hurt.

Random (incorrect) comments reduced GPT-3.5 unit-test success to 22.1% and GPT-4 to 68.1% (arXiv:2404.03114).

Misleading comments as code mutations reduced debugging accuracy to 24.55%; absent or partial comments caused no statistically significant change for GPT-4 (arXiv:2504.04372).

Comment density in training data correlates with 6-13% benchmark gains (arXiv:2402.13013).

**Rule for generated prompts:** write correct comments or none. A wrong comment is worse than silence.

## Dead code

Inserting unreachable statements reduced debugging accuracy to 18.5% - the largest single-mutation impact found across all studies (arXiv:2504.04372).

Models cannot filter dead branches; attention weights non-functional tokens the same as functional ones.

**Rule for generated prompts:** remove dead code, unreachable branches, and commented-out blocks before presenting code to an agent.

## Type annotations

94% of LLM compilation errors stem from type-check failures.

Type-constrained decoding cuts compilation errors by more than half and improves functional correctness across models up to 34B parameters (arXiv:2504.09246, PLDI 2025).

Type annotations are machine-verifiable documentation that cannot be wrong the way natural-language comments can.

**Rule for generated prompts:** include type annotations in code agents read or generate. For code-gen tasks, instruct the agent to annotate types.

## Function length

No study directly benchmarks an optimal function line count, but retrieval studies imply a practical ceiling.

Functions that exceed a single chunk boundary harm retrieval: the chunk bisects the function and neither half is useful as standalone context (arXiv:2510.06606).

Practical chunk size by context budget: 32-64 lines for 4K tokens, 64-128 lines for 4K-8K tokens, whole-file viable at 16K+.

Context length alone (independent of content) degrades accuracy: open-source models lost 44-59% at 7K tokens even with perfect retrieval (arXiv:2510.05381).

**Rule for generated prompts:** keep functions small enough to fit in one retrieval chunk. For code-gen, instruct the agent to prefer small, focused functions.

## File length and position effects

The "lost in the middle" effect applies within files, not just RAG contexts: faults in the first 25% of a file are found 60% of the time; faults in the final 25% only 13% (arXiv:2504.04372).

Agents front-load attention regardless of where relevant logic sits.

**Rule for generated prompts:** put the most important logic near the top of files. For review or debugging tasks, tell the agent that content late in a file is more likely to be missed.

## Whitespace and formatting consistency

Mixed formatting (some elements removed, some kept) degrades performance more than either extreme consistently formatted (arXiv:2508.13666).

Spacing changes around operators trigger the highest per-rewrite sensitivity rate (10%+) of any formatting change, driven by tokenizer fragmentation (arXiv:2510.14972).

**Rule for generated prompts:** pick one formatting style and apply it throughout. Inconsistent formatting is worse than any single consistent choice.

## Code chunking for RAG

AST-based chunking (splitting at function / class boundaries) outperforms fixed-size line chunking by 4-6 points on Pass@1 for code completion tasks (cAST arXiv:2506.15655, EMNLP 2025).

For code-to-code retrieval: BM25 with word-level splitting is 14x faster than dense embeddings with comparable accuracy.
For NL-to-code retrieval: dense embeddings outperform BM25 by 14 NDCG points at 270x higher latency cost.

Function / method is the minimum effective retrieval unit - GraphCodeAgent, STALL+, and LocAgent converge on this independently.

**Rule for generated prompts:** for RAG-based code agents, instruct AST / function-boundary chunking. For repo-level agents, treat function as the minimum navigation unit.

## Coding-agent prompt rules

Current coding-agent guidance has shifted from "show a plan first" toward outcome, autonomy, and verification contracts.

For generated coding-agent prompts, include:

1. Scope: files, modules, behavior, and surfaces the agent may change. State explicit out-of-scope items if the model risks over-delivery (Claude 4.7 / GPT-5.2 scope discipline).
2. Context gathering: inspect relevant code before claims or edits; use fast search first.
3. Reuse rule: prefer existing helpers, patterns, and tests before adding abstractions.
4. Edit safety: preserve unrelated dirty work; avoid destructive commands unless explicitly authorized.
5. Side-effect policy: define whether commits, pushes, network calls, package installs, or external system writes are allowed.
6. Verification: name the narrowest useful test / lint / build command when known, plus manual checks when tests are absent. For UI / agent flows, end-to-end check via Playwright or an integration harness.
7. Completion: final response must state changed files, validation run, residual risk.
8. Persistence: bias to action over clarification; persist end-to-end within a single turn whenever feasible.
9. Tool policy: prefer dedicated tools over shell, parallelize independent reads, avoid hard-coded tool-call order unless the harness contract requires it.

Avoid:

- Mandatory upfront plans for every coding task.
- Routine progress preambles in non-interactive rollouts. Allow short preambles every 1-3 logical steps for long agentic work; hard floor every 6 steps or 10 tool calls.
- Hard-coded tool-call order when the agent can choose based on evidence.
- "Make tests pass" wording without requiring a general solution.

Use step-by-step instructions only when order is part of correctness - migrations, deployment, destructive operations, multi-system state changes.

## Tool design for coding agents

Anthropic "Writing tools for AI agents" (Sept 2025): treat tool design as onboarding a new hire. Even small refinements yield large gains - Sonnet 3.5 hit SOTA on SWE-bench from tool-description tweaks alone.

When a generated prompt also defines tools:

- Consolidate. `schedule_event` beats `list_users` + `list_events` + `create_event` when the agent's job is scheduling.
- Namespace consistently (`asana_projects_search`, `slack_messages_post`).
- Use specific parameter names (`user_id` not `user`). Disambiguate every parameter.
- Return semantic identifiers (`name`) over technical ones (`uuid` or MIME type) when possible.
- Provide actionable error messages: `Query returned 2,847 results. Add filters (e.g., status='active') or use pagination with limit=25.` not `Error: Invalid parameters`.
- Pagination and filtering with sensible defaults.
- 1-5 example calls per tool covering minimal, partial, and full specification.
- Programmatic Tool Calling (PTC, Anthropic 2025): for repetitive multi-tool sequences, allow the model to write Python that orchestrates tool calls. Reduces latency and tokens.
- Tool Search Tool (Anthropic 2025): for harnesses with thousands of tools, expose discovery as a tool rather than loading all definitions in context.

## The agent loop

Anthropic's agent-loop framing (four-stage feedback cycle):

1. Gather context - collect relevant information (agentic search, semantic search, subagents).
2. Take action - execute decisions using tools.
3. Verify work - evaluate output quality (rule-based, visual, LLM-as-judge).
4. Iterate - refine based on feedback.

For generated coding-agent prompts, include verification methods that match the task:

- Rule-based: linting, format validation, regex / type checks.
- Visual: screenshots and renders for UI work.
- LLM-as-judge: secondary model evaluation for fuzzy criteria; warn that the judge is itself injection-vulnerable, so use a different model family for the judge.

## Long-running coding harness

For agents whose work spans multiple sessions or context windows:

- Two-agent harness (Anthropic): an initializer agent sets up structured environments (feature lists, git repos, progress tracking files) on first run; a coding agent makes incremental progress session-by-session.
- Three-agent harness (Anthropic 2026): planner / generator / evaluator. The evaluator owns a "sprint contract" - acceptance criteria negotiated before implementation. Best for multi-hour autonomous full-stack work.
- External artifacts as memory: progress files, git history, structured feature lists persist across sessions. Each session reconstructs context from these artifacts before any new work.
- Use JSON for structured state (less prone to model corruption than Markdown).
- Commit progress to git with descriptive messages; use git to revert bad changes.
- Work on one feature at a time. Single-feature focus prevents the agent from doing too much at once.
- Standard 2026 stop conditions: milestone fully implemented and verified, real blocker requiring human input, budget or permissions prevent safe progress, human pauses or redirects.
