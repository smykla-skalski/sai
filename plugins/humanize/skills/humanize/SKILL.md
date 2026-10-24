---
name: humanize
description: "Use this skill when the user hands you existing prose (pasted text or a file) and wants it to sound plainer and more like a person wrote it, because it reads as fluffy, stiff, corporate, buzzword-heavy (\"enhance\", \"robust\", \"seamless\", \"leverage\", \"pivotal milestone\"), over-hyped, robotic, or ChatGPT-like. This covers any medium: commit messages, PR descriptions, Slack posts, emails, announcements, docs, changelogs, blog posts, and review comments. Also use it when the user wants to rate or score how AI-sounding a text is without editing it. The trigger is an existing draft that needs de-slopping, not the type of document. Don't use it to draft new content from scratch (such as writing release notes from commits), to make text more formal or polished, to summarize, shorten, or simplify for clarity alone, to edit code or identifiers, to beat AI detectors, or to judge whether someone used AI."
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. No scripts or network access needed.
argument-hint: "[file-path | text] [--score-only] [--dry-run]"
allowed-tools: AskUserQuestion Edit Read Write
user-invocable: true
metadata:
  short-description: Rewrite text to sound natural
---

# Humanize

Remove AI writing patterns from prose and rewrite it for its reader: answer first, use concrete words, include only useful context, match the audience, stop. Detection follows Wikipedia's "Signs of AI writing" and common agent habits. The rewrite follows Strunk and the Google and Microsoft style guides.

Use it for commit messages, PR descriptions, docs, changelogs, blog posts and review comments. Not for code, structured data (JSON/YAML), translation, edits where the wording must stay nearly exact, or text where AI patterns are intentional. Not for beating AI detectors or hiding AI use that a policy requires you to disclose: the patterns are editing smells, not proof of who wrote the text.

Run every phase yourself, in this conversation. Do not hand any phase to a subagent: Phase 5 checks against the same catalog and hit list, and only the main conversation can ask the user for a missing target.

## Agent compatibility

Paths are relative to this skill's directory. Outside Claude Code, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| AskUserQuestion | Ask in plain text and wait for the answer |
| Edit and Write | Use the agent's own file-edit tool (`apply_patch` in Codex). If the Codex sandbox blocks the write, request escalation with a short reason |

## Arguments

Invocation arguments: `$ARGUMENTS`

If that line is empty or still shows the literal placeholder, the client passed none: take the file path, text and flags from the user's request.

| Flag | Default | Purpose |
| :-- | :-- | :-- |
| (positional) | - | File path or raw text to humanize. Ask for it if omitted |
| `--score-only` | off | Report detected patterns without rewriting |
| `--dry-run` | off | Print the rewrite to chat instead of editing the file |

By default the skill edits the file in place.

## Workflow

### Phase 1: Input

1. Parse the target and flags from [Arguments](#arguments).
2. If there is no file path or text, use AskUserQuestion to get it.
3. Read the target file, or keep raw text as given. If the path is missing or unreadable, report the error and stop.
4. Warn if the text is under 50 characters: detection needs more content.
5. Note the medium and the audience.

### Phase 2: Pattern scan

Read [references/patterns.md](references/patterns.md) in full. Check the text against all 30 patterns, one at a time, and skip none. A listed word or mark is a hit only when it harms the text in context.

Record each match in a hit list: pattern number and name, the quoted offending text, and severity (faint, clear or glaring). Phases 4 to 6 work from this list.

- No hits: tell the user in one sentence that the text needs no changes, then stop. Do not list what you checked.
- `--score-only`: go to Phase 6.

### Phase 3: Voice assessment

Read [references/voice-guide.md](references/voice-guide.md) in full. Note what is the author's own and must stay (contractions, first person, opinions, team phrasing) and the shape the medium expects. Mark flat sections: uniform sentences or bullets, one corporate register, stiff phrasing, useful facts buried late.

### Phase 4: Rewrite

Read [references/elements-of-style.md](references/elements-of-style.md) in full. This phase needs ultrathink: weigh pattern removal, voice, composition and meaning before you rewrite each section.

Fix every hit, faint ones included, in this order:

1. Strip communication artifacts: chatbot phrases, disclaimers, sycophantic openings.
2. Fix structure: put the point in the first sentence, cut what nobody asked for, drop generic headings and automatic pros and cons.
3. Fix content patterns: deflate significance claims, replace vague attributions with specifics, keep a confident claim only with the source's evidence.
4. Fix language patterns: replace vague AI vocabulary, restore simple copulas (is/are/has), remove negative parallelisms, forced triads and needless connectors.
5. Fix style patterns: em dash overuse, mechanical boldface and emoji, title case headings, curly quotes in plain text.
6. Cut filler: remove filler phrases, reduce hedging, cut generic conclusions and recaps.
7. Restore voice where Phase 3 marked it: the medium's register and shape, rhythm that follows the meaning. Keep the author's contractions, first person and opinions, and add none of your own.
8. Apply the composition principles: active voice where the actor is known, positive form, concrete and plain words, one main idea per sentence, no needless words, emphasis at the end of the sentence, one topic per paragraph.

Keep the original meaning. Never add facts the source does not contain: invented facts undermine trust even when the prose reads better. Never add typos, broken grammar, feelings or tangents to seem human. Keep technical accuracy and the audience's jargon intact, because a style fix that breaks correctness makes the text worse.

### Phase 5: Verification

Re-read the hit list, then check the rewrite:

- No pattern from the catalog remains.
- The first sentence gives the point, and every sentence adds information.
- No information is lost or invented, and nothing was added to seem human.
- The author's voice survives, and the tone fits the medium and audience.
- Every composition principle from Phase 4 step 8 holds.
- The text sounds natural read aloud.

Revise and recheck each failing section.

### Phase 6: Report

Build the pattern report as a table with the columns #, Pattern (catalog names), Instance (only the quoted original text, no notes, even for structure patterns) and Fix (what replaced it, or "removed"). Give each quoted phrase one row naming every pattern it shows, and never quote text that sits inside another row's quote.

Under the table, write exactly one summary line, such as `14 patterns in 5 categories. Severity: Heavy.` (Minor, Moderate or Heavy). Under it, write `Cut for lack of evidence:` and list each claim you cut or hedged, one line each with just the quoted claim. The author's own numbers and facts are evidence, not claims to flag. With `--score-only`, leave out the Fix column and the claims list, print the report and stop.

Never call the text AI-written, and add no authorship disclaimer either: people write these patterns too, and false accusations do real harm. Your reply is the output, then the report, and nothing else: no commentary, notes, advice, follow-up offers or alternatives.

### Phase 7: Output

1. With `--dry-run`, or when the input was raw text, print the rewritten text to chat.
2. Otherwise edit the file in place: targeted edits (Edit) for local fixes, a full rewrite (Write) when most of the content changed.
3. Print the pattern report next, also after an in-place edit, not a change summary.
