---
name: humanize
description: Rewrite text to remove common AI-writing patterns and produce more natural prose. Use when the user wants writing to sound less formulaic or less obviously AI-generated.
metadata:
  short-description: Rewrite text to sound natural
---

# Humanize

Use this skill when the user wants a draft rewritten to sound more natural, less formulaic, and less obviously AI-generated.

This is a Codex-oriented port of the Claude skill at `claude/humanize/skills/humanize`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a draft rewritten to sound more natural, less formulaic, and less obviously AI-generated.

## Do Not Use This Skill

- Do not use this skill for factual editing where the user wants wording preserved exactly or for translation tasks.

## Workflow

1. Read the target text first and decide whether the user wants scoring only, a rewrite, or both.
2. Read `references/patterns.md` to detect common AI-writing artifacts, `references/elements-of-style.md` for rewriting principles, and `references/voice-guide.md` to maintain a direct, varied voice.
3. Preserve the original meaning, factual claims, and structure unless the user asked for deeper rewriting.
4. Call out repetitive phrasing, inflated claims, filler transitions, and unnatural emphasis before or alongside the rewrite when that helps the user learn the pattern.
5. If rewriting, provide text that is ready to use, not a commentary-heavy essay.

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

- Avoid replacing one formula with another. Vary rhythm and keep the prose specific.
- Do not introduce new claims while rewriting.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Rewrite this post so it sounds less AI-generated."
Assistant: Identifies the main patterns, then rewrites the text in a more natural voice.
</example>

<example>
User: "Score this draft for AI-writing patterns only."
Assistant: Reports the patterns found without rewriting the text.
</example>
