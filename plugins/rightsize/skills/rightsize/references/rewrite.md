# Rewrite

Rewrite an existing document or message so that its content is the minimum adequate system and its prose is plain, and lose nothing it needs. Change no file other than the document, and none for a message.

## Phase 1: Find the document

Use the first case that applies:

1. A named file, or pasted text.
2. No target: the latest document or message in this conversation that the request points to, such as a plan, design, proposal, process or answer that the user or the agent wrote.
3. Nothing found, or two or more equally likely targets: ask once with AskUserQuestion, one option per candidate.

Code is not a document. For a code target, reply in one sentence that rewrite works on documents and that audit checks code, then stop. Read the whole text. If a path is unreadable, report it and stop.

## Phase 2: Understand

Read [references/rules.md](rules.md), [references/documents.md](documents.md) and [references/prose/lossless-method.md](prose/lossless-method.md) in full. Pick the groups: P, M, N, R, B, I, V, D, E and W always; G for a new software project, service, component or initial architecture; T and K for software.

Write working notes, kept out of the reply: the semantic contract, the meaning ledger and the protected elements. Note what the work must do: its outcome, users and hard constraints, stated or plainly implied.

## Phase 3: Check the content

Check each rule in the chosen groups in both directions: what the document adds without a current reason, and what it removes or skips that a requirement, failure mode or real case needs. Then try to refute each finding. Does a stated or plainly implied requirement, constraint or measurement justify the element (N2)? Would the fix remove variety that a real case needs (V1 to V3)? Drop each finding that fails. Keep the rest, each with its rule ID and the smallest fix, in the order eliminate, combine, default, standardize, encapsulate, automate, optimize.

## Phase 4: Plan the content changes

Mark each ledger unit keep, change or move, and give each change and move its rule ID:

- Move an element that has no N2 reason to non-goals or alternatives, in one line with the trigger that would admit it. Elements that share a trigger share one line. Never delete an author's idea silently.
- Merge repeats into one place (R2, W11).
- Restore a removed safeguard, and add one that a requirement needs (V2, V3).
- Add each missing part the type needs, such as a success signal, non-goals, alternatives with "do nothing", a rollback, an owner and status, from what the document already says. When the facts are missing, add an open question instead. Never invent a number, owner, date, measurement or commitment.
- Add an open question only for a part the type needs, or for information that a stated requirement or safeguard depends on. An edge case that the document does not raise is not a rewrite change.
- Reorder the parts to the type's order in documents.md, the point first. Keep the author's type unless it breaks W1.

Every other unit keeps its meaning.

## Phase 5: Rewrite the prose

Read [references/prose/patterns.md](prose/patterns.md), [references/prose/usage.md](prose/usage.md), [references/prose/voice-guide.md](prose/voice-guide.md) and [references/prose/elements-of-style.md](prose/elements-of-style.md) in full. Check the document against all patterns and usage rules, and note each hit. This phase needs ultrathink.

Apply the planned changes. Then follow the method's edit order: delete dispensable units, merge repeats, reorder so that the point comes first, simplify syntax, simplify words, restore the voice. Fix every hit, faint ones included. Say each fact once: the summary gives the problem and the decision in short form, and the other sections add detail without repeating it. Keep the author's voice, terms and courtesy. Never add facts, examples, commands, causes, commitments, feelings or opinions that the document lacks. Except for a planned change, never change certainty, modal verbs, numbers, units, responsibility, conditions, exceptions, quotations or citations.

## Phase 6: Verify and cut

1. Run the method's gates, questions and adversarial check on every unit marked keep, and restore what was lost.
2. Check the result against the chosen rules again: each finding from Phase 3 is fixed or is an open question, and the result has each part that W2 to W10 require, or an open question for it. Add other parts from the type table only when the author's own text calls for them, because each one makes the document longer.
3. Confirm that no pattern or usage error remains and that a reader can state the problem, the decision, why the alternatives lost, the main risk and the return path from the first screen (W15).
4. Final cut: delete what carries nothing until nothing else can go, and rerun the gates after each material cut.

## Phase 7: Output

1. For a file, edit it in place before you reply: Edit for local fixes, Write when most of it changed. For pasted text, a message from this conversation, or with `--dry-run`, print the rewrite, ready to paste.
2. Then print the report:

```markdown
| # | Rule | Change |
| --- | --- | --- |
| 1 | N2 Admission test | Moved the Redis cache to alternatives: no measured latency problem; admit it when p95 latency passes 300 ms |
```

One row for each change or move from Phase 4, sorted by severity. Rule is a rule ID from rules.md or documents.md and its short name, never the name of a part from the type table. Change is one sentence of at most 25 words. Prose fixes get no rows. With no content change, write `No content changes.` instead of the table. Under it, one summary line: `4 content changes, 2 open questions, 11 prose fixes. 1,240 → 610 words.` For legal, regulatory, safety, medical or financial text, add the line `A qualified reviewer must check this before use.`

After an in-place edit, the report is the whole reply. After a printed rewrite, the reply is the rewrite, then the report. Write nothing else: no sentence before them, nothing after the summary line except the reviewer line, no list of what stayed, no explanation of the word count, no offer.
