---
name: kubecon-cfp
description: Draft and refine KubeCon CFP submissions using accepted-talk patterns, reviewer criteria, and reusable output templates. Use when the user wants to assess, draft, or improve a KubeCon proposal.
metadata:
  short-description: Draft and refine KubeCon CFPs
---

# KubeCon CFP

Use this skill when the user wants to assess, draft, or improve a KubeCon CFP proposal.

This is a Codex-oriented port of the Claude skill at `claude/kubecon-cfp/skills/kubecon-cfp`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants to assess, draft, or improve a KubeCon CFP proposal.

## Do Not Use This Skill

- Do not use this skill for generic blog writing or conference submissions that are not KubeCon-style CFP work.

## Workflow

1. Confirm the talk topic, target track, format, and whether the user wants ideation, drafting, or review of an existing proposal.
2. Read `references/cfp-criteria.md`, `references/talk-patterns.md`, and `references/output-template.md` before drafting or scoring. Use `evals/eval-cases.md` only when calibrating the approach.
3. Assess the idea first: novelty, audience relevance, practical payoff, and fit for the chosen format.
4. Write titles and abstracts that are concrete, teachable, and outcome-oriented rather than buzzword-heavy.
5. When reviewing an existing draft, score it against the copied criteria and explain the highest-leverage changes.

## Bundled Resources

- `agents/openai.yaml`
- `evals/`
- `references/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Keep claims believable and specific. CFP reviewers penalize vague hype.
- When the user gives weak topic detail, elicit missing specifics before producing a polished abstract.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Turn this service-mesh idea into a stronger KubeCon abstract."
Assistant: Assesses topic strength, uses the copied criteria and template, and drafts a tighter proposal.
</example>

<example>
User: "Review my CFP draft for the security track."
Assistant: Scores it against the criteria and suggests the highest-leverage changes.
</example>
