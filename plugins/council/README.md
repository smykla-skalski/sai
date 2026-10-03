# council

Run a council review through 27 sourced engineering and UX persona reviewers - antirez, tef, Casey Muratori, Fred Hebert, Donella Meadows, Cedric Chin, Alexis King, John Hughes, Eric Evans, Mark Seemann with Scott Wlaschin, Hillel Wayne, Kief Morris with Yevgeniy Brikman, Gary Bernhardt with Beck and Fowler, Brendan Gregg, Simon Willison, Charity Majors, Chris Eidhof with Florian Kugler, Mike Ash, Brent Simmons, Don Norman, Bruce Tognazzini, Steve Krug, Jakob Nielsen, Léonie Watson, Val Head, John Siracusa, and Edward Tufte. Each persona is built from the writer's primary public corpus, argues from their actual positions, and disagrees with the others where honest.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install council@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add council@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/council/` directly:

```bash
ln -s /path/to/sai/plugins/council/skills/council ~/.config/opencode/skills/council
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/council/` or `copilot --plugin-dir /path/to/sai/plugins/council`

## Modes

| Mode | Trigger | Personas |
|------|---------|----------|
| `core` | Default; no group keyword; auto-picks `core-eng`, `core-ux`, or `core-mix` from problem text | 6 |
| `auto` | Explicit best-fit mode; picks the best-fit personas from all 27 | 6 |
| `core-eng` (alias `eng`) | Code, architecture, refactor, perf, protocol, infra, ops | 6 engineering |
| `core-ux` (alias `ux`) | Interaction, layout, dashboard, a11y, usability | 6 UX |
| `core-mix` (alias `mix`, `random`) | Features that ship code and UI together | 3 eng + 3 UX |
| `all` | Substantial designs touching multiple domains | 27 deduped |
| `debate` | Hard tradeoff calls where disagreement is the point | 3-6 selected, three rounds |

## Usage

In Claude Code and Copilot CLI use `/council`, in Codex `$council`.

```text
/council                                            # Free-form question; defaults to core profile auto-detect
/council auto @docs/plans/refactor-auth.md          # Pick best-fit personas from file content
/council core @docs/plans/refactor-auth.md          # 6-person core profile selection
/council core-ux @apps/desktop-app/Sources/Sidebar.swift  # Pin UX lenses
/council mix @docs/plans/sessions-redesign.md       # Code + UI feature
/council all @docs/plans/llm-feature-rollout.md     # Full 27-persona coverage
/council debate Should we move sessions to Redis?   # Multi-round debate
```

`@<path>` reads the file as problem context. Bare arguments treat the whole string as the problem and default to `core` profile auto-detect.

## Reviewers per agent

| Agent | Reviewers | Runs above 6 reviewers |
| :-- | :-- | :-- |
| Claude Code | Named agents `council:<slug>` from `agents/`, spawned in parallel; each persona reads its dossier | Run directly |
| Copilot CLI | Same named agents `council:<slug>`, parallel background agents supervised about once a minute | Need AskUserQuestion approval in the current run |
| Codex | Generic `spawn_agent` reviewers at high reasoning effort, each given its mandate from `skills/council/references/agents/<slug>.md`; one at a time by default, parallel waves of at most 5 only on request | Need explicit same-turn approval |
| opencode | `task` subagents with the same mandates, one at a time | Need explicit approval in the request |

The old Codex agent definitions pinned a read-only sandbox; generic reviewers inherit the session sandbox, so the skill asks for read-only where `spawn_agent` allows it and the assignment forbids edits. Without approval, broad runs stop with exactly `Council not run: broad council approval not granted.` Without any subagent tool, the personas run inline and the synthesis says so.

## Output

The orchestrator returns one integrated review: convergence across opposed lenses, named disagreement where constraints decide the tradeoff, per-reviewer top-3 in each persona's own voice, concrete next moves smallest-first, and explicit gaps the council does not cover. Council is advisory: it answers in blocker language (`material blockers remain` / `no material blockers remain`), never as an approval gate.

## Files

- `agents/*.md` - Claude Code and Copilot CLI persona agent definitions. They keep the Claude tool list (`Read, Grep, Glob, WebFetch`) so Claude personas can read their dossiers; on Copilot that is wider than the old `Read`-only bundle, and the reviewer assignment still forbids search, web access and reads beyond named files. No `model:` pin, so agents use the session model
- `plugin.json` - root manifest for Codex and Copilot CLI, with the strict Codex UI prompts. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/council/SKILL.md` - the workflow, with per-agent sections for Claude Code, Copilot CLI, Codex and opencode
- `skills/council/references/agents/*.md` - each persona agent's body, used as the mandate where named agents do not exist. Agent bodies and these files must stay identical; `tests/test_council_persona_mandates.py` enforces it
- `skills/council/references/personas.md` and `*-deep.md` - persona registry and sourced dossiers
- `runbooks/codex-council-improvement-loop.md` (repo root) - the Codex live-validation loop

## Privacy

Persona dossiers under `skills/council/references/` are private review aids derived from each thinker's public writing. Do not republish wholesale. When a review leaves the team, strip persona framing and restate the argument in your own voice.

## License

MIT
