# plan-critic

Critique an implementation plan **before** any code is written. Three persona reviewers (Skeptic, Architect, Verifier) evaluate the plan against the codebase and return an Approve/Refine/Reject verdict with concrete refinements.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **Triage** — fast scope check, trivial-change escape hatch, 7+ files scope warning
- **Grounding Brief** — one pass verifies every file/symbol the plan names against the actual codebase, lists callers, surfaces existing patterns
- **Three personas** — Verifier (did the author read the code?), Architect (is the structure sound?), Skeptic (what's missing?)
- **Three-Response Framework** — Approve / Refine / Reject verdict with refinement list or rejection rationale
- **Calibration guardrails** — don't reject for preference, don't refine into oblivion, trust the Grounding Brief over plan claims

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install plan-critic@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add plan-critic@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/plan-critic/` directly:

```bash
ln -s /path/to/sai/plugins/plan-critic/skills/plan-critic ~/.config/opencode/skills/plan-critic
```

Optional named opencode subagents: for each persona create `~/.config/opencode/agents/<persona>-reviewer.md` (`skeptic`, `architect`, `verifier`) with frontmatter `description` and `mode: subagent`, followed by the body of `skills/plan-critic/references/<persona>-reviewer.md`.

Local checkout: `claude --plugin-dir /path/to/sai/plugins/plan-critic/` (or `copilot --plugin-dir ...`)

## Usage

Triggers on: "critique this plan", "review this plan", "is this plan good", "poke holes in this plan", "should I approve this plan", or sharing a plan for evaluation.

In Claude Code and Copilot CLI use `/plan-critic`, in Codex `$plan-critic`:

```text
/plan-critic <plan file path>
/plan-critic <paste plan inline>
/plan-critic --from-conversation
```

## Personas per agent

| Agent | Grounding Brief | Personas |
| :-- | :-- | :-- |
| Claude Code | `Explore` subagent | Named agents `plan-critic:skeptic-reviewer`, `architect-reviewer`, `verifier-reviewer`, all three in parallel; `general-purpose` with the mandate prepended as fallback |
| Copilot CLI | Inline | Same named agents, delegated one at a time (parallel only on request) |
| Codex | Inline | Inline lenses by default; sequential `spawn_agent` calls on request, each closed after it returns |
| opencode | Inline | `task` tool, one persona at a time, with installed persona agents or the built-in `general` subagent |

Every agent falls back to adopting the personas inline when subagents are unavailable.

## Files

- `agents/{skeptic,architect,verifier}-reviewer.md` - Claude Code and Copilot CLI agent definitions. They inherit the session model
- `plugin.json` - root manifest for Codex and Copilot CLI. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/plan-critic/references/{skeptic,architect,verifier}-reviewer.md` - the same mandates for the generic-subagent and inline paths. Each agent body and its reference file must stay identical; `tests/test_plan_critic_personas.py` enforces it

## License

MIT
