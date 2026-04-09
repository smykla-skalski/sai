---
name: slug
description: Generate a semantic branch-style slug for the current session. Use when the user wants a concise name for the work or a ready-to-use `/rename` command.
metadata:
  short-description: Generate a concise session slug
---

# Session Slug

Use this skill when the user wants a concise, branch-style name for the work completed in the conversation.

This is a Codex-oriented port of the Claude skill at `claude/slug/skills/slug`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a concise, branch-style name for the work completed in the conversation.

## Do Not Use This Skill

- Do not use this skill when the conversation had no meaningful work or when the user wants a product name rather than a session slug.

## Workflow

1. Review the full session context, not just the last message, and identify the dominant unit of work.
2. Choose the most fitting type prefix from `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, or `perf`.
3. Produce a short kebab-case slug with two to four words and avoid generic filler like `update` or `changes`.
4. If clipboard automation is useful and the user wants it, use a platform-appropriate copy command with escalation only if required. Otherwise return the rename command directly in chat.
5. Keep the final output concise and directly usable.

## Bundled Resources

- `agents/openai.yaml`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- If the session had no meaningful implementation work, say so instead of inventing a weak slug.
- If multiple unrelated topics exist, choose the dominant one and state the ambiguity briefly when needed.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Give me a good session name for this work."
Assistant: Reviews the conversation, picks a type and slug, and returns a ready-to-use rename command.
</example>

<example>
User: "What should I rename this session to?"
Assistant: Produces a concise branch-style slug based on the dominant work in the session.
</example>
