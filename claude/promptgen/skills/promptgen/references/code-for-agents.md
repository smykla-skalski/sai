# Code format and style for AI agent comprehension

Condensed from 21 empirical studies (2022-2025). Full research with all citations at `tmp/research/code-for-agents.md`.

# Contents

- [Naming](#naming)
- [Comments and docstrings](#comments-and-docstrings)
- [Dead code](#dead-code)
- [Type annotations](#type-annotations)
- [Function length](#function-length)
- [File length and position effects](#file-length-and-position-effects)
- [Whitespace and formatting consistency](#whitespace-and-formatting-consistency)
- [Code chunking for RAG](#code-chunking-for-rag)

## Naming

Identifier names are the single most influential surface feature for agent code comprehension.

Fully anonymizing names collapsed retrieval MRR from 70% to 17% for Java and 68% to 24% for Python on CodeBERT/GraphCodeBERT (arXiv:2307.12488).

Misleading names (shuffled to create wrong associations) hurt more than random names - models learn spurious correlations and apply them confidently.

On class-level summarization: GPT-4o dropped 29 points (87.3% to 58.7%) after alpha-renaming; DeepSeek V3 dropped 11 points (arXiv:2510.03178).

Casing changes caused 100% worst-case accuracy drop for Java with smaller models (TokDrift, arXiv:2510.14972).

**Rule for generated prompts:** Use descriptive, consistent names. Misleading names are worse than terse ones.

## Comments and docstrings

Missing comments are neutral; incorrect comments actively hurt.

Random (incorrect) comments reduced GPT-3.5 unit test success to 22.1% and GPT-4 to 68.1% (arXiv:2404.03114).

Misleading comments as code mutations reduced debugging accuracy to 24.55%; absent or partial comments caused no statistically significant change for GPT-4 (arXiv:2504.04372).

Comment density in training data correlates with 6-13% benchmark gains (arXiv:2402.13013).

**Rule for generated prompts:** Write correct comments or none. A wrong comment is worse than silence.

## Dead code

Inserting unreachable statements reduced debugging accuracy to 18.5% - the largest single-mutation impact found across all studies (arXiv:2504.04372).

Models cannot filter dead branches; attention weights non-functional tokens the same as functional ones.

**Rule for generated prompts:** Remove dead code, unreachable branches, and commented-out blocks before presenting code to an agent.

## Type annotations

94% of LLM compilation errors stem from type check failures.

Type-constrained decoding cuts compilation errors by more than half and improves functional correctness across models up to 34B parameters (arXiv:2504.09246, PLDI 2025).

Type annotations are machine-verifiable documentation that cannot be wrong the way natural language comments can.

**Rule for generated prompts:** Include type annotations in code agents will read or generate. For code-gen tasks, instruct the agent to annotate types.

## Function length

No study directly benchmarks an optimal function line count, but retrieval studies imply a practical ceiling.

Functions that exceed a single chunk boundary harm retrieval: the chunk bisects the function and neither half is useful as standalone context (arXiv:2510.06606).

Practical chunk size by context budget: 32-64 lines for 4K tokens, 64-128 lines for 4K-8K tokens, whole-file viable at 16K+.

Context length alone (independent of content) degrades accuracy: open-source models lost 44-59% at 7K tokens even with perfect retrieval (arXiv:2510.05381).

**Rule for generated prompts:** Keep functions small enough to fit in one retrieval chunk. For code-gen, instruct the agent to prefer small, focused functions.

## File length and position effects

The "lost in the middle" effect applies within files, not just RAG contexts: faults in the first 25% of a file are found 60% of the time; faults in the final 25% only 13% (arXiv:2504.04372).

Agents front-load attention regardless of where relevant logic sits.

**Rule for generated prompts:** Put the most important logic near the top of files. For review or debugging tasks, tell the agent that content late in a file is more likely to be missed.

## Whitespace and formatting consistency

Mixed formatting (some elements removed, some kept) degrades performance more than either extreme consistently formatted (arXiv:2508.13666).

Spacing changes around operators trigger the highest per-rewrite sensitivity rate (10%+) of any formatting change, driven by tokenizer fragmentation (arXiv:2510.14972).

**Rule for generated prompts:** Pick one formatting style and apply it throughout. Inconsistent formatting is worse than any single consistent choice.

## Code chunking for RAG

AST-based chunking (splitting at function/class boundaries) outperforms fixed-size line chunking by 4-6 points on Pass@1 for code completion tasks (cAST, arXiv:2506.15655, EMNLP 2025).

For code-to-code retrieval: BM25 with word-level splitting is 14x faster than dense embeddings with comparable accuracy.
For NL-to-code retrieval: dense embeddings outperform BM25 by 14 NDCG points at 270x higher latency cost.

Function/method is the minimum effective retrieval unit - GraphCodeAgent, STALL+, and LocAgent converge on this independently.

**Rule for generated prompts:** For RAG-based code agents, instruct AST/function-boundary chunking. For repo-level agents, treat function as the minimum navigation unit.
