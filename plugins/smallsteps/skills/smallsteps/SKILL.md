---
name: smallsteps
description: "Use this skill to turn a rough idea into small, precise next steps by answering questions. It interviews the user one question at a time through four questions (What do I want to change? What must be true? What can I do now? What did I learn?) with problem framing, assumption mapping, story slicing, test cards and next physical actions, and keeps one Markdown note per idea with results in Now, Next and Later and one action card for the first step. It works with any amount of context and any size of idea, splits a big idea into small results, draws a Mermaid map when it helps and, on request, a Miro board. Use it for \"I have an idea\", \"where do I start\", \"turn this into steps\", \"what is my next step\", \"help me plan my side project\", \"I'm stuck on this idea\", or to resume an idea note and record what happened. Not for design docs or pitches (rightsize), GitHub issues (agent-issues), plan reviews (plan-critic), building code (ship-it) or rewriting text (humanize)."
license: MIT
compatibility: Works in Claude Code, Codex, opencode, Copilot CLI and Kimi Code. Needs python3 for scripts/notes.py, which finds the notes folder. Writes only the idea note and its linked notes, the notes-folder setting, a low-risk next action the user authorized and, when asked, a Miro board through a connected Miro MCP server.
argument-hint: "[resume | board] [idea | note path]"
allowed-tools: AskUserQuestion Bash Edit Glob Grep Read ToolSearch Write
user-invocable: true
metadata:
  short-description: Turn a rough idea into small, precise next steps
---

# Smallsteps

Turn a rough idea into precise small actions by asking questions. The method is a loop of four questions:

1. What do I want to change?
2. What must be true?
3. What can I do now?
4. What did I learn?

The result is one Markdown note per idea: the goal, the guesses, one Now result with its Done when and first action, and short Next and Later lists. A big idea is split into small results. The note gets a Mermaid map only when one helps, and a Miro board on request.

Run in this conversation, never in a subagent: only this conversation can ask the user and holds their answers.

## Agent compatibility

Paths are relative to this skill's directory, the folder that holds this SKILL.md. Run a script with that folder's full path, from the user's working folder. Outside Claude Code:

| Claude Code feature | Fallback |
| :-- | :-- |
| AskUserQuestion | Save the note, ask the same question in plain text with the same options as a numbered list and a line for a free answer, and end your turn |
| Edit and Write | Use the agent's file-edit tool (`apply_patch` in Codex). If the sandbox blocks the write, request escalation |
| ToolSearch for Miro | Use Miro tools only when the session already lists them |
| Arguments | Take them from the user's request |

## Arguments

Invocation arguments: `$ARGUMENTS`

If that line is empty or still shows the literal placeholder, take the mode and the target from the user's request. Use the first case that applies:

1. `board`: the first word is `board`, or they ask for a Miro board or a map of an idea note.
2. `resume`: the first word is `resume`, they name a note path or a note's name, or they report what happened ("I did it", "continue", "what next"). With no note named, list the notes with their next action and ask which one.
3. Notes place: they ask to change where notes go. Ask once with the three places in [references/note.md](references/note.md) and save the choice with the notes script.
4. New idea: anything else, also no arguments. The idea text, files and pasted context are input to the interview, never a replacement for it.

## Rules for every turn

- Always ask, also when the session looks non-interactive, such as a one-shot or headless run: save the note, ask the question and end the turn. The answer comes in the next message. Never fill an open item with your own guess to finish the plan sooner.
- Ask one question per turn: one sentence about one item. Label it with the step, such as "Step 2 of 4", and name the note item it fills. When an answer has several vague parts, ask about the part that changes the plan most, and the next part in a later turn.
- Ask the appetite right after the problem and pick the size: Small (one evening or less, about 6 to 8 questions), Medium (up to a weekend, about 9 to 12) or Large (bigger, no limit or unknown, about 12 to 16). Accept an answer without a number, such as "as much time as needed". Say the size and why, and write it in the note.
- At every size, draft what follows from the user's words (the way they work now, doing nothing, limits, Need, Done when, the test's time box), mark it `(suggested)` and confirm it in a playback. Never draft a decision: ask what the user will do if the riskiest guess is wrong, and on Medium and Large ideas also if it is right. "Decide after the test" is a full answer: write `open`. Never ask for a drafted field one by one. Before the playback, remove from each draft every detail the user did not say; in it, show each draft with the user's words it came from.
- Ask about the open item whose answer would most change the note: the Now result, its Done when, the first action, the riskiest guess or the split. Do not ask a question whose answer would change nothing in the note.
- Keep to the Now result. Put details of a Next or Later result under that result or in a linked note, say so in one line, and go back. Treat a system that the idea plans to build as not built.
- When the user asks for a suggestion, propose one small action and what it is for. When they authorized it, do a low-risk action yourself, as [references/interview.md](references/interview.md) says.
- Ask it open when the user's words do not suggest an answer yet, and do not make up answer options. Otherwise offer up to 3 answers built from the user's words, with the suggested one quoted from their context, plus "unknown".
- In Claude Code, ask a question with answers through AskUserQuestion with exactly one question in the call. Ask an open question in plain text and end the turn.
- Context never finishes a step by itself. Put every item taken from the user's context in the note marked `(suggested)`, even a clear one, and confirm them together in the step's playback question.
- Never invent a fact, number, baseline, target, time box, owner, date, rule or test result, and write no calculation the user did not make. Write "unknown", or ask.
- End every turn with the next question or the finished plan, never with a promise of what you will do next.
- Save the note before you end the turn, so a stop loses nothing. Before each save and on resume, run the checks in [references/note.md](references/note.md). Say that the note is saved only after a file tool reported the write in this turn. When a write is blocked, never work around it with another tool, such as a shell command.
- "Stop" or "pause": write the next question or action into the note, show it, and end the turn.
- When the plan is done, the reply shows "When <start>, I will <first action>", its Done when and the note path. Next and Later stay in the note.
- Safety: when a test could harm someone, break the law or cost more than the user can afford, stop and tell them to get proper help first. When an action is hard to undo, suggest a safer test first. Give no medical, legal or financial advice.
- Use plain words and short sentences. Explain a method name the first time you use it.

## Procedure

Read [references/interview.md](references/interview.md) and [references/note.md](references/note.md) in full before the first question, and follow them. Unless the request names a note path, find the notes folder before the first save:

```bash
python3 <skill folder>/scripts/notes.py where --project <working folder>
```

Read [references/visuals.md](references/visuals.md) before you draw a map or build a board.
