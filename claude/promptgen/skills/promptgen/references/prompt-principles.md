# Prompt principles

Evidence-backed principles condensed from 50+ academic papers (2022-2026), Anthropic and OpenAI documentation through April 2026, Mollick / Wharton Prompting Science Reports 1-4, Chroma context-rot research, and leaked production system prompts.

# Contents

- [Preamble rules](#preamble-rules)
- [Structure order](#structure-order)
- [Outcome-first design and the Done-when contract](#outcome-first-design-and-the-done-when-contract)
- [Information positioning](#information-positioning)
- [Formatting](#formatting)
- [Conciseness and context rot](#conciseness-and-context-rot)
- [Model-generation awareness](#model-generation-awareness)
- [Tool and agent mechanics](#tool-and-agent-mechanics)
- [Few-shot rules](#few-shot-rules)
- [Positive framing](#positive-framing)
- [Chain-of-thought guidance](#chain-of-thought-guidance)
- [Emphasis and tone](#emphasis-and-tone)
- [Contradictions and instruction following at scale](#contradictions-and-instruction-following-at-scale)
- [Templates, variables, and evals](#templates-variables-and-evals)
- [Multi-agent and orchestration](#multi-agent-and-orchestration)
- [Automated optimization](#automated-optimization)

## Preamble rules

1. Open with brief factual identity. "You are [Name], [what it is, who made it]." One sentence on scope. Then straight into constraints. Both major vendors use this pattern in production (`You are Claude Code, Anthropic's official CLI for Claude.` / `You are ChatGPT, a large language model trained by OpenAI...`).
2. Do not stack adjectives ("expert, meticulous, thorough, world-class"). Static expert personas underperform plain prompts on factual benchmarks. Mollick "Playing Pretend" (Prompting Science Report 4, arXiv:2512.05858, Dec 2025): expert personas dropped MMLU from 71.6% to 68.0% across 6 frontier models. Zheng EMNLP 2024 (162 personas, 9 models): zero significant improvement. Confirmed in arXiv:2603.18507 (PRISM): personas improve tone/alignment but damage factual accuracy.
3. Low-knowledge personas actively hurt. o4-mini dropped 73% to 67% with a toddler persona; GPT-4o dropped 46% to 41%. Gemini 2.5 Flash refused to answer 10.56/25 trials with mismatched expert personas (Mollick PSR4).
4. Role prompts change tone and analytical framing, not correctness. Use specific domain framing only when you need a particular perspective: "senior tax attorney specializing in Section 1031 exchanges" beats "expert."
5. Use second person ("You are..."). Both Anthropic and OpenAI ship this pattern; their models are most heavily tested against it. No rigorous evidence supports alternatives.

## Structure order

For modern agent prompts, use this hierarchy:

1. Identity (1-2 sentences, factual)
2. Outcome contract (desired result, success criteria, evidence, allowed side effects, stop rule)
3. Constraints (non-negotiable rules, stated positively)
4. Instructions (specific, actionable - not "be thorough" but what to do)
5. Output specification (format, structure)
6. Examples (when needed - see few-shot rules)
7. Critical reminders at the end only when they carry real priority

Anthropic guidance: put longform data at the top and the query at the end for long-context work. OpenAI GPT-5 / 5.1 / 5.2 guidance favors outcome-first prompts: expected result, constraints, output shape, and verification before detailed process. Both vendors use the same overall shape.

## Outcome-first design and the Done-when contract

Start by defining what a successful answer or agent run looks like.

A high-quality prompt answers these questions in observable terms:

1. What artifact or behavior should exist at the end?
2. What evidence proves it is acceptable? (the "done-when" contract)
3. What sources, files, or inputs may the model use?
4. What side effects are allowed?
5. When should the model ask, abstain, or report blocked instead of guessing?

Modern reasoning models perform worse when every intermediate step is prescribed. Add step order only when order affects safety, correctness, or side effects ("Decreasing Value of CoT" arXiv:2506.07142, "Evolving Prompt Effectiveness" arXiv:2510.22251).

For simple tasks the outcome contract can be one line. For long-running agents it should include acceptance criteria, verification commands, side-effect gates, and final-report shape. The 2026 evolution names this the "instruction contract": a testable spec the agent and the user agree on before execution.

Standard 2026 stop conditions for agentic prompts:

- Milestone fully implemented and verified.
- Real blocker requires human input (data loss risk, security boundary, missing access).
- Budget or permissions prevent safe progress.
- Human pauses or redirects.

## Information positioning

Models attend to information in this order: user message > beginning of system prompt > end of system prompt > middle sections.

The "lost in the middle" effect (Liu et al. TACL 2024, arXiv:2307.03172): >30% performance drop when relevant information is in the middle of context. Even long-context models exhibit this.

Mechanistically explained by arXiv:2502.01951 ("On the Emergence of Position Bias"): the causal mask plus multi-layer attention amplify earlier-token bias regardless of semantics. Confirmed as architectural in OpenReview XSHP62BCXN. No production model has eliminated this as of April 2026.

Chroma "Context Rot" (2025, 18 frontier models including Claude 4 Opus / Sonnet, GPT-4.1, GPT-5, Gemini 2.5 Pro / Flash, Qwen3): all models degrade as input grows. 20-50% accuracy drops from 10K to 100K tokens. Even a single distractor reduces performance.

Opening tokens are prime real estate. Do not waste them on generic role declarations or motivational language.

At 500 instructions, even the best frontier models achieve only 68% accuracy, with bias toward earlier instructions (IFScale arXiv:2507.11538 - 20 frontier models). AgentIF (arXiv:2505.16944) and ManyIFEval (arXiv:2509.21051) confirm degradation begins around 100-250 instructions.

## Formatting

Use Markdown headers for sections. Use XML tags for data boundaries (especially for Claude). Avoid JSON for document formatting - it performed "particularly poorly" for long-context retrieval (OpenAI GPT-4.1 guide).

Format ranking for long-context: XML > ID|TITLE|CONTENT > JSON (OpenAI testing).

Hybrid approach works well: Markdown headers for sections, XML tags for data delimiters and examples.

Be consistent within a prompt. The specific format matters less than consistency on modern models.

Prompt sensitivity to formatting persists. ProSA EMNLP 2024 (arXiv:2410.12405): LLaMA-2-13B varies up to 76 points between equivalent format changes. "When Punctuation Matters" arXiv:2508.11383 (Aug 2025, 8 models, 52 tasks): whitespace and punctuation alone introduce large output shifts. Larger and newer models are more robust but not immune.

For structured output: do not force JSON during reasoning. JSON-mode dropped Claude-3-Haiku from 86.51% to 23.44% on GSM8K and GPT-3.5-Turbo from 76.60% to 49.25% ("Let Me Speak Freely?" EMNLP 2024 arXiv:2408.02442). Let models reason in free text first, then convert to structured format in a second pass, or use the API's structured-output / strict-tool feature instead of describing the schema in prose.

## Conciseness and context rot

Every token competes for attention budget. Context rot is real.

- ~113k tokens of conversation history drops accuracy by 30% vs a focused 300-token version (Chroma).
- Even a single distractor in context reduces performance.
- 27.61% performance gap between verbose and concise responses (Qasper, arXiv:2411.07858). GPT-4 exhibits "Verbosity Compensation" 50.40% of the time - padding when uncertain.
- Generic quality instructions ("be accurate", "be helpful") were selected far less often than chance by genetic optimization across 47 task types (SPRIG arXiv:2410.14826).
- Anthropic Claude Code best practices: bloated CLAUDE.md files cause Claude to ignore the actual instructions.

Token budget guidelines:

- Task prompts: under 500 tokens.
- System prompts: under 1500 tokens.
- Skill SKILL.md body: under 5000 tokens (under 500 lines).
- Every instruction must earn its place.

For long-running agents, use compaction (high-fidelity summarization that preserves architectural decisions and unresolved bugs) and just-in-time retrieval. Sub-agents should return 1k-2k token summaries, not raw transcripts (Anthropic context-engineering guidance).

## Model-generation awareness

Optimal prompting strategies co-evolve with model capabilities. What worked on GPT-3.5 may hurt on GPT-5. What worked on Claude 3 may be counterproductive on Claude 4.6 / 4.7. Cross-generation finding: sculpted prompts that helped GPT-4o (97% vs 93% standard CoT) became detrimental on GPT-5 (94% vs 96.36% CoT) - "Evolving Prompt Effectiveness" arXiv:2510.22251.

### Claude 4.6 / 4.7 (Opus 4.7, Sonnet 4.6, Haiku 4.5)

- More responsive to system prompts than predecessors - dial back aggressive language.
- Remove anti-laziness prompts ("be thorough", "do not be lazy"). They amplify already-proactive behavior, causing runaway thinking or write-then-rewrite loops.
- Soften tool-use language. "You must use [tool]" causes overtriggering. "Use [tool] when it would help" works.
- Remove explicit think-tool instructions - causes over-planning.
- Manual `budget_tokens` and `thinking: {type: "enabled"}` are deprecated on 4.6 and removed on 4.7. Use `thinking: {type: "adaptive"}` plus the `effort` parameter (`low | medium | high | xhigh | max`).
- Prefilled assistant responses are deprecated on 4.6+ and rejected on 4.7. Use `<output>` tags or system-prompt instructions like "Respond directly without preamble".
- 4.7 follows instructions more literally. State scope explicitly ("Apply this formatting to every section, not just the first one"). Avoid scope-restricting language like "Only report high-severity issues" - 4.7 will literally drop everything else; ask for full coverage with severity tags instead.
- 4.7 calibrates verbosity to perceived complexity. Tune with positive examples ("Provide concise responses"), not "do not be verbose".

### OpenAI GPT-5 / 5.1 / 5.2

- Outcome-first prompts outperform inherited process-heavy stacks.
- Tune `reasoning_effort` (`none | minimal | low | medium | high | xhigh`) and `verbosity` as configuration knobs in the API instead of writing prose that approximates them. GPT-5.2 default is `none`; calibrate up only for genuinely complex multi-step work.
- Contradictory instructions damage GPT-5 reasoning more than prior models - the model burns tokens reconciling. Use "Do not" exception clauses to carve narrow exclusions instead of layering positive directives.
- Apply scope discipline explicitly: "Implement EXACTLY and ONLY what the user requests."
- Calibrate tool persistence with budgets. Provide escape hatches for proceeding under uncertainty.
- Final-reminders pattern at the end is no longer load-bearing on GPT-5.2 - skip routine repetition. Reserve it for resolving a specific contradiction or for older models that benefit from recency exploitation.
- Metaprompting works well - ask GPT-5 to improve its own prompt from concrete failures.

### Codex (GPT-5.3-Codex)

- Coding-agent prompts need autonomy, codebase exploration, edit safety, and a verification contract.
- Bias to action over clarification. Persist end-to-end within a single turn whenever feasible. Deliver working code, not just a plan.
- Prefer dedicated tools over shell. Always parallelize independent reads. Avoid hard-coded tool-call order unless the harness contract requires it.
- Allow short preambles every 1-3 logical steps; hard floor every 6 steps or 10 tool calls. Routine progress preambles for non-interactive rollouts are wasteful.
- Include rules for when to continue with assumptions versus when to ask because risk is high (data loss, security, external impact).

### Reasoning models in general (o-series, GPT-5 reasoning, Claude with thinking)

- Do not request visible chain-of-thought. Reasoning happens internally; "think step by step" is counterproductive on these models ("Decreasing Value of CoT" arXiv:2506.07142, "Reasoning Models Struggle to Control CoT" arXiv:2603.05706 - 13 models tested, controllability mostly <10%).
- Prompt repetition helps non-reasoning models without latency cost; it is neutral for reasoning models (arXiv:2512.14982).
- Complex prompts dilute structured reasoning. Accuracy drops from 100% in isolation to 0-30% under instruction interference (arXiv:2603.13351).

## Tool and agent mechanics

Tool quality depends more on tool definitions than on a long system prompt.

For each tool, the best prompt-adjacent information is:

1. What the tool does.
2. When to use it.
3. When not to use it.
4. Parameter meanings, formats, and caveats. Use specific names (`user_id` not `user`). Use namespace prefixes (`asana_projects_search`).
5. Output meaning, missing fields, and common errors. Return semantic identifiers (`name`) over technical (`uuid`) when possible.
6. Side effects and retry safety.

Treat the agent computer interface (ACI) with as much care as the human interface. Even small refinements yield large gains - Sonnet 3.5 hit SOTA on SWE-bench from tool description tweaks alone.

For agent prompts, keep cross-tool policy in the prompt: approval gates, destructive-action rules, evidence standards, parallelization policy, and final-report expectations.

Avoid brittle choreography ("always call A, then B, then C") unless the product contract requires that order. Prefer decision rules and done criteria.

Subagent briefing rules:

- Subagent context starts empty. The parent must include file paths, error messages, and prior decisions.
- One-way communication: parent → child → parent. Never child → child.
- Subagents return structured summaries with file paths and line numbers, not raw transcripts.

## Few-shot rules

1. Few-shot examples work primarily by defining task format, not by teaching reasoning (Min et al. EMNLP 2022 arXiv:2202.12837: random labels barely hurt performance).
2. 1-2 examples show strong accuracy gains. Diminishing returns beyond 4-5.
3. Diverse examples beat many similar examples.
4. Examples must perfectly match desired behavior - models adopt patterns exactly, including mistakes. Anthropic specifically warns Claude 4.x "pays extremely close attention to example details".
5. Modern reasoning models often prefer zero-shot. Few-shot can degrade DeepSeek-R1 and o-series ("Zero-shot Can Be Stronger than Few-shot" arXiv:2506.14641). Test both.
6. Use examples for formatting and style requirements. Skip them for straightforward tasks.
7. Few-shot safety demonstrations enhance role-playing prompts (+4.3%) but degrade task-oriented prompts (-21.2%). Match the technique to the prompt style.

## Positive framing

Tell the model what to do, not what not to do. "Don't use markdown" works worse than "Write in flowing prose paragraphs."

State constraints positively where possible. Reserve negative framing for actual safety boundaries. ACM CIKM 2025 ("Yes is Harder than No" DOI:10.1145/3746252.3761350) confirms an asymmetry: models say "yes" only when confident and "no" under uncertainty - positive directives reduce the model's uncertainty load.

When you must restrict a behavior on Claude 4.7, use a "Do not" exception clause inside a positive directive ("Cover every section. Do not stop after the first.") rather than a standalone negative.

## Chain-of-thought guidance

1. For reasoning models (o-series, GPT-5 reasoning, Claude with thinking enabled): do not request private chain-of-thought. Reasoning happens internally. Ask for concise rationale or evidence in the final answer when needed. Models cannot reliably control their CoT - controllability is mostly <10% and decreases by an order of magnitude during reasoning training (arXiv:2603.05706).
2. For non-reasoning models: CoT helps modestly (Gemini Flash 2.0 +13.5%, Sonnet 3.5 +11.7%; GPT-4o-mini only +4.4% and not statistically significant). But 35-600% longer response times. Mollick PSR2 (arXiv:2506.07142): non-reasoning gains come with higher variance - errors on items the model would otherwise get right.
3. Zero-shot CoT ("Let's think step by step") matches few-shot CoT on strong modern models (Qwen2.5 series, arXiv:2506.14641).
4. Do not force structured output during reasoning. Free-text reasoning followed by a separate format pass beats single-pass JSON (see Formatting).
5. CoT is brittle outside the training distribution ("CoT a Mirage?" arXiv:2508.01191). Do not rely on it for novel tasks.

## Emphasis and tone

Where you once needed "CRITICAL: You MUST use this tool when...", now "Use this tool when..." works (Anthropic 4.6 / 4.7 guidance, OpenAI GPT-5.1 / 5.2 guidance). Aggressive language causes overtriggering on modern models.

Reserve CAPS for actual safety-critical rules. Use sparingly.

No emotional manipulation, tipping, or threats. Tipping ($200-$1000) and threatening showed no reliable aggregate effect across controlled studies (Mollick Reports 1, 3 - SSRN 5165270, SSRN 5375404). Original EmotionPrompt 10.9% gains do not replicate on 2025-2026 models (arXiv:2604.02236).

Politeness has minimal aggregate impact (up to 60 percentage point differences on individual questions, but balanced out across datasets - Mollick PSR1).

## Contradictions and instruction following at scale

Contradictory instructions cause silent, unpredictable failures. Models silently drop instructions rather than flag conflicts (SIFo Benchmark 2024, "Control Illusion" arXiv:2502.15851). Even GPT-4 and Claude 3 often fail to complete all instructions when facing multiple conflicting requirements.

System / user prompt separation does not provide a reliable instruction hierarchy ("Control Illusion" 2025). OpenAI's instruction-hierarchy training (arXiv:2404.13208, deployed in GPT-4o-mini and successors) reduces but does not eliminate this.

Audit prompts for contradictions. The model will not tell you they exist.

GPT-5 and successors are more sensitive to contradictions than prior generations. The model spends extra reasoning tokens trying to reconcile and often produces lower-quality output as a result.

## Templates, variables, and evals

Use prompt templates and variables for prompts that will be reused. Keep stable instructions separate from dynamic user data so the prompt is easier to test, diff, cache, and version. Place stable text first and dynamic variables last for caching.

Wrap variables in clear boundaries, especially when variable content is untrusted or long.

For production prompts, pair changes with evals or at least representative failure examples. Strong prompt improvement starts from observed failures:

1. Collect examples where the prompt failed or produced weak output.
2. Name the failure mode for each one.
3. Group failures into clusters; patch the cluster, not individual cases.
4. Add the smallest rule, example, or output contract that blocks the cluster.
5. Re-run examples or graders before accepting the change.

Use API structured outputs or tool schemas when strict output validation matters. Do not spend hundreds of prompt tokens describing a schema the API can enforce.

### Eval grader contract

A reproducible LLM-as-judge grader has six required components. A grader missing any one of them produces unstable scores across runs and is unsafe to use as a quality signal.

1. **Per-dimension definition.** State what each dimension measures in one or two sentences. Dimension labels alone (faithfulness, coverage, conciseness) are not enough - graders bias toward whichever interpretation the source data suggests.
2. **Calibration anchors.** Define what counts as low / mid / high (or 0 / 0.5 / 1) for each dimension with a concrete example or a written rule. Without anchors, graders drift and inter-rater agreement collapses.
3. **Independence rule.** State that scoring dimensions are evaluated independently; a low score on one does not imply low scores on others.
4. **Input contract.** Specify the allowed evidence (reference + candidate, source + summary, etc.) and forbid the grader from drawing on outside knowledge. LLM judges otherwise inject memorized facts.
5. **Output schema.** Strict JSON with the rubric fields plus a one-line rationale tying each score to the inputs. No prose preamble, no markdown fences inside the JSON.
6. **Edge cases.** Define behavior for empty / identical / refused / non-cooperative candidates. The grader returns a defined failure shape, not a hallucinated score.

Treat the candidate text as untrusted (LLM-as-judge prompt-injection attack surface) - apply data-marking or sandwich defense around it.

## Multi-agent and orchestration

Single-agent baselines are stronger than the multi-agent literature suggests. arXiv:2604.02460 and arXiv:2601.12307: at equal token budget, well-prompted single-agent setups beat multi-agent on multi-hop reasoning and many coding tasks. Anthropic's deep-research agent shows 90.2% improvement over single-agent for breadth-first research, but uses ~15x tokens.

Default to single-agent. Reach for multi-agent only when the task is breadth-first parallelizable, fits a routing pattern, or requires evaluator-optimizer feedback loops.

When you do use multi-agent prompts:

- Lead agent specifies objective, output format, tool guidance, and boundary per subagent.
- Scale rules in-prompt: simple = 1 subagent / 3-10 calls; comparison = 2-4 subagents / 10-15 calls each.
- Use JSON for structured state files (less prone to model corruption than Markdown).
- Three-agent harness (planner / generator / evaluator) is the 2026 long-running pattern. The evaluator owns a "sprint contract" - acceptance criteria negotiated before implementation.

Coding tasks remain a poor multi-agent fit because they need shared context (Cognition "Don't Build Multi-Agents", 2025). Two principles are now consensus: share context, and remember actions carry implicit decisions.

## Automated optimization

Human intuitions about what makes a good prompt are frequently wrong. Automated optimization consistently outperforms human-crafted prompts.

- APE: outperformed human-engineered prompts on 19/24 tasks (arXiv:2211.01910).
- OPRO: up to 8% on GSM8K and 50% on Big-Bench Hard versus human-designed (arXiv:2309.03409).
- PromptWizard: 5x cheaper than continuous optimization, 16-60x cheaper than discrete methods (arXiv:2405.18369).
- SAMMO: 10-100% gains in instruction tuning, 26-133% in RAG tuning, >40% in prompt compression (arXiv:2404.02319).
- GEPA (arXiv:2507.19457, ICLR 2026 Oral): reflective evolution plus Pareto frontier. Beats MIPROv2 by ~12 percentage points; beats GRPO by 6-19 points with 35x fewer rollouts. Now state of the art for prompt optimization.
- MetaSPO (arXiv:2505.09666): meta-learning for cross-task system prompts.

If a prompt matters enough to optimize, run it through GEPA, PromptWizard, or a successor. Two-step metaprompting (analyze failures, then make surgical revisions) approximates the same gain without special tooling.
