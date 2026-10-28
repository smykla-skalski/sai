# smallsteps

Turns a rough idea into small, precise next steps by asking questions. It walks you through four questions, one question at a time:

1. What do I want to change?
2. What must be true?
3. What can I do now?
4. What did I learn?

The result is one Markdown note per idea. Its top shows the shape of the idea: your goal and the idea's parts, under headings that fit it, such as a contents list, a working example or conventions. Its bottom holds the process: one Now result with its Done when, your guesses, checks, questions and the next action. A big idea is split into small results that you can finish and review on their own. The note gets a Mermaid map only when one helps, and on request the skill also builds a Miro board.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI, opencode and Kimi Code.

The method comes from research on turning vague ideas into defined action, and on working with ADHD. Its sources include problem framing from the UK service manual, Theory of Change, assumption mapping, hypothesis-driven development, story slicing, the Getting Things Done next action, and implementation intentions (Gollwitzer and Sheeran, 2006).

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

Paste as much context as you have, or none. Context becomes suggested answers in the note, and the skill still confirms them with you.

## How it asks

Each turn has one question, labeled with the step and the note item it fills. The skill asks about the item whose answer would change the plan most, such as the first result, its Done when or the riskiest guess. It asks no question whose answer would change nothing. When your context suggests an answer, the question offers up to 3 answers built from your words, with the suggested one quoted, plus "unknown".

It picks a technique for each situation:

| Situation | Technique |
| :-- | :-- |
| The idea is a solution | Ask what problem it solves, and for whom |
| An answer has vague words | Ask who exactly, how much, by when, and how you will see it |
| No evidence for the problem | Ask for the last time it happened, or plan a small test |
| Many guesses | Assumption map: how much each guess matters, and how much evidence it has |
| The idea is large | Split it into thin results, and ask which one you need first |
| A guess must be checked | Test card: what you expect if it is right or wrong, and what you will do after each |
| No first step | The next physical action, under 10 minutes, with a when-and-where plan |

Right after the problem, the skill asks how much time the idea is worth to you, and sizes the interview by your answer:

| Size | When | Questions before the first action |
| :-- | :-- | :-- |
| Small | one evening or less, one result | about 6 to 8 |
| Medium | up to about a weekend | about 9 to 12 |
| Large | bigger, several people, or you do not know yet | about 12 to 16 |

An answer without a number, such as "as much time as needed", is a full answer: the idea is then large, and the skill does not ask for hours.

At every size, the skill drafts what follows from your own words (the way you work now, doing nothing, limits, Done when, the test of your riskiest guess) instead of asking for each field. It never drafts a decision: it asks what you will do if your riskiest guess is wrong, and for a medium or large idea also if it is right. "Decide after the test" is a full answer, recorded as `open`. When you ask for a suggestion, the skill proposes one small next action and says what it is for, and it does a low-risk action itself only when you allow it. It marks drafts `(suggested)` and shows them in a playback, apart from your own answers and each with the words it came from, so you can spot a detail you never gave before you say "Is this right?". Small ideas get one playback at the end, medium ideas two, large ideas one per step. The skill stops asking when the problem, the wanted change and the first step are clear, or you marked them "unknown", and no other answer would change them. It never fills a gap with an invented number or fact.

The first version of this question system came from a comparison with Jev, the TypeSafe decision model on OpenRouter. Jev scored short descriptions of five question policies, four full systems and three question formats. Its scores were close (most between 0.5 and 0.73), so they are only a first signal. The evals in `evals/` check the real behavior: one-turn cases, and whole simulated interviews (`evals/interviews.json`, run with `scripts/eval_interview.py`) that count the questions for each size.

## The note

Notes go to `${XDG_DATA_HOME:-~/.local/share}/sai/smallsteps/ideas/` by default. To keep them in the current repository (`ideas/` at the top of the git repository) or in a folder of your own, such as an Obsidian vault folder, ask the skill to change where notes go. It saves the choice as one line in `${XDG_DATA_HOME:-~/.local/share}/sai/smallsteps/notes-dir`. A note path in the request always wins.

In Codex's default sandbox, the shared folder is outside the workspace, so Codex asks for approval before it writes the note there. To avoid that, keep the notes in the repository.

The note keeps the step and the date in front matter (`step: 3 of 4`, `updated: 2026-10-28`). The rest has two parts.

The top is the idea itself: `## Goal` in a sentence or two, `## Idea` with your raw idea and its current form, and one section for each part of the idea, with a heading that fits it, such as "Contract contents", "Working example" or "Format conventions". When an answer or a check changes the idea, the skill changes these sections in place. They never hold questions, statuses or tests.

The bottom, `## Process`, holds the work:

| Field | What it holds |
| :-- | :-- |
| Now, Done when, Need | The current result, what you will see when it is done, and what you need |
| Main uncertainty, Guesses, Test | What you are least sure about, the other guesses with their evidence, and the test of the riskiest guess |
| Checks | One line per check: planned, done, not done or stuck, what it showed and what it did not prove |
| Questions | Open questions, one line each, with the item each blocks |
| Next results, Later | One line per result |
| Next action | "When <time or place>, I will <step>", or the next question while the interview runs |
| Background | Problem, appetite, size, limits and the other options |
| Links | Linked notes and the Miro board |

Each fact is written once. You can rename, move or delete sections: the skill keeps your layout and never puts back what you removed. A check that did not run stays in the note as not done.

When you come back, the skill shows the Now result, the next action and any question that blocks it, and asks "Done, not done, or stuck?". When the Now result is finished, it offers the Next results so you can pick the next one.

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
