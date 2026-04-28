# council

Run a council review through 27 sourced engineering and UX persona agents - antirez, tef, Casey Muratori, Fred Hebert, Donella Meadows, Cedric Chin, Alexis King, John Hughes, Eric Evans, Mark Seemann with Scott Wlaschin, Hillel Wayne, Kief Morris with Yevgeniy Brikman, Gary Bernhardt with Beck and Fowler, Brendan Gregg, Simon Willison, Charity Majors, Chris Eidhof with Florian Kugler, Mike Ash, Brent Simmons, Don Norman, Bruce Tognazzini, Steve Krug, Jakob Nielsen, Léonie Watson, Val Head, John Siracusa, and Edward Tufte. Each persona is built from the writer's primary public corpus, argues from their actual positions, and disagrees with the others where honest.

## Install

```bash
claude --plugin-dir ~/Projects/github.com/smykla-skalski/sai/claude/council/
```

## Modes

| Mode | Trigger | Personas |
|------|---------|----------|
| `core` | Default; no group keyword; auto-picks `core-eng`, `core-ux`, or `core-mix` from problem text | 6 |
| `auto` | Explicit best-fit mode; picks the best-fit personas from all 27 | 6 |
| `core-eng` (alias `eng`) | Code, architecture, refactor, perf, protocol, infra, ops | 6 engineering |
| `core-ux` (alias `ux`) | Interaction, layout, dashboard, a11y, usability | 6 UX |
| `core-mix` (alias `mix`, `random`) | Features that ship code and UI together | 3 eng + 3 UX |
| `all` | Substantial designs touching multiple domains | 27 deduped |
| `debate` | Hard tradeoff calls where disagreement is the point | 3-6 selected |

## Usage

```
/council                                            # Free-form question; defaults to core profile auto-detect
/council auto @docs/plans/refactor-auth.md          # Pick best-fit personas from file content
/council core @docs/plans/refactor-auth.md          # Use legacy 6-person core profile selection
/council core-ux @apps/desktop-app/Sources/Sidebar.swift  # Pin UX lenses
/council mix @docs/plans/sessions-redesign.md       # Code + UI feature
/council all @docs/plans/llm-feature-rollout.md     # Full 27-persona coverage
/council debate Should we move sessions to Redis?   # Multi-round debate
```

`@<path>` reads the file as problem context. Bare arguments treat the whole string as the problem and default to `core` profile auto-detect. Use `auto` explicitly for the 6-person best-fit roster.

## Output

The orchestrator returns one integrated review: convergence across opposed lenses, named disagreement where constraints decide the tradeoff, per-persona top-3 in each persona's own voice, concrete next moves smallest-first, and explicit gaps the council does not cover.

## Privacy

Persona dossiers under `skills/council/references/` are private review aids derived from each thinker's public writing. Do not republish wholesale. When a review leaves the team, strip persona framing and restate the argument in your own voice.

## License

MIT
