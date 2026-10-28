# Idea note

Each idea has one Markdown note. The note is the record: every answer goes into it at once, and the next session starts from it. Keep progress only in the note: never create a separate progress or status file, and never ask the user for one.

## Where notes live

A note path in the request wins. Use it as given.

Otherwise ask the notes script before the first save. It is `scripts/notes.py` in this skill's directory, the folder that holds SKILL.md. Run it with that folder's full path, and pass the user's project folder (your working folder) as `--project`:

```bash
python3 <skill folder>/scripts/notes.py where --project <working folder>
```

It prints one JSON object. `dir` is the folder for new notes. When `exists` is false, the folder is new: create it, and add one line to the reply that names the folder in full, such as `~/.local/share/sai/smallsteps/ideas/`, and says that the user can ask to change where notes go. When `status` is `error`, show the error and ask the user where notes should go.

When the sandbox blocks the write to `dir`, request permission to write there. If you cannot get it, do not save the note somewhere else on your own, and do not write it with another tool, such as a shell command. Make your next question, before any idea question, whether to keep the notes in this repository, because nothing is saved until the place works. On yes, save that choice with `notes.py set ideas` (below) and write the note there, so the setting and the notes stay in one place.

Never ask about the place before the first idea question.

To change the place, save it at once when the request already names it ("keep them in this repository", "put them in ~/vault/Ideas"). Otherwise ask once with three answers: "Shared folder (works from any repo)", "This repository (ideas/)" and "A folder you name, such as an Obsidian vault folder". Then save the choice:

```bash
python3 <skill folder>/scripts/notes.py set <shared | ideas | /absolute/folder> --project <working folder>
```

To list the notes, for example to resume with no note named, run `notes.py list` the same way. It prints each note's name, step and next action or question.

The file name is a short kebab-case name from the idea, such as `link-finder.md`. If that file exists and is another idea, ask whether to resume it or to use a new name.

## Shape first, process last

The note is about the idea, not about the interview. Its top shows the idea's current shape: `## Goal` in one or two sentences, `## Idea`, and a section for each part of the idea, with a heading that fits it, such as "Contract contents", "Working example", "Format conventions" or "Scope". These shape sections hold what the idea is made of: its parts, contents, rules, conventions, scope and a working example, in the user's words. Everything about getting there sits at the bottom, under `## Process`: the current result, the guesses, the test, the checks, the questions and the next action.

- Write what the user says about the idea itself into the shape sections at once. Keep them current: when an answer or a check changes the idea, change the shape in place, and record the check under `**Checks:**`.
- Add a heading for a part of the idea when the user describes one. Never put a question, a status, a test or a next action in a shape section.
- Write each fact once: a fact about the idea goes in the shape, a fact about the work goes in `## Process`.
- The user may rename, reorder, add or remove headings and fields: keep their choice, find items by their meaning, never put back what they removed, and do not ask about headings. A note in an older layout keeps its layout.
- Put a long piece, such as research or a full example, in a linked note, and link it in one line under `### Links`. Put a new linked note in a folder named after the note, such as `link-finder/search-options.md`, unless the user keeps such notes elsewhere. Use the link style that the folder already uses, such as `[[Research/Search options|search options]]` in an Obsidian vault, and Markdown links otherwise.

## Marks

| Mark | Meaning |
| :-- | :-- |
| `(suggested)` | Drafted from the user's context or by you, not confirmed yet. Put it after the field name, as in `**Need (suggested):**`, or after a list item |
| no mark | Confirmed by the user |
| `unknown` | The user does not know. Do not ask again |
| `open` | A decision the user will make when the result is in. Do not ask for it before |
| `unclear` | Still vague after one follow-up. Ask about it in the step playback |

A step is done only when it has no `(suggested)` or `unclear` mark left.

## Template

Use the headings and field names below for a new note. Keep a blank line between field lines, so that each renders as its own line. Add a field or section when its item is known, and leave out a field or section that has no content. Write "unknown" only when the user says they do not know.

````markdown
---
step: <n> of 4
updated: <YYYY-MM-DD>
---

## Goal

<what gets better, and how the user will see it>

## Idea

**Raw idea:** <the user's words, unchanged>

<the idea in its current form, in the user's words>

## <a part of the idea, such as "Contract contents">

<that part: a list, rules, a convention, the scope or a working example>

## Process

**Now:** <the current result>

**Done when:** <what the user will see>

**Need:** <tools, people, files, or "nothing">

**Main uncertainty:** <the riskiest guess: it matters most and has the least evidence>

**Guesses:**

- <claim>: <guess, fact or unknown>. Evidence: <none, weak or strong>, <the source, or how to check it>

**Checks:**

- <YYYY-MM-DD>, <check>: <planned, done, not done or stuck>. Showed: <what happened>. Did not prove: <the part of the guess it does not cover>. Decision: <decision or "open">

**Questions:**

- <question, and which item it blocks>

**Next results:**

- <result, in the order the user named it>, needs <what it needs first, as the user said it>

**Later:**

- <result>

**Next action:** When <time or place>, I will <one physical step under 10 minutes>.

### Background

**Problem:** <what happens today, and who has it>

**Appetite:** <how much time the idea is worth before deciding again, in the user's words>

**Size:** <small, medium or large>, because <reason>

**Limits:** <what must hold, or "none named">

**Other options:** the way I work now: <how>. Do nothing or wait: <what happens then>.

### Links

- <a linked note, or "Miro board" with the URL from a tool result>
````

While the interview runs, end the process block with `**Next question:** <the next question>`, after the next action when there is one. Leave out `needs ...` when the user named nothing that a result needs first. On a Small idea, leave out `**Guesses:**`. On a Large idea with several guesses, end each guess with `Matters: a lot` or `Matters: a little`.

When the Now result checks a guess first, add the test after `**Main uncertainty:**`:

```markdown
**Test:**

- Guess: <the guess>
- Time box: <how long the test may take, set by the user>
- If right, I expect: <result>
- If wrong, I expect: <result>
- Then: if right, <decision or "open">. If wrong, <decision or "open">.
```

On a Small idea, leave out "if right" in `Then:` when the user did not give it. Add `### Map` before `### Links` only for the maps in [references/visuals.md](visuals.md).

Update `updated:` on every save.

## Checks and evidence

`**Checks:**` lists every check and action, one item each. When the plan sets a test or another check, add its item with the status `planned`. Change the status only from what the user reports: `done`, `not done` or `stuck`. A check that did not run stays in the list as `not done`, with "Showed: not run" and no Did not prove. Never drop it, and never mark it done. In Showed, write what happened and whether it matched the expectation. Draft Did not prove from the guess and the result, such as "that the search finds links saved with other words", mark it `(suggested)`, and show it in the reply above the next question so the user can correct it. It needs no question of its own: when the user's next answer does not correct it, remove the mark. A guess's evidence changes only after a check is done, never after a planned one. When a check changes the idea, also update the shape.

## Before each save

Check the note and this turn's question:

1. The question asks for no item that is confirmed, `unknown` or `open`, or that the user already answered in any words, also without a number, such as "as much time as needed".
2. Every check that the user did not run is in `**Checks:**` as `not done`.
3. The shape sections hold only the idea, with no question, status, test or next action, and each fact is written once.
4. Nothing that the user removed is back, such as a section, a field or a map.

Fix the note or the question before you save.

## Resume

1. Read the whole note, and a linked note only when the next action needs it.
2. Run the checks in "Before each save" on the note as you found it.
3. Show the Now result, the next action or next question, and each question that blocks it.
4. If the note has `(suggested)` or `unclear` items, confirm them first. A Did not prove draft is the exception: show it with the next question, and remove the mark when the answer does not correct it.
5. If the Now result has an action or a test, run step 4: ask "Done, not done, or stuck?". When a decision is `open` and the result is in, ask for the decision before the next action.
6. Never ask about a confirmed item again. Change an earlier section only when the user corrects it, and say which line changed.
