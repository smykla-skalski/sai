---
name: humanize
description: Identify and remove AI writing patterns to make text sound natural and human-written. Use when humanizing commit messages, PR descriptions, review comments, docs, changelogs, or release notes. Also for de-slopping text that sounds robotic, has AI vibes, or reads like ChatGPT output.
argument-hint: "[file-path] [--score-only] [--inline]"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
user-invocable: true
---

# Humanize

Remove AI writing patterns from text and replace them with natural, human-sounding alternatives. Based on Wikipedia's "Signs of AI writing" guide, maintained by WikiProject AI Cleanup.

## Arguments

Parse from `$ARGUMENTS`:

| Flag           | Default | Purpose                                         |
|:---------------|:--------|:------------------------------------------------|
| (positional)   | —       | File path to humanize. Prompt user if omitted   |
| `--score-only` | off     | Report detected patterns without rewriting      |
| `--inline`     | off     | Edit the file in-place. Default: output to chat |

## Pattern categories

The skill detects 24 AI writing patterns organized into five categories:

1. Content patterns (1-6): significance inflation, notability claims, superficial -ing analyses, promotional language, vague attributions, formulaic challenges sections
2. Language and grammar (7-12): AI vocabulary words, copula avoidance, negative parallelisms, rule-of-three, synonym cycling, false ranges
3. Style (13-18): em dash overuse, boldface overuse, inline-header lists, title case headings, emoji decoration, curly quotes
4. Communication artifacts (19-21): chatbot correspondence phrases, knowledge-cutoff disclaimers, sycophantic tone
5. Filler and hedging (22-24): filler phrases, excessive hedging, generic positive conclusions

Full pattern descriptions with words-to-watch lists and before/after examples are in `references/patterns.md`.

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

Apply fixes in this order:

1. Strip communication artifacts: chatbot phrases, disclaimers, sycophantic openings.
2. Fix content patterns: deflate significance claims, replace vague attributions with specifics, remove formulaic sections.
3. Fix language patterns: replace AI vocabulary, restore simple copulas (is/are/has), remove negative parallelisms and forced triads.
4. Fix style patterns: replace em dashes with commas or periods where appropriate, remove mechanical boldface and emoji, use sentence case in headings, straighten curly quotes.
5. Cut filler: remove filler phrases, reduce hedging, replace generic conclusions with specifics.
6. Add voice: vary sentence rhythm, inject appropriate perspective, let some imperfection in. Match tone and register to the text's audience.

Preserve the original meaning. Do not add information the source text does not contain. Do not remove technical accuracy for the sake of style.

### Phase 5: Verification

Re-read the rewritten text and check:

- No AI patterns from `references/patterns.md` remain.
- Core meaning is preserved (no information lost or invented).
- Sentence structure varies naturally (not uniform length).
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

1. If `--inline`: apply edits to the file using the Edit tool. Present a summary of changes.
2. If no `--inline`: output the rewritten text to chat.
3. Append the pattern report after the rewritten text.

## Example

**Input:**
> Additionally, this groundbreaking framework serves as a testament to the team's commitment to fostering innovation, showcasing how modern tools can enhance developer productivity in today's rapidly evolving landscape.

**Output:**
> The framework speeds up common tasks like scaffolding and test generation. The team built it after noticing developers spent 40% of sprint time on boilerplate.

**Patterns fixed:** AI vocabulary (Additionally, groundbreaking, enhance), significance inflation (testament, commitment to fostering), copula avoidance (serves as), superficial -ing (showcasing), promotional language (rapidly evolving landscape)
