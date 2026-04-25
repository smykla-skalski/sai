# Prompt generation mechanics

Use this reference during prompt generation. It converts broad prompting advice into concrete decisions for the generated prompt.

# Contents

- [Source synthesis](#source-synthesis)
- [Prompt brief](#prompt-brief)
- [Specificity dial](#specificity-dial)
- [Model-specific mechanics](#model-specific-mechanics)
- [Examples and failure cases](#examples-and-failure-cases)
- [Author preferences](#author-preferences)
- [Prompt quality gate](#prompt-quality-gate)

## Source synthesis

Current vendor guidance converges on these mechanics:

1. Start from the outcome, not the process.
2. Separate stable instructions from dynamic inputs.
3. Define success criteria, completion rules, and verification before adding workflow steps.
4. Put tool behavior in tool definitions when building a tool API; keep prompts focused on cross-tool policy, side effects, and user-facing behavior.
5. Add examples only when they demonstrate output shape, edge cases, or policy boundaries better than prose.
6. Use evals or at least failure examples for prompts that will be reused.
7. Add security structure only when untrusted content, private data, or external side effects are present.

## Prompt brief

Before writing the generated prompt, fill this brief mentally or in scratch notes:

| Field | Decision |
| :-- | :-- |
| Target | Claude, GPT, Codex, generic, or unknown |
| Prompt type | task prompt, system prompt, tool description, eval grader, or prompt-improvement request |
| Desired result | the concrete artifact, behavior, or decision the model must produce |
| Success criteria | observable checks that prove the result is acceptable |
| Failure modes | hallucination, partial completion, wrong format, unsafe action, overengineering, stale data, weak evidence, excessive verbosity |
| Context boundary | trusted context, untrusted data, repo files, retrieved evidence, examples, or user variables |
| Side effects | read-only, file edits, commits, network calls, external writes, payments, messages, production actions |
| Tool policy | available tools, preferred tools, prohibited tools, approval gates, retry behavior |
| Verification | tests, citations, schema validation, manual review checklist, grader signals |
| Stop rule | when to finalize, ask for help, mark blocked, or abstain |

Only include fields that matter in the final prompt. A one-shot writing prompt may only need desired result, output shape, and style. A coding-agent prompt usually needs every field.

## Specificity dial

Choose the least process that protects the task.

| Task shape | Best prompt mechanics |
| :-- | :-- |
| Simple generation | Goal, constraints, output format |
| Structured extraction | Source boundary, fields, missing-value behavior, output schema |
| Research | Source policy, citation rules, empty-result recovery, synthesis rules |
| Coding task | Repo exploration, edit scope, reuse rules, tests, final evidence |
| Long-horizon agent | Completion checklist, recovery rules, compaction/handoff expectations, side-effect gates |
| High-risk action | Permission gate, preflight parameters, post-action verification |

Avoid turning every prompt into a universal agent prompt. Extra machinery lowers signal for simple tasks.

## Model-specific mechanics

### Claude

- Use XML tags for instructions, context, examples, inputs, and output contracts when the prompt has multiple parts.
- Use 3-5 high-quality examples only when examples are needed; Claude follows example details closely.
- For current Claude 4.6+ models, use adaptive thinking and effort controls in API configuration. Avoid manual thinking-budget prose and last-assistant prefill patterns.
- Be explicit when you expect action, not only suggestions.
- Add minimal-scope guidance for coding tasks that risk overengineering.

### GPT and OpenAI reasoning models

- Prefer outcome-first prompts: result, constraints, evidence, output shape, done criteria.
- Reduce inherited process-heavy prompt stacks. Add process only when it prevents a known failure.
- For production prompts, place stable text first and dynamic variables last for caching and easier versioning.
- Use `reasoning.effort` and `text.verbosity` as configuration knobs; do not try to recover quality only by adding more prompt prose.
- Use structured outputs for strict schemas when the integration supports them.

### Codex

- Include autonomy, codebase exploration, edit safety, verification, and final-report expectations.
- Avoid mandatory upfront plans and routine preambles for rollout-style coding prompts unless the user explicitly wants them.
- Encourage parallel reads and dedicated tools when available, but do not hard-code exact tool-call order unless the harness requires it.
- State when to continue with assumptions versus when to ask because a choice risks data loss, security, or external impact.

### Generic

- Use Markdown sections, short instructions, positive constraints, and explicit output shape.
- Avoid model-specific claims such as XML superiority, recency-effect hacks, or reasoning-parameter guidance.

## Examples and failure cases

Include examples when one of these is true:

- The output format is easy to misread.
- The task has edge cases where prose rules are ambiguous.
- The prompt is a policy or safety workflow and examples show allowed versus disallowed actions.
- The prompt will be reused and the user supplied representative inputs.

Do not include examples when they are generic, invented without confidence, or likely to narrow the model away from valid outputs.

For prompt improvement tasks, prefer failure examples over abstract advice:

1. Identify 2-5 representative failures.
2. Name the failure mode for each one.
3. Add or revise only the smallest instruction that would prevent the failure.
4. Re-check that the revision does not create a new failure mode.

## Author preferences

Skip this section when `--raw` is set.

For markdown outputs such as docs, reports, changelogs, and READMEs, add:

- Do not hard-wrap or break long lines. Keep each sentence or logical unit on one line and let the editor or renderer wrap it.
- Leave no trailing whitespace.

For code-editing prompts, add only the relevant rules:

- Commit after each logical unit of work if commits are allowed.
- Use descriptive, consistent names.
- Write correct comments or none.
- Remove dead code, unreachable branches, and commented-out blocks.
- Add type annotations where the language supports them.
- Keep functions small enough to fit in one context chunk.
- Put important logic near the top of files when practical.

## Prompt quality gate

Before returning the generated prompt, verify:

1. The prompt says what done means.
2. The model knows what evidence to use and what evidence is out of scope.
3. The output shape is explicit enough to test.
4. Missing information behavior is defined.
5. Tool side effects and approval gates are clear.
6. The prompt does not ask for private reasoning or chain-of-thought disclosure.
7. No process step exists only because it sounds careful.
8. The prompt can be shortened without losing a real requirement; if yes, shorten it.
