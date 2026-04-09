---
name: ai-daily-digest
description: Produce a daily AI news digest that highlights technical advances, business developments, and engineering impact. Use when the user wants a curated AI briefing or a reusable digest format.
metadata:
  short-description: Assemble a daily AI news digest
---

# AI Daily Digest

Use this skill when the user wants a current AI news digest, a themed roundup, or a reusable briefing structure.

This is a Codex-oriented port of the Claude skill at `claude/ai-daily-digest/skills/ai-daily-digest`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a current AI news digest, a themed roundup, or a reusable briefing structure.

## Do Not Use This Skill

- Do not use this skill for timeless AI explanations or historical summaries that do not need current-source verification.

## Workflow

1. Confirm the requested time horizon, focus area, and output destination. If the request is ambiguous, ask one focused follow-up.
2. Because this skill depends on current events, browse for up-to-date primary sources before drafting. Prefer direct source links and concrete dates.
3. Read `references/sources.md` before collecting links, `references/search-patterns.md` while gathering coverage, and `references/output-template.md` before drafting the final digest.
4. Cover the most important developments first, then explain why each item matters for engineers, operators, or leadership.
5. Treat publishing into Notion or another sink as a separate step after the digest content is correct.

## Bundled Resources

- `agents/openai.yaml`
- `references/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Separate reporting from opinion. Clearly label any inference or synthesis.
- Call out source freshness explicitly when the user asks for "today" or "latest".

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Summarize the most important AI news from this week for engineering leaders."
Assistant: Browses for current sources, drafts a dated digest, and separates factual reporting from inference.
</example>

<example>
User: "Give me a technical-only AI digest for today with direct source links."
Assistant: Verifies same-day sources, filters to technical updates, and returns a concise digest with links.
</example>
