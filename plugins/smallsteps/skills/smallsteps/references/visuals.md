# Visuals

The note always holds Mermaid maps. A Miro board is extra, made only when the user asks for it and Miro tools are connected. The note stays the record: a board whose decisions are not also in the note is soon forgotten.

## Mermaid maps

Put the maps under `## Map` in the note. Redraw a map when its step changes. Use only names and values that are in the note.

Assumption map, after step 2, whenever the note's claims table has ratings. Without ratings, as on a Small idea, draw only the plan map. The x axis is evidence and the y axis is how much the guess matters, from 0 to 1. Use none = 0.1, weak = 0.5, strong = 0.9, a little = 0.25 and a lot = 0.75, When several guesses share both labels, add 0.05 to x for the second, 0.10 for the third, and so on. The top-left area holds the guesses to test first.

```mermaid
quadrantChart
    title What must be true
    x-axis Little evidence --> Strong evidence
    y-axis Matters a little --> Matters a lot
    quadrant-1 Safe to build on
    quadrant-2 Test first
    quadrant-3 Watch
    quadrant-4 Ignore for now
    App search finds links: [0.12, 0.78]
    I save links daily: [0.55, 0.72]
```

Plan map, after step 3. One box per result, grouped by place. Draw an arrow only where the note says that a result needs another result first:

```mermaid
flowchart LR
    subgraph Now
        A["Save one link with a description"]
    end
    subgraph Next
        B["Find a link by a word I remember"]
    end
    subgraph Later
        C["Save links automatically"]
    end
    A --> B --> C
```

Rules:

- Put labels in double quotes and keep them short. Do not use `"` inside a label.
- Do not use `kanban`: GitHub may not render it.

## Miro board

Make one board per idea, only when the user asks ("put it on Miro", "make a board").

1. Find the Miro tools. In Claude Code, search the deferred tools with ToolSearch (query `miro`). In other agents, use them only when the session already lists them.
2. If there are no Miro tools, say so in one line, give the setup line for the agent (below), and keep the Mermaid maps. Never claim a board without a URL from a tool result.
3. Do not count on fixed tool names. Miro removed its older diagram and layout tools in September 2026. Look for a tool that creates a board, and tools that create, read and update board content.
4. If the server has a format or guide tool (today `canvas_get_canvas_composer_skill`), call it first and follow it. Today board content is sent as SVG, with Mermaid inside for flowcharts.
5. Build two frames:
   - "What must be true": a 2x2 with one sticky note per guess, placed as in the assumption map;
   - "Plan": the plan map, with Now, Next and Later as columns and arrows for what each result needs first.
6. Write the board URL in the note, next to `Miro board:`.
7. For a later board request on the same idea, read the board first, then send the redrawn frames as an update. Changes made on the board come into the note only through the interview.

Each board takes about 3 Miro calls. The Miro Free plan allows 100 calls a day.

## Miro setup lines

Show only the line for the current agent:

| Agent | Setup |
| :-- | :-- |
| Claude Code | Turn on the Miro connector in claude.ai, or run `claude mcp add --transport http miro https://mcp.miro.com/` and sign in with `/mcp` |
| Codex | `codex mcp add miro --url https://mcp.miro.com/`, then `codex mcp login miro` |
| Copilot CLI | `copilot mcp add --transport http miro https://mcp.miro.com/` |
| opencode | Add `"mcp": {"miro": {"type": "remote", "url": "https://mcp.miro.com/"}}` to `opencode.json`, then run `opencode mcp auth miro` |
