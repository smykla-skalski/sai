# Codex Skill Examples

Use these patterns when fixing weak Codex skills.

## Description

Good:

```yaml
description: Audit Codex skill bundles before publishing. Use when reviewing or fixing a Codex skill's SKILL.md, references, scripts, or agents/openai.yaml.
```

Bad:

```yaml
description: Helps review skills.
```

## Routing boundaries

Good:

```md
## Use this skill
- Audit a skill before publishing

## Do not use this skill
- Do not use it for generic PR review
```

Bad:

```md
This skill can help with many tasks and quality work in general.
```

## Approval and escalation language

Good:

```md
Before running a risky remote command, ask for approval or rerun with `sandbox_permissions=require_escalated` when sandbox restrictions are the blocker.
```

Bad:

```md
Run `gh pr merge` when the branch looks good.
```

## `agents/openai.yaml`

Good:

```yaml
interface:
  display_name: "Skill Review"
  short_description: "Audit Codex skills before publishing"
  default_prompt: "Use $review-skill to audit this Codex skill and explain the verdict."
```

Bad:

```yaml
interface:
  display_name: Skill Review
  short_description: "Review skills"
  default_prompt: "Audit this skill"
```

## Startup cost

Good:

```md
Resolve the target skill from the user request first. Do not enumerate every installed skill unless the user asked for discovery.
```

Bad:

```md
At startup, list every installed skill and scan the whole repo so you have full context before answering.
```
