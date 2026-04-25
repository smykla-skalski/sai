# Anti-patterns checklist

Verify the generated prompt contains none of these. Each item lists the evidence for why it hurts.

## Must not contain

1. **Adjective stacking** - "expert, meticulous, thorough, world-class" in identity. Static expert personas underperform plain prompts on factual tasks. Mollick PSR4 (arXiv:2512.05858, Dec 2025): expert personas dropped MMLU from 71.6% to 68.0% across 6 frontier models. Zheng EMNLP 2024 (162 personas, 9 models): zero significant improvement. Confirmed by arXiv:2603.18507 (PRISM): personas help tone, hurt facts.

2. **Generic quality instructions** - "be accurate", "be helpful", "provide high-quality responses", "be thorough". Genetic optimization across 47 task types selected these far less often than chance (SPRIG arXiv:2410.14826). They add tokens but not signal.

3. **Tipping or incentives** - "$200 tip for a good answer", "I'll pay you", "bonus for accuracy". No reliable aggregate effect across controlled studies (Mollick PSR3 SSRN 5375404, Aug 2025: tested $200-$1000 tips and threats; no significant benchmark effect). Original EmotionPrompt 10.9% gain does not replicate on 2025-2026 models (arXiv:2604.02236).

4. **Anti-laziness directives** - "do not be lazy", "think carefully", "be thorough", "do not skip steps". On Claude 4.6 / 4.7 these amplify already-proactive behavior, causing runaway thinking or write-then-rewrite loops (Anthropic Claude 4.6 / 4.7 best practices). On GPT-5.2 they trigger tool overuse.

5. **Aggressive emphasis on routine instructions** - "CRITICAL: You MUST use this tool", "IMPORTANT: ALWAYS do X". Anthropic 4.6 / 4.7 and OpenAI GPT-5.1 / 5.2 guidance: "Use this tool when..." now suffices. Aggressive language causes overtriggering.

6. **Contradictory instructions** - any two instructions that conflict. Models silently drop one instead of flagging the conflict (SIFo Benchmark 2024, "Control Illusion" arXiv:2502.15851). GPT-5 and successors are more sensitive to contradictions than predecessors - the model burns reasoning tokens reconciling.

7. **Negative-only framing** - "Don't use markdown", "Never include headers", "Do not format as a list". Less effective than positive alternatives ("Write in flowing prose paragraphs"). ACM CIKM 2025 ("Yes is Harder than No" DOI:10.1145/3746252.3761350): models say "yes" only when confident and "no" under uncertainty - positive directives reduce uncertainty load. Use "Do not" exception clauses inside positive directives only when restricting a specific behavior.

8. **Emotional manipulation** - "this is very important to my career", "lives depend on this", "I'm counting on you". EmotionPrompt results are contested. Mollick PSR1 / PSR3 controlled studies: no aggregate effect.

9. **Motivational language** - "you are the best at what you do", "you excel at this task", "your expertise is unmatched". No empirical support. Wastes prime opening tokens.

10. **AI vocabulary** - additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate, intricacies, key (adjective), landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore (verb), valuable, vibrant, groundbreaking, renowned, breathtaking, nestled, in the heart of, profound, furthermore, moreover. These are tells that the prompt is AI-generated.

11. **Filler phrases** - "in order to" (use "to"), "due to the fact that" (use "because"), "it is important to note that X" (just say X), "could potentially possibly" (one qualifier max). Every token competes for attention budget.

12. **Excessive emphasis** - CAPS and bold on more than 2-3 items. Reserve for actual safety-critical rules. Overuse dilutes signal and causes overtriggering on emphasized items (Anthropic 4.6 / 4.7).

13. **Brittle tool choreography** - "always call tool A, then B, then C" when decision rules would work. Current agent guidance favors clear tool descriptions, side-effect policy, and done criteria over hard-coded call order unless order is safety-critical.

14. **Mandatory preambles and upfront plans by default** - requiring visible plans, progress notes, or preambles for every task interrupts coding-agent rollouts and wastes tokens. Add visible planning only when the user or product experience needs it. For long Codex rollouts, allow short preambles every 1-3 logical steps; hard floor every 6 steps or 10 tool calls.

15. **Hard-coded current dates in reusable prompts** - reusable prompts with fixed dates go stale. Include date context only when the runtime does not provide it or the task is explicitly time-sensitive.

16. **Private chain-of-thought requests** - "show all reasoning", "include hidden thoughts". For reasoning models (o-series, GPT-5 reasoning, Claude with thinking enabled), this is counterproductive. Models cannot reliably control their CoT - controllability is mostly <10% (arXiv:2603.05706 "Reasoning Models Struggle to Control CoT", 13 models). Ask for concise rationale or evidence in the final answer instead.

17. **"Think step by step" on reasoning models** - explicitly counterproductive on o-series, GPT-5 reasoning, and Claude with thinking enabled. Reasoning happens internally. The phrase trains the model toward visible step-by-step output that competes with internal reasoning ("Decreasing Value of CoT" arXiv:2506.07142, "Reasoning Models Struggle to Control CoT" arXiv:2603.05706).

18. **Schema prose that should be enforced by tooling** - long natural-language JSON schema descriptions when the target API supports structured outputs, strict tools, or validators. Use runtime validation when available. Forcing JSON during reasoning collapses accuracy ("Let Me Speak Freely?" EMNLP 2024 arXiv:2408.02442 - Claude-3-Haiku 86.51% to 23.44% on GSM8K).

19. **No escape hatch** - prompts that force an answer when evidence is absent. Define when to say "not found", "insufficient evidence", "blocked", or ask for missing input. Provide an explicit escape ("if uncertain after [budget], answer with the best available evidence and flag the uncertainty").

20. **Routine final reminders** - repeating instructions at the end "for emphasis" on every prompt. GPT-5.2's stronger instruction adherence makes this redundant; on Claude 4.6 / 4.7 it can cause overtriggering on the emphasized items. Reserve recency repetition for resolving a specific contradiction or for older models that benefit from recency exploitation.

21. **Scope-restricting "Only X" phrasing on Claude 4.7** - "Only report high-severity issues" causes 4.7 to literally drop everything else. Ask for full coverage with severity tags or confidence labels and let the consumer filter.

22. **Verbose instruction stacks** - cramming more rules in makes the model worse at following the ones that matter. IFScale arXiv:2507.11538 (20 frontier models, 500 instructions): best models hit only 68%. AgentIF (arXiv:2505.16944) and ManyIFEval (arXiv:2509.21051): degradation begins around 100-250 instructions. Specify only what the model would get wrong without the instruction.

23. **Manual `budget_tokens` and `thinking: {type: "enabled"}` for Claude** - deprecated on 4.6 and removed on 4.7 (returns 400). Use `thinking: {type: "adaptive"}` plus the `effort` parameter (`low | medium | high | xhigh | max`).

24. **Prefilled assistant responses on Claude 4.7** - deprecated on 4.6+ and rejected on 4.7. Use `<output>` tags or system-prompt instructions like "Respond directly without preamble".

25. **"Maximize" / "thoroughly" tool-use language on GPT-5** - triggers redundant tool calls. Use specific budgets ("max 2 search calls before answering") and provide an escape hatch.

26. **Mandatory upfront plans on Codex** - causes early stopping and wasted tokens. Allow planning only when the user or product experience needs it.

27. **Subagent overuse** - on Claude 4.6 / 4.7, agents are eager to spawn subagents. Without a scope boundary, parents will delegate work that should be done inline. Add: "For simple tasks and single-file edits, work directly instead of delegating." Default to single-agent. Reach for multi-agent only when the task is breadth-first parallelizable, fits a routing pattern, or requires evaluator-optimizer feedback.

28. **Sycophantic openings and chatbot artifacts** - "Great question!", "Certainly!", "Happy to help", "I hope this helps", "Let me know if...". Wastes opening tokens and is a tell of an unrefined prompt.

29. **AI-vibe patterns** - "serves as a testament", "pivotal moment", "marks a shift", "setting the stage", "rich heritage", "stunning", "must-visit", "commitment to", "the future looks bright", "exciting times ahead". Cut or replace with specifics.

30. **Synonym cycling** - using different words for the same concept across a prompt. Pick one term per concept and stick with it.

31. **Inline-header lists** - bulleted lists shaped like `**Header:** description`. Use prose paragraphs or proper headings, not pseudo-bullets.

32. **Vague attributions** - "experts argue", "observers note", "studies show" without citing the specific source. Either cite specifically or remove the appeal to authority.

33. **Boldface overuse** - mechanical bold on every proper noun and acronym. Reserve bold for terms a careful reader might miss.

## Self-check process

After generating a prompt, scan it against all items above. If any are present:

1. Identify the specific violation.
2. Rewrite to eliminate it.
3. Verify the fix does not introduce a new violation.
4. Confirm total token count stays within budget.
5. Confirm no two instructions contradict each other.
