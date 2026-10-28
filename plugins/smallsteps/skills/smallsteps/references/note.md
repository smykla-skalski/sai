# Idea note

Each idea has one Markdown note. The note is the record: every answer goes into it at once, and the next session starts from it.

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

To list the notes, for example to resume with no note named, run `notes.py list` the same way. It prints each note's name, step and next action.

The file name is a short kebab-case name from the idea, such as `link-finder.md`. If that file exists and is another idea, ask whether to resume it or to use a new name.

## Marks

| Mark | Meaning |
| :-- | :-- |
| `(suggested)` | Taken from the user's context, not confirmed yet |
| no mark | Confirmed by the user |
| `unknown` | The user does not know. Do not ask again |
| `unclear` | Still vague after one follow-up. Ask about it in the step playback |

A step is done only when it has no `(suggested)` or `unclear` mark left.

## Template

Keep the headings and field names exactly as below. Leave out a field only when the template says it is optional. On a Small idea, step 2 holds only the `Riskiest guess:` line, without the claims table. Write "unknown" only when the user says they do not know. Leave a field empty until you ask about it or draft it.

````markdown
# <idea title>

Step <n> of 4 | Next action: <first action or next question> | Updated: <YYYY-MM-DD>

## 1. What I want to change

Raw idea: <the user's words, unchanged>
Problem: <what happens today>
Who has it: <who exactly>
Better when: <the change, and how the user will see it>
Limits: <what must hold, or "none">
Options:
1. <the idea>
2. The way I work now: <how>
3. Do nothing or wait: <what happens then>

## 2. What must be true

| Claim | Fact, guess or unknown | Source or test | Matters | Evidence |
| :-- | :-- | :-- | :-- | :-- |
| <claim> | <label> | <source, or how to check it> | <a lot or a little> | <none, weak or strong> |

Riskiest guess: <the guess that matters most and has the least evidence>

## 3. What I can do now

Appetite: <how much time the idea is worth before deciding again, in the user's words>
Size: <small, medium or large>, because <reason>

| Result | Needs first | Place |
| :-- | :-- | :-- |
| <result> | <what it needs first, as the user said it, or "nothing"> | Now, Next or Later |

### Action card

Result I want: <the Now result>
What I need: <tools, people, files, or "nothing">
Done when: <what the user will see>
First action: <one physical step under 10 minutes>
When I start: When <time or place>, I will <first action>.

### Test

Add this block when the Now result checks a guess first. Leave it out otherwise.

Guess: <the guess>
Time box: <how long the test may take, set by the user>
If right, I expect: <result>
If wrong, I expect: <result>
Then: if right, <decision>. If wrong, <decision>. (On a Small idea, leave out "if right" when the user did not give it.)

## 4. What I learned

| Date | What I did | What happened | Done | As expected | Decision |
| :-- | :-- | :-- | :-- | :-- | :-- |

## Open questions

- <question, and which item it blocks>

## Map

<Mermaid blocks>

Miro board: <URL from a tool result, or "none">
````

The status line always shows the next thing to do: the next question during the interview, the first action after it. Update the date on every save.

## Resume

1. Read the whole note.
2. Show the next action from the status line.
3. If the note has `(suggested)` or `unclear` items, confirm them first.
4. If the Now result has an action or a test, run step 4: ask "Done, not done, or stuck?".
5. Never ask about a confirmed item again. Change an earlier section only when the user corrects it, and say which line changed.
