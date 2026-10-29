# smallsteps

Helps you explore and develop an idea, assess its value, and find small next steps when you want a plan. It asks one question at a time, offers critique and alternatives, and can research existing solutions and relevant terms. You can return to exploration at any point.

The skill keeps one concise Markdown note per idea. It records the current shape, decisions, checks, open questions and changes. When you want a plan, it uses four questions as a flexible loop: what to change, what must be true, what to do now and what was learned. It keeps one current result and one next action. Maps are optional, and a Miro board is available on request.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI, opencode and Kimi Code.

The skill selects methods for the problem and stage. It explains useful choices and can change or combine them as the work develops.

For examples of that approach, see the GOV.UK guidance on [understanding user needs](https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs) and [choosing research activities](https://www.gov.uk/service-manual/user-research/plan-user-research-for-your-service). These guides address public services, so their procedures may need adaptation for a small personal idea.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install smallsteps@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add smallsteps@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/smallsteps/` directly:

```bash
ln -s /path/to/sai/plugins/smallsteps/skills/smallsteps ~/.config/opencode/skills/smallsteps
```

Kimi Code loads the skill folder directly:

```bash
kimi --skills-dir /path/to/sai/plugins/smallsteps/skills
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/smallsteps/`

The skill needs `python3` for `scripts/notes.py`, which finds the notes folder.

## Usage

In Claude Code and Copilot CLI use `/smallsteps`, in Codex `$smallsteps`, or ask in plain words ("I have an idea for ...", "where do I start with this?", "what is my next step on the link app?"). The skill runs in the current conversation and starts no subagents.

```text
/smallsteps an app that finds my saved links by a word I remember
/smallsteps                          # start with a question about your idea
/smallsteps resume link-finder       # record what happened and pick the next step
/smallsteps board link-finder        # build or update the Miro board for the idea
```

Paste as much context as you have, or none. The skill records your answers and marks its own inferences as suggestions.

## How it helps

The skill starts with the problem, the people affected and the desired change. It uses a broader vision when you have one. It offers relevant questions, critique, alternatives and proportionate research, with sources and limits for factual claims. It treats value, novelty and feasibility as questions until evidence supports them.

You decide when to plan or run a check. The skill respects an open time budget and helps compare the next step with other options, including a pause or stop. It asks one clear question at a time and does not repeat an answer you already gave. In voice, it waits for you to finish a thought.

When you want a plan, the skill can split a large idea into independently useful results. It keeps one current result, an observable success condition and one next action. It records planned checks separately from completed checks, and preserves material decisions and results as the idea changes.

## The note

Notes go to `${XDG_DATA_HOME:-~/.local/share}/sai/smallsteps/ideas/` by default. To keep them in the current repository (`ideas/` at the top of the git repository) or in a folder of your own, such as an Obsidian vault folder, ask the skill to change where notes go. It saves the choice as one line in `${XDG_DATA_HOME:-~/.local/share}/sai/smallsteps/notes-dir`. A note path in the request always wins.

In Codex's default sandbox, the shared folder is outside the workspace, so Codex asks for approval before it writes the note there. To avoid that, keep the notes in the repository.

The note keeps the planning step and the date in front matter (`step: 3 of 4`, `updated: 2026-10-28`). The rest has two parts.

The top is the idea itself: `## Goal` in a sentence or two, `## Idea` with your raw idea and its current form, and one section for each part of the idea, with a heading that fits it, such as "Contract contents", "Working example" or "Format conventions". When an answer or a check changes the idea, the skill changes these sections in place. They never hold questions, statuses or tests.

The bottom, `## Process`, holds the work:

| Field | What it holds |
| :-- | :-- |
| Now, Done when, Need | The current result, what you will see when it is done, and what you need |
| Main uncertainty, Guesses, Test | What you are least sure about, the other guesses with their evidence, and the test of the riskiest guess |
| Checks | One line per check: proposed, planned, done, not done or stuck, what it showed and what it did not prove |
| Questions | Open questions, one line each, with the item each blocks |
| Next results, Later | One line per result |
| Next action | One concrete action or the next question, when known |
| Background | Problem, appetite, limits and the other options |
| Links | Linked notes and the Miro board |

Each fact is written once. You can rename, move or delete sections: the skill keeps your layout and never puts back what you removed. A check that did not run stays in the note as not done.

When you come back, the skill shows the current stage and the next action or question. It follows your direction, including a return to exploration, and keeps decisions open until you make them.

## Visuals

Maps are optional. The skill draws a Mermaid map, which renders on GitHub and in Obsidian, only when it shows something the text cannot show at a glance:

- an assumption map (a quadrant chart of how much each guess matters against how much evidence it has), when there are two or more rated assumptions;
- a plan map (Now, Next and Later, with what each result needs first), when a result needs another result first.

Ask for a map to get one anyway. A map that you removed stays out. Ask for a Miro board ("put it on Miro") to get the same two maps as frames on one board per idea. That needs the Miro MCP server:

| Agent | Setup |
| :-- | :-- |
| Claude Code | Turn on the Miro connector in claude.ai, or run `claude mcp add --transport http miro https://mcp.miro.com/` and sign in with `/mcp` |
| Codex | `codex mcp add miro --url https://mcp.miro.com/`, then `codex mcp login miro` |
| Copilot CLI | `copilot mcp add --transport http miro https://mcp.miro.com/` |
| opencode | Add `"mcp": {"miro": {"type": "remote", "url": "https://mcp.miro.com/"}}` to `opencode.json`, then run `opencode mcp auth miro` |

The note stays the record. Changes made on the board come back into the note only through the interview.

## After the plan

When it fits, the skill points to other SAI plugins: `agent-issues` to turn the Next results into issues, `rightsize` for a design doc or pitch, `plan-critic` to review a technical plan, and `ship-it` to build a step in a repository.
