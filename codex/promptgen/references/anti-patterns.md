# Anti-patterns checklist

Verify the generated prompt contains none of these. Each item has evidence for why it hurts.

## Must not contain

1. **Adjective stacking** - "expert, meticulous, thorough, world-class" in identity section. Static expert personas don't improve accuracy (Mollick Report 4: 6 frontier models, no significant effect. Zheng EMNLP 2024: 162 personas, zero improvement).

2. **Generic quality instructions** - "be accurate," "be helpful," "provide high-quality responses," "be thorough." Genetic optimization across 47 task types selected these far less often than chance (SPRIG 2024). They add tokens but not signal.

3. **Tipping or incentives** - "$200 tip for a good answer," "I'll pay you," "bonus for accuracy." No reliable aggregate effect across controlled studies (Mollick Report 3: tested $200-$1000 tips and threats, no significant benchmark effect).

4. **Anti-laziness directives** - "do not be lazy," "think carefully," "be thorough," "don't skip steps." On Claude 4.6, these amplify already-proactive behavior causing runaway thinking or write-then-rewrite loops (Anthropic Claude 4.6 best practices).

5. **Aggressive emphasis on routine instructions** - "CRITICAL: You MUST use this tool," "IMPORTANT: ALWAYS do X." Where you once needed this, now "Use this tool when..." works. Previous aggressive language causes overtriggering on modern models (Anthropic 4.6, OpenAI GPT-5.1/5.2 guidance).

6. **Contradictory instructions** - any two instructions that conflict. Models silently drop one instead of flagging the conflict (SIFo Benchmark 2024). "Control Illusion" (2025): system/user separation fails to provide reliable hierarchy.

7. **Negative-only framing** - "Don't use markdown," "Never include headers," "Do not format as a list." Less effective than positive alternatives: "Write in flowing prose paragraphs" (Anthropic best practices).

8. **Emotional manipulation** - "this is very important to my career," "lives depend on this," "I'm counting on you." EmotionPrompt results are contested. Mollick's controlled studies found no aggregate effect.

9. **Motivational language** - "you are the best at what you do," "you excel at this task," "your expertise is unmatched." No empirical support. Wastes prime opening tokens.

10. **AI vocabulary** - additionally, crucial, delve, enhance, foster, garner, highlight (verb), intricate, key (adj), landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore (verb), valuable, vibrant. These are tells that the prompt was AI-generated.

11. **Filler phrases** - "in order to" (use "to"), "due to the fact that" (use "because"), "it is important to note that X" (just say X). Every token competes for attention budget.

12. **Excessive emphasis** - CAPS and bold on more than 2-3 items. Reserve for actual safety-critical rules. Overuse dilutes the signal and causes the model to overtrigger on emphasized items.

## Self-check process

After generating a prompt, scan it against all 12 items above. If any are present:

1. Identify the specific violation
2. Rewrite to eliminate it
3. Verify the fix doesn't introduce a new violation
4. Confirm total token count stays within budget
