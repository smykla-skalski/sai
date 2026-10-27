# Reporting a defect in this skill

Every rule in this skill comes from a defect found in a real build, and the next one will come from yours. The installed skill is a copy that each plugin update replaces, so a fix written into it is lost. Report the fix as a GitHub issue for the repository the skill comes from, `smykla-skalski/sai`, written so that someone with no access to your session can implement it directly.

## When to write one

Write an issue when the cause is in the skill:

- A script in `scripts/` or `assets/explainer.py` fails, gives a wrong result, flags correct output, or misses a defect that you then found by hand.
- A step in SKILL.md is wrong, missing or in the wrong order, or you needed knowledge that is not in the skill: a Manim behavior, a missing glyph, a voice that misreads a word, an ElevenLabs quirk.
- You wrote a helper in video.py that a video on another topic would also need, or you typed the same manual command more than twice.

Leave out choices of taste, visuals for one topic, and one-off network or API failures.

## What to do in the session

1. Fix the project copy so the video ships, and note the change. new_project.py overwrites the shared files in the project, so the issue is the only lasting record.
2. If `gh` is available, look for an open issue first: `gh issue list --repo smykla-skalski/sai --search "explainer-video <keyword>"`. If one covers the defect, draft a comment with your new evidence instead.
3. Write the issue to `skill-issues/<short-slug>.md` in the project folder: the title on the first line as `# <title>`, then the body.
4. In the report, list each issue file with its title and the problem it fixes.
5. File it only when the user asks: `gh issue create --repo smykla-skalski/sai --title "<title>" --body-file <file without the title line>`.

## Title

`fix(explainer-video): <symptom>` for a defect, `feat(explainer-video): <capability>` for a missing helper or step. Imperative, lowercase after the colon, no trailing period, under 70 characters, one deliverable. Example: `fix(explainer-video): stop trim() cutting a leading short word`.

## Body

Use these sections and leave out any that would be empty. One physical line per paragraph and per bullet.

```markdown
## Problem

2-4 sentences: what went wrong, in which kind of video, what a viewer or the agent saw, and why it matters. No proposed fix here.

## Reproduction

The command, run from a project scaffolded with new_project.py, and the output you saw, quoted exactly. Name the input that triggers it (a script.py line, a scene).

## Expected behavior

- Observable result with its check, for example "given a clip that starts with 'So', `narration.py clips` prints OK".
- `scripts/selftest.py` ends with `selftest OK`, and it gains a step or a check that fails without the fix whenever the self-test does not cover the defect yet.

## Constraints

- Decided: <what you established, such as the cause you verified>.
- Your call: <choices the implementer may make>.
- Do not loosen a threshold in narration.py check: each one maps to a defect someone heard.
- Keep old projects working: new parameters get defaults, no helper that a video.py may use is renamed or removed, and any change that an old project needs is made by new_project.py on refresh and covered by the old-project step of `scripts/selftest.py`.
- Keep SKILL.md under 8,000 bytes: details go in references/.

## Starting points

- The files in the plugin, `plugins/explainer-video/skills/explainer-video/` in the repository: pipeline behavior in `scripts/`, shared look and helpers in `assets/explainer.py`, starting files in `assets/script.py` and `assets/video.py`, pitfalls (symptom, cause, fix) in `references/manim-pitfalls.md` or `references/audio-pitfalls.md`, process in `SKILL.md`, a new worked example in `references/examples/` with one line in `references/animation.md`.
- The function or step involved, by name, not line number.
- The patch you applied to the project copy, as a diff, labelled as the tested workaround.

## Stop and flag

- Stop and report if the fix needs a lower check threshold or breaks an existing video.py.
- No change needed if the defect no longer reproduces on the default branch.
```

## Rules for the text

- Every path, symbol and command in the issue was checked in this session; drop anything you did not verify, or label it a hypothesis with the check that would confirm it.
- Paths are relative to the project or the repository. Leave out home folders, temp folders, user names, API keys and other machine details.
- Quote error text and check output exactly.
