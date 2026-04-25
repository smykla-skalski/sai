# Prompt generation mechanics

Use this reference during prompt generation. It turns broad prompting advice into concrete decisions for the prompt being written.

# Contents

- [Source synthesis](#source-synthesis)
- [Prompt brief](#prompt-brief)
- [Specificity dial](#specificity-dial)
- [Reasoning effort and verbosity](#reasoning-effort-and-verbosity)
- [Model-specific mechanics](#model-specific-mechanics)
- [Examples and failure cases](#examples-and-failure-cases)
- [Two-step metaprompting](#two-step-metaprompting)
- [Author preferences](#author-preferences)
- [Prompt quality gate](#prompt-quality-gate)

## Source synthesis

Anthropic, OpenAI, and the 2025-2026 academic literature converge on these mechanics:

1. Start from the outcome contract, not the process. Modern reasoning models burn tokens reconciling instructions that contradict the goal.
2. Define "done when" criteria - observable signals the answer is acceptable - before adding workflow steps. This is the single highest-leverage section of any prompt.
3. Separate stable instructions from dynamic inputs. Wrap untrusted inputs in clear delimiters.
4. Put tool behavior in tool definitions when building a tool API. Keep prompts focused on cross-tool policy, side effects, and user-facing behavior.
5. Use 3-5 diverse examples only when output format, edge cases, or policy boundaries are easier to show than describe. On modern models examples teach format, not reasoning.
6. Use API-level controls (`reasoning_effort`, `verbosity`, structured outputs, strict tools) instead of prose that re-implements them.
7. Add security structure only when untrusted content, private data, or external side effects are present. Match the security model to the threat, not maximum hardening for every prompt.
8. Audit for contradictions - models silently drop conflicting instructions instead of flagging them (SIFo Benchmark 2024, "Control Illusion" arXiv:2502.15851).

## Prompt brief

Before writing the prompt, fill this brief mentally or in scratch notes. Skip fields that do not apply.

| Field | Decision |
| :-- | :-- |
| Target | Claude (Opus 4.7, Sonnet 4.6, Haiku 4.5), GPT (5/5.1/5.2/5.3-Codex), generic, or unknown |
| Prompt type | task prompt, system prompt, tool description, eval grader, prompt-improvement, or reusable template |
| Desired result | the concrete artifact, behavior, or decision the model must produce |
| Done-when criteria | observable checks that prove the result is acceptable (the verification contract) |
| Failure modes | hallucination, partial completion, wrong format, unsafe action, overengineering, scope creep, stale data, weak evidence, excessive verbosity |
| Context boundary | trusted context, untrusted data, repo files, retrieved evidence, examples, or user variables |
| Side effects | read-only, file edits, commits, network calls, external writes, payments, messages, production actions |
| Tool policy | available tools, preferred tools, prohibited tools, approval gates, retry behavior, parallelization |
| Verification | tests, citations, schema validation, manual review checklist, grader signals |
| Stop rule | when to finalize, ask for help, mark blocked, or abstain |
| Scope discipline | what is explicitly out of scope (prevents 4.7 / GPT-5.2 over-delivery) |

A one-shot writing prompt may only need desired result, done-when, and output shape. A coding-agent prompt usually needs every field.

## Specificity dial

Choose the least process that protects the task. Extra machinery lowers signal on modern models (Mollick PSR2 arXiv:2506.07142, "Evolving Prompt Effectiveness" arXiv:2510.22251).

| Task shape | Best prompt mechanics |
| :-- | :-- |
| Simple generation | Goal, constraints, output format. No process steps. |
| Structured extraction | Source boundary, fields, missing-value behavior, output schema (use API structured outputs when available) |
| Research / synthesis | Source policy, citation rules, empty-result recovery, freshness rules, synthesis shape |
| Coding task | Repo exploration, edit scope, reuse rules, tests, evidence required for final answer |
| Long-horizon agent | Done-when checklist, recovery rules, compaction/handoff expectations, side-effect gates, parallelization policy |
| High-risk action | Permission gate, preflight parameters, post-action verification, abort rules |
| Multi-step pipeline | Step order only when order affects safety, correctness, or side effects - otherwise decision rules |

Avoid turning every prompt into a universal agent prompt. Add process only when it prevents a known failure mode.

## Reasoning effort and verbosity

Modern model APIs expose `reasoning_effort` (or `effort`) and `verbosity` as configuration knobs. Tune them at the API call site instead of writing prose that approximates them.

**Anthropic Claude (Opus 4.7, Sonnet 4.6, Haiku 4.5):** `effort` levels `low`, `medium`, `high`, `xhigh`, `max`. Manual `budget_tokens` and `thinking: {type: "enabled"}` are deprecated on 4.6 and removed on 4.7 - use `thinking: {type: "adaptive"}` paired with `effort`. For Opus 4.7 at `max` or `xhigh`, set `max_tokens` to 64k or higher to avoid runaway truncation.

**OpenAI GPT-5 / 5.1 / 5.2:** `reasoning_effort` levels `none`, `minimal`, `low`, `medium`, `high`, `xhigh`. Default on GPT-5.2 is `none` (was `medium` on GPT-5). Calibrate up only for genuinely complex multi-step work. `verbosity` is a separate parameter from reasoning length - give explicit length constraints in the prompt ("`<= 2 sentences`" or "1 short overview paragraph then `<= 5` bullets") rather than describing the verbosity in prose.

**Codex (GPT-5.3-Codex):** same parameters as GPT-5.2. Use `low` for well-scoped repos, `medium` or `high` for debugging, `xhigh` for long agentic work.

If the prompt cannot rely on these knobs (older models, non-API integrations), use prose only as fallback - "Be concise" or "Reason carefully through edge cases before answering" - not both.

## Model-specific mechanics

### Claude (Opus 4.7, Sonnet 4.6, Haiku 4.5)

- XML tags for instructions, context, examples, inputs, and output contracts - native and well-supported. Use `<instructions>`, `<context>`, `<example>`, `<examples>`, `<documents>` with descriptive names. Match prompt formatting style to desired output style.
- For long-context work (20k+ tokens), put longform data at the top wrapped in `<document index="n">` tags, queries at the end. Often a 30% quality lift.
- 3-5 diverse examples only when needed - Claude 4.x pays close attention to example details and copies mistakes.
- Be explicit when you expect action, not only suggestions. State scope explicitly on Opus 4.7 ("Apply this formatting to every section, not just the first one") - 4.7 follows literally.
- Soften tool-use language. "You must use [tool]" causes overtriggering - "Use [tool] when it would help" works.
- Prefilled assistant responses are deprecated and rejected on Opus 4.7. Use `<output>` tags or system-prompt instructions like "Respond directly without preamble" instead.
- Claude 4.x calibrates verbosity to perceived complexity. Tune with positive examples ("Provide concise responses") rather than "do not be verbose".
- Avoid scope-restricting language like "Only report high-severity issues" - 4.7 will literally drop everything else. Ask for full coverage with severity tags instead.

### GPT-5 / 5.1 / 5.2 (and reasoning models)

- Outcome-first: result, constraints, evidence, output shape, done criteria. Reduce inherited process-heavy stacks. Sculpted prompts that helped GPT-4o measurably hurt GPT-5 ("Evolving Prompt Effectiveness" arXiv:2510.22251).
- Place stable text first and dynamic variables last for caching and easier versioning.
- Use API structured outputs and strict tools when the integration supports them. Do not spend hundreds of tokens describing a JSON schema the API can enforce.
- GPT-5.2 follows instructions more literally than predecessors. Audit for contradictions - they damage reasoning more than on prior models. Use "Do not" exception clauses to carve narrow exclusions instead of layering conflicting positive instructions.
- Apply scope discipline explicitly: "Implement EXACTLY and ONLY what the user requests. No extra features, no added components, no UX embellishments."
- Calibrate tool persistence with budgets ("max 2 search calls before answering"). Provide escape hatches ("if uncertain after 2 calls, answer with the best available evidence and flag the uncertainty").
- Final-reminders pattern is no longer load-bearing on GPT-5.2 - skip routine repetition at the end. Reserve it for resolving a specific contradiction or for exploiting recency on older models.
- For reasoning models (o-series, GPT-5 reasoning, Claude with thinking enabled): never request visible chain-of-thought. Reasoning happens internally; prompting "think step by step" is counterproductive ("Decreasing Value of CoT" arXiv:2506.07142, "Reasoning Models Struggle to Control CoT" arXiv:2603.05706). Ask for concise rationale or evidence in the final answer when needed.

### Codex (GPT-5.3-Codex) and coding agents

- Identity is a coding agent operating in the user's repository. Persist end-to-end within the current turn whenever feasible - bias to action over clarification.
- Prefer dedicated tools over shell. Always parallelize independent reads. Do not hard-code tool-call order unless the harness contract requires it.
- Inspect relevant code before claims or edits. Reuse existing helpers, patterns, and tests before adding abstractions.
- Include a verification contract: narrowest useful test, lint, or build command, plus manual checks when tests are absent.
- Final response must state changed files, validation run, and residual risk.
- For long agentic rollouts, allow short preambles every 1-3 logical steps (hard floor: every 6 steps or every 10 tool calls). Routine progress preambles for non-interactive tasks are still wasteful.
- State explicitly when to continue with a reasonable assumption versus when to pause and ask. Default: pause only for actions that risk data loss, security, or external impact.

### Generic

- Use Markdown sections, short instructions, positive constraints, and explicit output shape.
- Avoid vendor-specific claims (XML tag superiority, prefill prefixes, reasoning-effort knobs, recency-effect reminders).
- Markdown is the safest cross-model format choice.

## Examples and failure cases

Include examples when one of these is true:

- The output format is easy to misread.
- The task has edge cases where prose rules are ambiguous.
- The prompt is a policy or safety workflow and examples show allowed versus disallowed actions.
- The prompt will be reused and the user supplied representative inputs.

Skip examples when they are generic, invented without confidence, or likely to narrow the model away from valid outputs. Modern reasoning models often prefer zero-shot - few-shot's primary role today is format alignment, not skill teaching ("Zero-shot Can Be Stronger than Few-shot" arXiv:2506.14641).

Few-shot safety demonstrations enhance role-playing prompts (+4.3%) but degrade task-oriented prompts (-21.2%) - match the technique to the prompt style.

For prompt improvement, prefer failure examples over abstract advice:

1. Identify 2-5 representative failures.
2. Name the failure mode for each one.
3. Add or revise only the smallest instruction that would prevent the failure.
4. Re-check that the revision does not create a new failure mode.

## Two-step metaprompting

When the user has access to failures or representative inputs, run a metaprompting pass:

1. Collect 3-10 failure examples.
2. For each, name the failure mode (hallucinated field, wrong format, unsafe action, scope creep, etc.).
3. Group failures into clusters - patch the cluster, not individual cases.
4. Add the smallest instruction, example, or output-contract change that blocks the cluster.
5. Re-run on the original failures and a held-out set to confirm no regression.

Automated prompt optimization (GEPA arXiv:2507.19457 ICLR 2026 Oral, MetaSPO arXiv:2505.09666, PromptWizard, OPRO, APE) consistently outperforms human-crafted prompts. If the prompt matters enough to optimize, consider running it through a tool. Two-step metaprompting (analyze failures, surgical revision) approximates the same gain without special tooling.

## Author preferences

Skip this section when `--raw` is set.

For markdown outputs (docs, reports, changelogs, READMEs):

- Do not hard-wrap or break long lines. Keep each sentence or logical unit on one line and let the editor or renderer wrap it.
- Leave no trailing whitespace.
- Use sentence-case headings, straight quotes, and dashes (not em dashes or semicolons).

For code-editing prompts, add only the rules that apply to the task:

- Commit after each logical unit of work if commits are allowed.
- Use descriptive, consistent names. Misleading names are worse than terse ones (arXiv:2510.03178).
- Write correct comments or none. A wrong comment is worse than silence (arXiv:2404.03114).
- Remove dead code, unreachable branches, and commented-out blocks.
- Add type annotations where the language supports them.
- Keep functions small enough to fit in one retrieval chunk.
- Put important logic near the top of files when practical.

## Prompt quality gate

Before returning the generated prompt, verify:

1. The prompt states what done means in observable terms.
2. The model knows what evidence to use and what evidence is out of scope.
3. The output shape is explicit enough to test.
4. Missing-information behavior is defined (when to ask, abstain, mark blocked, or report "not found").
5. Tool side effects and approval gates are clear.
6. The prompt does not request private reasoning or chain-of-thought disclosure from a reasoning model.
7. No process step exists only because it sounds careful.
8. No two instructions contradict each other (audit explicitly - models silently drop conflicts).
9. Token budget: task prompts under 500, system prompts under 1500. If over, cut the lowest-priority content.
10. Identity and constraints sit in the first ~200 tokens; verification and stop rules sit at the end.
