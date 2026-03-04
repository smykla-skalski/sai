---
name: humanize
description: Identify and remove AI writing patterns to make text sound natural and human-written. Use when humanizing commit messages, PR descriptions, review comments, docs, changelogs, or release notes. Also for de-slopping text that sounds robotic, has AI vibes, or reads like ChatGPT output.
argument-hint: "[file-path] [--score-only] [--dry-run]"
allowed-tools: Read, Write, Edit, Grep, AskUserQuestion
user-invocable: true
---

# Humanize

Remove AI writing patterns from text and replace them with natural, human-sounding alternatives. Uses two complementary sources:

- **Detection**: Wikipedia's "Signs of AI writing" guide (WikiProject AI Cleanup) - what to remove
- **Composition**: Strunk & White's "The Elements of Style" (1918) - how to write the replacement well

## Arguments

Parse from `$ARGUMENTS`:

| Flag           | Default | Purpose                                         |
|:---------------|:--------|:------------------------------------------------|
| (positional)   | —       | File path to humanize. Prompt user if omitted   |
| `--score-only` | off     | Report detected patterns without rewriting      |
| `--dry-run`    | off     | Output to chat instead of editing in-place      |

Default: edit the file in-place, fixing all detected patterns regardless of severity (including faint ones). Use `--dry-run` to preview changes without modifying the file.

## Pattern categories

The skill detects 24 AI writing patterns organized into five categories:

1. Content patterns (1-6): significance inflation, notability claims, superficial -ing analyses, promotional language, vague attributions, formulaic challenges sections
2. Language and grammar (7-12): AI vocabulary words, copula avoidance, negative parallelisms, rule-of-three, synonym cycling, false ranges
3. Style (13-18): em dash overuse, boldface overuse, inline-header lists, title case headings, emoji decoration, curly quotes
4. Communication artifacts (19-21): chatbot correspondence phrases, knowledge-cutoff disclaimers, sycophantic tone
5. Filler and hedging (22-24): filler phrases, excessive hedging, generic positive conclusions

Full pattern descriptions with words-to-watch lists and before/after examples are in `references/patterns.md`.

Composition principles for the rewrite phase (active voice, concrete language, omitting needless words, sentence variety, emphasis placement) are in `references/elements-of-style.md`.

## Workflow

### Phase 1: Input discovery

1. Parse `$ARGUMENTS` for file path and flags.
2. If no file path provided, use AskUserQuestion to get the target file or text.
3. Read the target file. If the input is raw text (not a file path), store it for processing.
4. Determine the text's intended tone and audience from context (technical docs, blog post, PR description, commit message, etc.).

### Phase 2: Pattern scan

Read `references/patterns.md` in full before starting this phase.

1. Scan the text for each of the 24 AI writing patterns.
2. For each detected instance, record:
   - Pattern ID and name
   - The offending text (quote it)
   - Severity: how obvious the AI tell is (faint, clear, glaring)
3. If `--score-only`, skip to Phase 5 (Report).

### Phase 3: Voice assessment

Read `references/voice-guide.md` in full before starting this phase.

1. Assess the text for signs of soulless writing:
   - Uniform sentence length and structure
   - No opinions, perspective, or personality
   - No acknowledgment of uncertainty or mixed feelings
   - Reads like a press release or generic Wikipedia article
2. Note sections that need voice injection, not just pattern removal.

### Phase 4: Rewrite

Read `references/elements-of-style.md` in full before starting this phase.

Fix every detected pattern regardless of severity. Even faint tells get fixed. Apply fixes in this order:

1. Strip communication artifacts: chatbot phrases, disclaimers, sycophantic openings.
2. Fix content patterns: deflate significance claims, replace vague attributions with specifics, remove formulaic sections.
3. Fix language patterns: replace AI vocabulary, restore simple copulas (is/are/has), remove negative parallelisms and forced triads.
4. Fix style patterns: replace em dashes with commas or periods where appropriate, remove mechanical boldface and emoji, use sentence case in headings, straighten curly quotes.
5. Cut filler: remove filler phrases, reduce hedging, replace generic conclusions with specifics.
6. Add voice: vary sentence rhythm, inject appropriate perspective, let some imperfection in. Match tone and register to the text's audience.
7. Apply composition principles from `references/elements-of-style.md`:
   - Convert passive constructions to active voice where the actor is known.
   - Replace negative hedging ("was not very often on time") with positive assertions ("usually came late").
   - Swap abstract language for concrete specifics ("a period of unfavorable weather" becomes "it rained every day for a week").
   - Cut needless words: "the fact that", "who is/which was" padding, "in order to", wordy "he is a man who" constructions.
   - Break monotonous sentence patterns - if three consecutive sentences use the same structure, recast at least one.
   - Move the most important word or phrase to the end of each sentence.
   - Keep one topic per paragraph. End paragraphs with the strongest point, not a trailing detail.

Preserve the original meaning. Do not add information the source text does not contain. Do not remove technical accuracy for the sake of style.

### Phase 5: Verification

Re-read the rewritten text and check:

- No AI patterns from `references/patterns.md` remain.
- Core meaning is preserved (no information lost or invented).
- Sentence structure varies naturally (not uniform length or identical clause patterns).
- Active voice used where the actor is known. No stacked passives.
- Statements are positive and definite, not hedged with negatives.
- Language is concrete and specific, not abstract and general.
- No needless words: no "the fact that", no "who is/which was" padding, no filler expressions.
- Emphatic words land at the end of sentences, not buried in the middle.
- Each paragraph covers one topic and ends with its strongest point.
- Tone matches the original audience and intent.
- Text sounds natural when read aloud.

If any check fails, revise the affected sections and re-verify.

### Phase 6: Report

Output a pattern report:

| Column   | Content                                     |
|:---------|:--------------------------------------------|
| #        | Sequential number                           |
| Pattern  | Pattern name from the catalog               |
| Instance | Quoted offending text from the original     |
| Fix      | What replaced it (or "removed" if stripped) |

Include a summary line: patterns detected count, category count, and overall severity (Minor, Moderate, Heavy).

If `--score-only`, stop here.

### Phase 7: Output

1. If `--dry-run`: output the rewritten text to chat.
2. Otherwise: apply edits to the file in-place. Use the Edit tool for targeted fixes. Use the Write tool to replace the file when the majority of its content changed.
3. Append the pattern report after the output.

## Example

**Input:**
> Additionally, this groundbreaking framework serves as a testament to the team's commitment to fostering innovation, showcasing how modern tools can enhance developer productivity in today's rapidly evolving landscape.

**Output:**
> The framework speeds up common tasks like scaffolding and test generation. The team built it after noticing developers spent 40% of sprint time on boilerplate.

**Patterns fixed:** AI vocabulary (Additionally, groundbreaking, enhance), significance inflation (testament, commitment to fostering), copula avoidance (serves as), superficial -ing (showcasing), promotional language (rapidly evolving landscape)
