# Evidence map

Why the rules are what they are, and how strong each basis is. Read this when a rule is being questioned, when changing a rule, or when re-validating on a new model.

Grades: **A** controlled study or ablation with data. **B** observational or benchmark analysis. **C** vendor or tool-maker guidance. **I** inference or heuristic with no direct test.

Research was gathered in October 2026 from abstracts, papers and vendor documentation. Most results use SWE-bench-style tasks and 2025 to 2026 models. Numbers are quoted from the sources; the summary lines are not a substitute for the papers.

## Rule to evidence

| Rule | Basis | Grade |
| :-- | :-- | :-- |
| Be complete up front; the implementer will not reliably ask | Removing paths, traces and detail from Verified tasks cost about 16 points; agents asked only when prompted to ([Ask or Assume](https://arxiv.org/html/2603.26233v1), [Ambig-SWE](https://arxiv.org/html/2502.13069v3)) | A |
| Expected behavior and requirements are essential | Ablation removing requirements or expected behavior cost large shares of solves in two small models ([Khatib et al.](https://arxiv.org/abs/2607.07593)); requirements tied to tests lifted GPT-5 from 8.4% to 25.9% ([SWE-Bench Pro](https://arxiv.org/html/2509.16941)) | A |
| Runnable check per outcome | Top vendor consensus ([Claude Code](https://code.claude.com/docs/en/best-practices), [Codex](https://learn.chatgpt.com/guides/best-practices), [Devin](https://docs.devin.ai/essential-guidelines/instructing-devin-effectively), [Spotify](https://engineering.atspotify.com/2025/11/context-engineering-background-coding-agents-part-2)); targeted test context cut regressions from 6.08% to 1.82% in small models ([TDAD](https://arxiv.org/abs/2603.17973)) | C, A |
| Cover empty, boundary and error states | Frontier agents saturate visible tests while held-out suites show gaps ([SpecBench](https://arxiv.org/abs/2605.21384)); "trust-then-verify gap" in Claude Code docs | B, C |
| No acceptance check that pins one implementation | Audit of Verified found tests enforcing details unrelated to the task (secondary report of an OpenAI audit); procedural instructions without test context raised regressions (TDAD) | B |
| Name the suite that must stay green | TDAD; maintainers rejected benchmark-passing PRs for breaking other code ([METR](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/)) | A, B |
| Verified anchors allowed; no line numbers | Localization cues were among the strongest ingredients (Khatib et al., Sayagh); verified cause and symbol hints improved pass@1 while imperfect localizers did not consistently help ([From Finding to Fixing](https://arxiv.org/abs/2610.25826)). Staleness of paths is an inference | A, B, I |
| Hypotheses only with their verification | Same study: unverified localization was net-negative in most settings; misleading hints anchored early search | A |
| Executable repro beats prose steps | Reproduction scripts associated with resolution, prose steps not significant (Khatib et al.); reproduction tests helped pipelines ([TestPrune](https://arxiv.org/html/2510.18270v2)) | A, B |
| Stop-and-flag triggers | Agents almost never interact unprompted (Ambig-SWE); an explicit flag action cut test cheating from 54% to 9% for GPT-5, with a much weaker effect for Claude Opus 4.1 ([ImpossibleBench](https://arxiv.org/abs/2510.20270)) | A |
| "No change needed if" | Agents edited already-fixed code in 35 to 65% of cases; a verify-first prompt helped but over-abstained on partial fixes ([FixedBench](https://arxiv.org/html/2605.07769v1)) | B |
| Non-goals and Do-not lines | Negative constraints were the beneficial rules in rule files ([Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088)); strong models expand scope (Claude prompting guides); Spotify's top judge veto is acting outside the prompt | A, C |
| Do not restate repo-wide rules; name the instance | Root instruction files are re-injected after compaction while nested ones are not, and are advisory ([Claude Code memory and context docs](https://code.claude.com/docs/en/memory)); context files do not generally improve success and cost over 20% more ([Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)). Cross-layer repetition is untested | C, A, I |
| Hard prohibitions in a mechanical gate | Docs: advisory files versus deterministic hooks; read-only tests stop test edits but not special-casing (ImpossibleBench) | C, A |
| Decided versus your call | Hidden test requirements make valid solutions fail (SWE-Bench Pro interface rationale); no direct test of the labels | I |
| Self-contained, inline decisions | Largest Copilot merge-rate correlate ([Sayagh](https://arxiv.org/abs/2512.21426)); Claude Code docs; fresh agents assume shared state ([Cognition](https://cognition.com/blog/dont-build-multi-agents)) | B, C |
| Small scope, one change per agent | Scope correlates with merge (Sayagh); resolve rate falls as files and lines grow (SWE-bench Pro, Multi-SWE-bench); Spotify "one change at a time" | B, C |
| Vertical slicing | No study. Indirect: scope and one-change findings above | I |
| Constraints as short lines, restated after long runs | Compactors kept about 17% of injected constraints; a constraint registry kept over 90% ([Lost in Context Compaction](https://arxiv.org/abs/2608.11242)) | A |
| Keep headers and lists | Removing headers or flattening lists reduced solve rates with no content change in small models (Khatib et al.) | A |
| No word cap | Self-containment outranks brevity; length correlates negatively but is confounded with scope; no source supports a threshold | B, I |
| Complete spec up front, no procedural verify lines | Opus 5 and Sonnet 5.5 prompting guides | C |
| Self-check always; cold-read by threshold | See [cold-read.md](cold-read.md) and below | I, B |

## Cold-read gate basis

- LLM detection of underspecification is uneven. Ambig-SWE found detection ranging from chance for one model to 0.74 to 0.89 for another, with false positives rising as prompts pushed harder to ask.
- Requirement-ambiguity detection reported precision around 50% ([Orchid](https://arxiv.org/abs/2604.21505)), and the best Anthropic model in another study caught a median of 47% of expert-flagged requirement issues ([arXiv 2609.03230](https://arxiv.org/abs/2609.03230)). A cold reader cannot see intent, so the author's comparison against intent is the real check.
- A reviewer-critic loop on code gained 3.6 points at about 4.5 times the tokens and sometimes turned plausible concerns into unnecessary edits ([arXiv 2608.18167](https://arxiv.org/abs/2608.18167)).
- Vendors say to skip planning when the diff fits in one sentence, and that a reviewer asked to find gaps will usually report some even when the work is sound.
- Unproven: the gate's net effect on outcomes, its cost, its false-question rate on good issues, and every numeric threshold.

## Unproven or thin

- No study compares LLM-written with human-written issues with the implementer held constant.
- No measured rate of hallucinated paths, APIs or reproduction steps in LLM-written issues.
- No test of vertical versus horizontal slicing for agents.
- No test of out-of-scope lists or decided-versus-free labels written in an issue.
- No test of repeating a rule across instruction layers.
- No controlled comparison of EARS, Given/When/Then, bullets or free text for LLM implementers.
- Effect sizes come largely from small open-weight models and SWE-bench Verified, which carries leakage and memorization risk.
- Model advice drifts. Re-test on the model that will implement.

## Re-validating a rule

A cheap paired evaluation, as a design to follow when a rule change is contested:

1. Take 20 to 30 merged PRs from your repos that changed tests and have a runnable test command. Validate each: tests fail at the parent commit and pass with the real patch, three times. Drop flaky ones.
2. For each task, the writer sees only the original pre-PR request, never the diff. Write one issue per arm (current rules, candidate rules). Check each issue for leaked solution identifiers.
3. Run the implementer three times per task per arm in a fresh worktree at the parent commit with remotes removed and the PR's tests deleted. Run the model headless with a turn cap.
4. Grade with the hidden fail-to-pass tests and the pass-to-pass tests. Record files touched outside the real patch, diff-size ratio, lint and CI, tokens and turns, and stop-and-flag rate. Use an LLM judge only as a diagnostic.
5. Compute the per-task difference between arms and a paired bootstrap interval. Adopt the candidate only if the 90% lower bound is above zero and no guardrail (tokens, scope drift) regresses. Add tasks rather than repeats to gain power.

Twenty to thirty tasks only detect effects of roughly 15 to 20 points. The decision rule and power figures are guesses; compute the spread from a pilot. Results are specific to your repos and model.
