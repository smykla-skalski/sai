# Write

Write a new document or message whose content is the minimum adequate system and whose prose is plain: a design doc, decision record, pitch, plan, proposal, RFC, spec, user stories, persona, runbook, postmortem, process or policy, or a chat message, Slack post, email or issue comment that proposes, plans, decides or explains work. Change no file other than the one the document goes into, and none for a message.

## Phase 1: Gather the material

1. Collect what the document must carry: the request, the decisions and facts in this conversation, and the files, notes, diffs or tickets it names. When the document is about code or a system in this repository, read the code, config and docs it describes. Look for the repository's own template, folder and numbering for this type, such as an ADR folder.
2. If no problem or outcome can be found or plainly inferred, ask once with AskUserQuestion. Otherwise go on without asking.

## Phase 2: Read the rules

Read [references/rules.md](rules.md), [references/documents.md](documents.md) and [references/prose/lossless-method.md](prose/lossless-method.md) in full. Pick the groups: P, M, N, R, B, I, V, D, E and W always; G for a new software project, service, component or initial architecture; T and K for software.

Write working notes, kept out of the reply: the semantic contract and a meaning ledger of the material. The ledger lists the reader, the purpose, the outcome, the users, each hard constraint with its source, each decision already made, and every fact, number, name and date.

## Phase 3: Shape the content

1. Type: the one the user names, else the smallest type in documents.md that fits the risk, reach and lifetime (W1).
2. Start from the minimum: the current system or the smallest change that meets the outcome and the constraints (N3), and for a new project the default topology (G2). Admit each further element only for an N2 reason, and state that reason in the document. For a new component (a service, datastore, queue, cache, framework or flag), also state its owner, cost, rollback path and removal trigger (N4). An ordinary table, module or function needs none of this.
3. Put each speculative idea from the material under non-goals or alternatives, in one line with the trigger that would admit it (N5). Ideas that share a trigger share one line. Never drop an idea silently.
4. Keep every safeguard the need requires (V1 to V3): security, privacy, data integrity, audit, accessibility, recovery, duplicate controls.
5. Keep the user's own decisions. When one breaks a rule, keep it and make the document honest: state its reason, or ask for the reason under open questions, and put the smaller option under alternatives with the trigger that favors each.
6. Fill the parts the type needs (W2 to W10). A part with no material becomes an open question with who decides, or a stated assumption, never filler. Never invent a number, owner, date, measurement or commitment.

## Phase 4: Draft

Read [references/prose/patterns.md](prose/patterns.md), [references/prose/usage.md](prose/usage.md), [references/prose/elements-of-style.md](prose/elements-of-style.md) and [references/prose/voice-guide.md](prose/voice-guide.md) in full. This phase needs ultrathink.

Write from the ledger in the type's order, so that the text needs no fixes: the point first, plain words, one term for one concept, named actors, concrete consequences. Say each fact once: the summary gives the problem and the decision in short form, and the other sections add detail without repeating it. Match the voice of the file or repository the document goes into. Never add facts, examples, commands, causes, commitments, feelings or opinions that the material lacks. Never change certainty, modal verbs, numbers, units, responsibility, conditions or exceptions. Turn a relative date into a calendar date only when it is certain. State your own estimates, such as load, capacity, cost or effort, as assumptions. Never add typos or broken grammar to seem human.

## Phase 5: Check and cut

1. Check the draft against every rule in the chosen groups, in both directions, and fix each broken rule.
2. Run the lossless method's gates against the material: every ledger unit is in the document or deliberately under non-goals, alternatives or open questions, and the material supports every claim.
3. Check the draft against all patterns and usage rules, and fix every hit.
4. Reader test: from the first screen, a reader can state the problem, the decision, why the alternatives lost, the main risk and the return path (W15). Fix what is missing.
5. Final cut: keep the document within its type's size in documents.md, and shorter when that says enough. Delete each section, sentence and word that carries nothing for this reader, and rerun the gates after each material cut.

## Phase 6: Output

- With a file path, or when the user asks to add the document to the repository: write it there, in the repository's folder and numbering for the type. Then your whole reply is the one line `Wrote <path>.` The open questions, assumptions and choices are in the document, so a summary of any of them makes the user read them twice.
- Otherwise, for a message, or with `--dry-run`: reply with the text alone, ready to paste.

Do not explain your choices, summarize the text, list the rules or add a report, a note or an offer.
