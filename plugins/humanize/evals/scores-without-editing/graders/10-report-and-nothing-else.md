---
type: llm
focus: last_message
weight: 1
---

This was a score-only request, so the reply should be the pattern report and nothing more.

PASS if the reply consists of the pattern report table and a short summary line (patterns, categories, overall severity), optionally with one short line saying the file was not changed.
FAIL if the reply adds anything beyond that, such as a list of claims lacking evidence, a disclaimer about authorship, advice on how to rewrite, or a follow-up offer.
