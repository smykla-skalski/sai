# Prompt principles

Condensed from 35+ academic papers, Anthropic/OpenAI vendor docs, and Mollick/Wharton Prompting Science Reports. No URLs inline - see the full research at `tmp/prompt-engineering-research.md` for citations.

# Contents

- [Preamble rules](#preamble-rules)
- [Structure order](#structure-order)
- [Outcome-first design](#outcome-first-design)
- [Information positioning](#information-positioning)
- [Formatting](#formatting)
- [Conciseness](#conciseness)
- [Model-generation awareness](#model-generation-awareness)
- [Tool and agent mechanics](#tool-and-agent-mechanics)
- [Few-shot rules](#few-shot-rules)
- [Positive framing](#positive-framing)
- [Chain-of-thought guidance](#chain-of-thought-guidance)
- [Emphasis and tone](#emphasis-and-tone)
- [Contradictions](#contradictions)
- [Templates, variables, and evals](#templates-variables-and-evals)
- [Automated optimization](#automated-optimization)

## Preamble rules

1. Open with brief factual identity: "You are [Name], [what it is, who made it]." One sentence scope. Then straight into constraints.
2. Don't stack adjectives ("expert, meticulous, thorough, world-class"). Static expert personas don't improve factual accuracy (Zheng EMNLP 2024: 162 personas, 9 models, zero significant improvement. Mollick Report 4: 6 frontier models, same result).
3. Low-knowledge personas actively hurt. Mollick Report 4: o4-mini dropped from 73% to 67% with a toddler persona, GPT-4o dropped from 46% to 41%.
4. Role prompts change tone and analytical framing, not correctness. Use specific domain framing when you need a particular perspective: "senior tax attorney specializing in Section 1031 exchanges" not "expert."
5. Use second person ("You are..."). Both Anthropic and OpenAI use this in production. No rigorous evidence that alternatives perform better.

## Structure order

For modern agent prompts, use this hierarchy:

1. Identity (1-2 sentences, factual)
2. Outcome contract (desired result, success criteria, evidence, allowed side effects, stop rule)
3. Constraints (non-negotiable rules, stated positively)
4. Instructions (specific, actionable - not "be thorough" but what to do)
5. Output specification (format, structure)
6. Examples (if needed - see few-shot rules below)
7. Critical reminders at the end only when they carry real priority

Anthropic: put longform data at the top and the query at the end for long-context work. OpenAI GPT-5.5 guidance favors outcome-first prompts: expected result, constraints, output shape, and verification before detailed process.

## Outcome-first design

Start by defining what a successful answer or agent run looks like.

High-quality prompts answer these questions:

1. What artifact or behavior should exist at the end?
2. What evidence proves it is acceptable?
3. What sources, files, or inputs may the model use?
4. What side effects are allowed?
5. When should the model ask, abstain, or report blocked instead of guessing?

Modern reasoning models often perform worse when every intermediate step is prescribed. Add step order only when order affects safety, correctness, or side effects.

For simple tasks, the outcome contract can be one line. For long-running agents, it should include acceptance criteria, verification commands, side-effect gates, and final-report shape.

## Information positioning

Models attend to information in this order: user message > beginning of system prompt > end of system prompt > middle sections.

The "lost in the middle" effect (Liu et al. TACL 2024): >30% performance drop when relevant information is in the middle of context. Even long-context models exhibit this.

Opening tokens are prime real estate. Don't waste them on generic role declarations or motivational language.

At 500 instructions, even the best frontier models achieve only 68% accuracy, with bias toward earlier instructions (Jaroslawicz 2025).

## Formatting

Use Markdown headers for sections. Use XML tags for data boundaries (especially for Claude). Avoid JSON for document formatting - it performed "particularly poorly" for long-context retrieval (OpenAI GPT-4.1 guide).

Format ranking for long-context: XML > ID|TITLE|CONTENT > JSON (OpenAI testing).

Hybrid approach works well: Markdown headers for sections, XML tags for data delimiters and examples.

Be consistent within a prompt. The specific format matters less than consistency (on modern models).

Prompt sensitivity to formatting varies by model size. Larger models are more robust. LLaMA-2-13B showed accuracy varying up to 76 points between equivalent format changes (ProSA, EMNLP 2024).

## Conciseness

Every token competes for attention budget. Context rot is real.

- ~113k tokens of conversation history drops accuracy by 30% vs focused 300-token version (Chroma, 18 models tested)
- Even a single distractor in context reduces performance
- 27.61% performance gap between verbose and concise responses (Qasper dataset)
- Generic quality instructions ("be accurate," "be helpful") were selected far less often than chance by genetic optimization across 47 task types (SPRIG 2024)

Token budget guidelines:
- Task prompts: under 500 tokens
- System prompts: under 1500 tokens
- Every instruction must earn its place

## Model-generation awareness

Newer models need simpler prompts. What works on GPT-3.5 may hurt on GPT-5. What works on Claude 3 may be counterproductive on Claude 4.6.

Claude 4.6:
- More responsive to system prompts than predecessors - dial back aggressive language
- Remove anti-laziness prompts ("be thorough," "do not be lazy")
- Soften tool-use language: "You must use [tool]" -> "Use [tool] when it would help"
- Remove explicit think tool instructions (causes over-planning)

GPT-4.1+:
- Follows instructions more literally
- A single clarifying sentence can redirect behavior
- Instructions closer to end of prompt followed more closely

GPT-5+:
- Outcome-first prompts outperform inherited process-heavy prompt stacks
- Tune reasoning effort and verbosity in configuration when available instead of adding prompt prose
- Contradictory instructions impair reasoning more than prior models
- Metaprompting works well - ask GPT-5 to improve prompts from concrete failures

Codex:
- Coding-agent prompts need autonomy, codebase exploration, edit safety, and verification contracts
- Avoid mandatory upfront plans, routine preambles, and hard-coded tool order unless the harness requires them
- Include rules for when to continue with assumptions versus when to ask because risk is high

Cross-generation finding (2025): sculpted prompts that helped GPT-4o became detrimental on GPT-5. Optimal strategies must co-evolve with model capabilities.

## Tool and agent mechanics

Tool quality depends more on tool definitions than on a long system prompt.

For each tool, the best prompt-adjacent information is:

1. What the tool does
2. When to use it
3. When not to use it
4. Parameter meanings and caveats
5. Output meaning, missing fields, and common errors
6. Side effects and retry safety

For agent prompts, keep cross-tool policy in the prompt: approval gates, destructive-action rules, evidence standards, and final-report expectations.

Avoid brittle choreography such as "always call A, then B, then C" unless the product contract requires that order. Prefer decision rules and done criteria.

## Few-shot rules

1. Few-shot examples work primarily by defining task format, not teaching reasoning (Min et al. EMNLP 2022: random labels barely hurt performance).
2. 1-2 examples show strong accuracy gains. Diminishing returns beyond 4-5.
3. Diverse examples > many similar examples.
4. Examples must perfectly match desired behavior - models adopt patterns exactly, including mistakes.
5. Modern reasoning models (DeepSeek-R1, o-series) may degrade with few-shot. Test both zero-shot and few-shot.
6. Anthropic: Claude 4.x "pays extremely close attention to example details" - bad examples actively hurt.
7. Use examples for formatting/style requirements. Skip them for straightforward tasks.

## Positive framing

Tell the model what TO do, not what NOT to do. "Don't use markdown" works worse than "Write in flowing prose paragraphs."

State constraints positively where possible. Reserve negative framing for actual safety boundaries.

## Chain-of-thought guidance

1. For reasoning models (o-series, GPT-5 reasoning models, Claude adaptive thinking): don't ask for private chain-of-thought. Reasoning happens internally. Ask for concise rationale or evidence in the final answer when needed.
2. For non-reasoning models: CoT helps modestly (Gemini Flash 2.0 +13.5%, Sonnet 3.5 +11.7%). But 35-600% longer response times.
3. Zero-shot CoT ("Let's think step by step") matches few-shot CoT on strong modern models.
4. Don't force structured output during reasoning. Let models reason in free text first, then convert to structured format in a second pass. JSON-mode dropped Claude-3-Haiku from 86.51% to 23.44% on GSM8K.

## Emphasis and tone

Where you once needed "CRITICAL: You MUST use this tool when...", now "Use this tool when..." works (Anthropic 4.6 guidance). Previous aggressive language causes overtriggering on modern models.

Reserve CAPS for actual safety-critical rules only. Use sparingly.

No emotional manipulation, tipping, or threats. Tipping ($200-$1000) and threatening showed no reliable aggregate effect across controlled studies with 100 repetitions per condition (Mollick Reports 1, 3).

Politeness has minimal aggregate impact (up to 60 percentage point differences on individual questions, but balanced out across datasets).

## Contradictions

Contradictory instructions cause silent, unpredictable failures. Models silently drop instructions rather than flag conflicts (SIFo Benchmark 2024). Even GPT-4 and Claude-3 often fail to complete all instructions when facing multiple conflicting requirements.

System/user prompt separation fails to provide reliable instruction hierarchy ("Control Illusion" 2025).

Audit prompts for contradictions. The model won't tell you they exist.

## Templates, variables, and evals

Use prompt templates and variables for prompts that will be reused. Keep stable instructions separate from dynamic user data so the prompt is easier to test, diff, cache, and version.

Wrap variables in clear boundaries, especially when variable content is untrusted or long.

For production prompts, pair changes with evals or at least representative failure examples. Strong prompt improvement starts from observed failures:

1. Collect examples where the prompt failed or produced weak output.
2. Name the failure mode.
3. Add the smallest rule, example, or output contract that blocks that failure.
4. Re-run examples or graders before accepting the change.

Use API structured outputs or tool schemas when strict output validation matters. Do not spend hundreds of prompt tokens describing a schema the API can enforce.

## Automated optimization

Human intuitions about what makes a good prompt are frequently wrong. Automated optimization consistently outperforms human-crafted prompts:
- APE: outperformed human-engineered prompts on 19/24 tasks
- OPRO: up to 8% on GSM8K and 50% on Big-Bench Hard vs human-designed
- PromptWizard: 5x cheaper than continuous optimization, evaluated on 45+ tasks

If your prompt matters enough to optimize, consider two-step metaprompting: analyze failures, then make surgical revisions.
