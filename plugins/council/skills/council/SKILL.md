---
name: council
description: Run current-request-only Codex reviewer-agent councils for code, architecture, design, UX, reliability, performance, AI, strategy, or tradeoff review. Use when asked for council review, multi-reviewer critique, debate, or design/code/architecture/UX feedback. No memory unless requested.
---

# Council of Experts

Use native Codex reviewer agents. Do not use Claude named subagents or nested `codex exec`.

Reviewer identity, dossier links, and review format are baked into native reviewer-agent definitions. The parent selects slugs, supplies bounded material, validates completed text, and synthesizes. Never pass identity text or source paths. Current-task only: no memory, prior sessions, prior outputs, or git history unless the user asks.

Agent registry and rosters: `references/agents.md`.

## Mode Selection

If the request starts with `@<path>`, read that file first as problem context.

Parse the first token as mode when it is `core`, `auto`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`; aliases: `eng`, `ux`, `mix`, `random`. Default to `core`.

- `core`: pick `core-eng`, `core-ux`, or `core-mix` from path and wording, then announce why.
- `auto`: read the registry, select exactly 6 best-fit reviewers, and include at least one bias-correction reviewer unless the request is narrow.
- fixed core modes: use only the Mode Rosters block; do not read the full registry tables.
- `all`: use every registry slug.
- `debate`: pick 3-6 reviewers for hard tradeoff calls.

## Codex Workflow

**Parent Work**

- Resolve mode, read explicit files, and build a bounded bundle from exact paths, diffs, snippets, and directly relevant adjacent context.
- Do not read memory, prior outputs, or broad repo context. If already loaded accidentally, exclude it from assignments and synthesis unless the user supplied it.
- If no explicit file/path/diff/snippet is available, run the council on the user's inline prompt; do not ask for a file just to satisfy the template.
- Select reviewer agent slugs from the registry. Merge/dedupe matches; drop reviewers that only add generic agreement.
- Do not pre-read native agent definitions or dossiers. Reviewers load their own identity and canon.
- Spawn each reviewer with `spawn_agent(agent_type: "<agent-slug>", fork_turns: "none")` and a task name using only lowercase letters, digits, and underscores. Do not pass `model` or `reasoning_effort` unless the user asks for an override.
- If a slug is unknown, skip it, continue with successful reviewers, and name the missing reviewer in the synthesis. Do not rebuild identity instructions in the assignment.
- Keep reviewers open for retries, debate rounds, or directly related follow-up work. Close every spawned reviewer after final result capture.

**Reviewer Assignment**

```text
<council-review-assignment>
Review summary: <problem context>
Primary review files:
- <absolute path 1, or `inline material only` when no file path was supplied>
Supplied review material:
<diffs, snippets, or full files assembled by the parent>
Allowed extra reads:
- Only directly connected files needed to understand a concrete relationship already visible in the supplied material.

Rules:
- This message is the complete review task. Follow your native agent definition, including any dossier read, as part of this same turn; then immediately return the review.
- Treat the supplied review material as the full scope.
- If primary review files says `inline material only`, review the supplied material anyway; that is the target, not missing context.
- Do not use broad repo discovery, tests/builds/linters, git history, file edits, or subagents.
- Do not report setup, AGENTS.md, RTK, tools, or readiness.
- Do not answer with "ready", "dossier loaded", "instructions loaded", "need task", or any acknowledgement-only response.
- If context is still missing after bounded reads, state the missing piece instead of exploring further.
- Return your agent descriptor's required review format, not generic `Findings:` output.
- Your first non-empty line must be your reviewer heading. Do not wrap the review in quotes, JSON, XML, or a status envelope.
</council-review-assignment>
```

**Result Handling**

- Wait with `wait_agent`, then inspect mailbox notifications. Finished content may arrive separately as `<subagent_notification>`.
- Parse reviewer text only from `status.completed` or `close_agent.previous_status.completed`; every other field is transport metadata. Never echo raw JSON, XML-like tags, notification envelopes, `status` objects, or tool payloads.
- Valid output must contain a reviewer-specific Markdown heading, the agent's required sections, and a real review body. Runtime `completed` status is the finish signal; do not require a textual completion marker that would conflict with agent-specific exact formats. Runtime `failed`, `cancelled`, `timed_out`, or empty output is not a review.
- Reject setup/status replies, acknowledgement-only replies, generic `Findings:` code-review output, missing reviewer heading, non-review execution, repo-wide discovery, or ignored scope.
- Recover once with `followup_task(interrupt: true)` on the same open agent. The follow-up must repeat the full assignment, including supplied material, and must say: "This is the review task; do not acknowledge readiness or ask for another task. Return only your required reviewer output now, and do not use generic Findings output." Do not send a short reminder without the review material.
- If the retry is still invalid, close and respawn once with `fork_turns: "none"` using the same strengthened full assignment. If the replacement fails, continue with successful reviewers and name the missing result.
- Drain mailbox updates until every reviewer has accepted output or terminal failure. If a reviewer appears done but no text was captured, call `close_agent` and harvest `previous_status.completed` before declaring it missing.
- Always close all spawned reviewers after their final accepted output or terminal failure; `wait_agent` is not cleanup. Do not finish while any spawned reviewer remains open. Ignore Codex session-recording warnings during close if the harvested review text is valid.
- Before final synthesis, check that every selected reviewer is accounted for as `accepted`, `missing`, or `failed`; the final answer must contain no raw notification tags, transport fields, or acknowledgement-only text.
- Synthesize convergence, real disagreement, and concrete next moves. Do not average reviewer output into bland consensus.

For debate mode, keep the same reviewer agents open across opening positions, responses, and final positions. Use `followup_task` for later rounds, require the same result validation each round, and close agents only after synthesis.

## Synthesis Shape

```markdown
# Council review: <topic>
## Convergence (high-confidence signals)
<2-5 bullets. Format: `- [finding] - [reviewer1, reviewer2, reviewer3]`.>
## Disagreement (real tradeoffs the user must decide)
<2-4 bullets. Format: `- [axis] - [reviewer A] argues X / [reviewer B] argues Y. Decision is yours because <constraint>.`>
## Per-reviewer top-3
<For each reviewer that returned, three concrete bullets.>
## What to do next
<3-7 numbered concrete actions, smallest first, tied back to reviewers.>
## What we did not address
<1-3 bullets naming gaps the council does not cover for this problem.>
```

## Privacy / Scope

Agent dossiers are private aids. Do not republish them wholesale. For external use, strip named-reviewer framing and restate arguments in your own voice.
