# Codex vs Claude Differences

Use this note when a target skill looks like a direct Claude port.

## What transfers

- narrow scope
- strong descriptions
- progressive disclosure
- bundled scripts for brittle workflows
- examples for judgment-heavy tasks
- explicit verification loops

## What changes in Codex

| Area | Claude-oriented pattern | Codex-oriented pattern |
| :-- | :-- | :-- |
| Inputs | `$ARGUMENTS` parsing | infer target from natural language and local context |
| Frontmatter | large control surface | minimal `name` and `description`, optional lightweight `metadata:` |
| Tool control | `allowed-tools` and hook contracts | approval, escalation, sandbox, and shell behavior |
| Metadata | frontmatter-heavy | `agents/openai.yaml` for UI and invocation policy |
| Helper agents | Claude-specific `context: fork` guidance | explicit helper-agent boundaries in prose |
| Discovery path | `claude/.../skills/...` | repo source `codex/...` plus runtime install surface such as `.agents/skills` or user/global directories |

## Do not import these Claude-only checks

- `allowed-tools`
- `argument-hint`
- `user-invocable`
- `disable-model-invocation`
- `$ARGUMENTS`
- hooks
- `context: fork`
- `agent:` skill frontmatter

## Codex-first review questions

Ask these instead:

- Is the routing description strong enough for natural-language invocation?
- Does the skill mention approval or escalation when commands can mutate state?
- Does `agents/openai.yaml` match the real workflow?
- Does the skill avoid startup-time enumeration and other first-turn tax?
- Is the install surface explicit when the path contract matters?
