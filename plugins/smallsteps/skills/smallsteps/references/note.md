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

The note is about the idea, not about the interview. Its top shows the idea's current shape: `## Goal` when known, `## Idea`, and sections that fit the idea. Keep one editable working example when one exists. Everything about getting there sits at the bottom, under `## Process`: the current stage, decisions, checks, questions and next action when known. Exploration can have no plan or action card.

- Write what the user says about the idea itself into the shape sections at once. Keep them current: when an answer or a check changes the idea, change the shape in place, and record the check under `**Checks:**`.
- Add a heading for a part of the idea when the user describes one. Never put a question, a status, a test or a next action in a shape section.
- Write each fact once: a fact about the idea goes in the shape, a fact about the work goes in `## Process`.
- Record the current question once. When it is the next question, do not repeat it in both `**Questions:**` and `**Next question:**`; keep its blocker with the one entry.
- Preserve material earlier decisions, corrections, check results and what changed in brief dated or undated entries as appropriate. Record the iteration count only when known. Do not reconstruct missing history or add dates without a reason.
- When the user changes direction or authorizes a check after postponing checks, mark the earlier decision as history and record the current choice. Do not leave the old direction as the current decision.
- Separate sourced observations, assumptions, suggestions and confirmed decisions. Record the source and limits of research claims. Do not present a proposed check as completed evidence.
- When the proposed Now condition needs a system that does not exist, mark it proposed and blocked until the user chooses a feasible condition or a new order. Do not write it as a confirmed current Done when.
- The user may rename, reorder, add or remove headings and fields: keep their choice, find items by their meaning, never put back what they removed, and do not ask about headings. A note in an older layout keeps its layout.
- Put a long piece, such as research or a full example, in a linked note, and link it in one line under `### Links`. Put a new linked note in a folder named after the note, such as `link-finder/search-options.md`, unless the user keeps such notes elsewhere. Use the link style that the folder already uses, such as `[[Research/Search options|search options]]` in an Obsidian vault, and Markdown links otherwise.

## Marks

| Mark | Meaning |
| :-- | :-- |
| `(suggested)` | Your inference or proposal, not confirmed yet. Put it after the field name, as in `**Need (suggested):**`, or after a list item |
| no mark | Confirmed by the user |
| `unknown` | The user does not know. Revisit only when relevant new evidence or the user makes it useful |
| `open` | A decision the user has not made. Do not press for it |
| `unclear` | Still vague after a follow-up. Clarify when it matters to a decision |

Confirm material suggestions when they affect the next decision. An open or unclear item need not block exploration or a pause.

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

**Stage:** <exploring, planning, acting, learning, paused or stopped>

**Decisions:** <current decision and material earlier decisions or corrections>

**Now:** <the current result>

**Done when:** <what the user will see>

**Need:** <tools, people, files, or "nothing">

**Main uncertainty:** <the riskiest guess: it matters most and has the least evidence>

**Guesses:**

- <claim>: <guess, fact or unknown>. Evidence: <none, weak or strong>, <the source, or how to check it>

**Checks:**

- <check>: <proposed, planned, done, not done or stuck>. Showed: <what happened, if run>. Did not prove: <limit, if known>. Decision: <decision or "open">

**Questions:**

- <question, and which item it blocks>

**Next results:**

- <result, in the order the user named it>, needs <what it needs first, as the user said it>

**Later:**

- <result>

**Next action:** <one concrete action and a start cue when useful>

### Background

**Problem:** <what happens today, and who has it>

**Appetite:** <how much time the idea is worth before deciding again, in the user's words>

**Limits:** <what must hold, or "none named">

**Other options:** the way I work now: <how>. Do nothing or wait: <what happens then>.

### Links

- <a linked note, or "Miro board" with the URL from a tool result>
````

Use `step: 1 of 4` during exploration for compatibility with note listing; record the actual stage in `**Stage:**`. Update the step when planning advances or returns to an earlier question. While a conversation continues, record its next question or action when known. Leave out empty fields and `needs ...` when the user named no dependency. Add ratings only when useful and supported.

When the Now result checks a guess first, add the test after `**Main uncertainty:**`:

```markdown
**Test:**

- Guess: <the guess>
- Time box: <how long the test may take, set by the user>
- If right, I expect: <result>
- If wrong, I expect: <result>
- Then: if right, <decision or "open">. If wrong, <decision or "open">.
```

Leave out test fields that are unknown or not relevant. Add `### Map` before `### Links` only for the maps in [references/visuals.md](visuals.md).

Update `updated:` on every save. Use only the fields that fit the current stage and the user's layout.

## Checks and evidence

`**Checks:**` lists material checks and actions, one item each. A check is `proposed` until the user agrees to plan it; an agreed check is `planned`. A check the user says did not run is `not done`. Change status only on user or tool evidence. For a completed check, record what happened, whether it met any stated expectation, and what it did not prove when known. Label an inferred limit `(suggested)` and let the user correct it without a separate confirmation question. Do not turn silence into confirmation. Preserve previous results and decisions when a later check changes the idea. A proposed or planned check does not change the evidence for an assumption.

## Before each save

Check the note and this turn's question:

1. The question does not repeat a confirmed answer or press for an `unknown` or `open` item. Revisit one only when a relevant change or the user makes it useful.
2. Unaccepted checks are `proposed`, agreed checks are `planned`, and checks the user says did not run are `not done`.
3. The shape sections hold only the idea, with no question, status, test or next action, and each fact is written once.
4. Nothing that the user removed is back, such as a section, a field or a map.

Fix the note or the question before you save.

## Resume

1. Read the whole note, and a linked note only when the next action needs it.
2. Run the checks in "Before each save" on the note as you found it.
3. Show the current stage and the next action or question, plus any relevant blocker. Follow the user's request, including a return to exploration.
4. Confirm a suggested item only when it matters to the current decision. If the user reports a check, record its status and result before suggesting a next step.
5. Keep an `open` decision open until the user decides. Offer a choice of next results when appropriate, without assuming the user wants to continue.
6. Never ask about a confirmed item again without a relevant change. Preserve the earlier decision when a correction changes it.
