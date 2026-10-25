---
name: humanize
description: "Use this skill whenever you write or rewrite text for people, even one short paragraph, that must be plain, concise and natural without losing anything. Skip it, without opening it, for summaries, translation, proofreading only, formal or promotional rewrites, code, comments, docstrings, data structure, AI-detection questions, and chat answers. It rewrites a pasted or file draft that reads wordy, unclear, stiff, corporate, buzzword-heavy (\"robust\", \"seamless\", \"leverage\"), hyped or ChatGPT-like, cuts text to a set length, also prose values in YAML or JSON, and writes new prose, also from notes or bullets: a commit message, PR description, release notes, changelog, a docs, README or CONTRIBUTING section, an email, a blog post or paragraph, a Slack post or announcement, a review comment or user-facing error messages. Load it before you write, even when you first read a diff, staged changes or files for the facts. It keeps every fact, number, condition and tone. Also use it to score how AI-like a text sounds."
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. No scripts or network access needed.
argument-hint: "[file-path | text] [--score-only] [--dry-run]"
allowed-tools: AskUserQuestion Edit Read Write
user-invocable: true
metadata:
  short-description: Write and rewrite text plainly without losing meaning
---

# Humanize

Make text for people as short and plain as it can be while it keeps everything its reader needs: every fact, instruction, condition, number and the intended tone. Remove AI writing patterns, fix usage, apply the composition principles, and check the result against its source before you cut further.

Modes: rewrite an existing draft, pasted or in a file; draft new text the user asks for, from the material it must carry; score with `--score-only`.

Not for code, identifiers, data structure (prose values in it are text), summaries or cuts that drop required content, translation, proofreading that must keep the wording, more formal or promotional rewrites, or your own chat answers. Not for beating AI detectors or hiding AI use that a policy requires you to disclose: the patterns are editing smells, not proof of who wrote the text.

Run every phase yourself in this conversation, never in a subagent: only it holds your notes and can ask the user.

## Agent compatibility

Paths are relative to this skill's directory. Outside Claude Code:

| Claude Code feature | Fallback |
| :-- | :-- |
| AskUserQuestion | Ask in plain text and wait for the answer |
| Edit and Write | Use the agent's file-edit tool (`apply_patch` in Codex). If the sandbox blocks the write, request escalation |

## Arguments

Invocation arguments: `$ARGUMENTS`

If that line is empty or still shows the literal placeholder, take the file path, text and flags from the user's request.

| Flag | Purpose |
| :-- | :-- |
| (positional) | File path or raw text to rewrite or score |
| `--score-only` | Report patterns without rewriting |
| `--dry-run` | Print the rewrite to chat instead of editing the file in place |

## Workflow

### Phase 1: Input

1. Pick the mode: draft when the user asks for new text, score with `--score-only`, else rewrite.
2. Rewrite or score with no file path or text: use AskUserQuestion to get it. Draft: collect the facts the text must carry from the request and any diff, notes or files it names, and read the file the text goes into.
3. Read the target or keep raw text. If the path is unreadable, report it and stop.
4. Warn if the text is under 50 characters.

### Phase 2: Understand

Read [references/lossless-method.md](references/lossless-method.md) in full. Write working notes, kept out of the reply: the semantic contract, the meaning ledger and the protected elements.

### Phase 3: Scan

Skip in draft mode. Read [references/patterns.md](references/patterns.md) and [references/usage.md](references/usage.md) in full. Check the text against all 30 patterns and every usage rule, one at a time. Record each hit: pattern or rule, quoted text, severity (faint, clear or glaring).

- No hits, and the method's final cut would remove nothing: say in one sentence that the text needs no changes, then stop. Do not list what you checked.
- `--score-only`: go to Phase 7.

### Phase 4: Voice

Read [references/voice-guide.md](references/voice-guide.md) in full. Note the author's own voice and courtesy, the force of each request or warning, and the medium's shape. In draft mode, match the file the text goes into or the user's examples.

### Phase 5: Rewrite or draft

Read [references/elements-of-style.md](references/elements-of-style.md) in full, and in draft mode also patterns.md and usage.md. This phase needs ultrathink: weigh every change against the ledger, the protected elements and the tone.

Follow the method's edit order: delete dispensable units, merge repeats, reorder so the point comes first, simplify syntax, simplify words, then restore the voice. Fix every hit, faint ones included. In draft mode, write from the ledger in the medium's shape so the text needs no fixes.

Never add facts, examples, commands, causes, commitments, feelings or opinions the source lacks. Never change certainty, modal verbs, numbers, units, responsibility, conditions, exceptions, quotations or citations. A substantive claim without evidence keeps its strength; only puffery goes. Never add typos or broken grammar to seem human.

### Phase 6: Verify and cut

Run the method's gates, questions and adversarial check on the result. Also confirm that no pattern or usage error remains, the first sentence gives the point, and the voice and tone fit the medium. Restore what was lost and check again. Then make the final cut, rerunning the gates after each material cut, until nothing else can go. In draft mode, the source is the material from Phase 1.

### Phase 7: Report

Skip in draft mode.

Use this exact table header: `| # | Pattern | Instance | Fix |`. Keep these four columns. Pattern names the pattern or usage rule, Instance holds only the quoted original text, and Fix holds only the replacement or "removed", with no notes. Give each quoted phrase one row naming every pattern it shows, and never quote text inside another row's quote.

Under it, one summary line with word counts: `14 patterns in 5 categories. Severity: Heavy. 212 → 94 words.` (Minor, Moderate or Heavy). Add these only when they apply, one quoted item per line:

- `Claims without evidence:` substantive claims kept although the source gives no evidence, quoted as in the original. The author's own numbers and facts are evidence.
- `Changed details:` only protected elements whose form changed, such as `forty-eight (48) hours → 48 hours`; never rewordings or merges.
- For legal, regulatory, safety, medical or financial text, the line `A qualified reviewer must check this before use.`

With `--score-only`, omit the Fix column, the word counts and the lists.

Never call the text AI-written or add an authorship disclaimer: people write these patterns too. The reply is the output, then the report, and nothing else: no sentence before or after them, no commentary, advice, follow-up offers or alternatives.

### Phase 8: Output

1. Draft mode, no report: in chat, reply with the text alone, without explaining your choices. In a file, reply only `Added "<section>" to <file>.`: the user reads the text there, so position or content is noise. Do nothing else with the text that the user did not ask for.
2. With `--dry-run`, or for raw text, print the rewrite to chat.
3. Otherwise edit the file in place before you reply: Edit for local fixes, Write when most of it changed. Never report an edit you did not make.
4. Print the report next. After an in-place edit, the report is the whole reply: no copy of the text and no summary of the changes.
5. Before you send, delete every sentence of the reply that is not the output, the report or the one file sentence.
