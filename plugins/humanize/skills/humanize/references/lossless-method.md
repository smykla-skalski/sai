# Lossless method

Write the shortest, plainest text that keeps every fact, instruction, condition and tone the reader needs. This is constrained minimization, not summarization: cut words and complexity only while every essential unit and every protected detail survives.

Delete what carries no required information. Paraphrase what can become clearer without a change in meaning. Keep what cannot be paraphrased safely.

## Contents

1. [Semantic contract](#semantic-contract)
2. [Meaning ledger](#meaning-ledger)
3. [Protected elements](#protected-elements)
4. [Compress, paraphrase or keep](#compress-paraphrase-or-keep)
5. [Edit order](#edit-order)
6. [Preserve tone](#preserve-tone)
7. [Verify](#verify)
8. [Final cut](#final-cut)
9. [High-risk text](#high-risk-text)

---

## Semantic contract

Answer these questions before you edit. When you draft new text, the source is the material the text must carry: the user's request and any diff, commits, notes or files it points to.

| Question | Record |
| :-- | :-- |
| Who reads it? | Teammates, users, customers, maintainers, the public |
| Why do they read it? | To understand, decide, act, comply or verify |
| What must they know? | Results, decisions, facts and the context they need |
| What must they do? | Actions, deadlines, order, conditions |
| What must not change? | The protected elements below |
| What tone matters? | Neutral, friendly, polite, urgent, firm, diplomatic |
| How much may it shrink? | A light edit, a full rewrite, or a length the user set |

A length the user sets holds only while every essential unit fits. If it does not fit, keep the units and say in one line that the limit would drop required content.

## Meaning ledger

Split the source into atomic units: the smallest claims, instructions, conditions or tone signals that can be true, false or lost on their own. "Because shipments were delayed by flooding, we will waive delivery charges for orders placed before 30 June" holds five: shipments were delayed, flooding caused the delay, delivery charges are waived, the waiver applies to orders, and only to orders placed before 30 June. A sentence-level comparison can hide a lost condition, so compare units, not sentences.

| Status | Meaning | Rule |
| :-- | :-- | :-- |
| Essential | Losing it changes what the reader knows, believes or must do | Keep |
| Supporting | Helps understanding | Merge or shorten |
| Dispensable | Repetition, filler, irrelevant history, decoration | Delete |

Counterfactual test: if this unit disappeared, could a reasonable reader reach a different conclusion, take a different action, misread who is responsible, or feel a materially different tone? If yes, it is essential.

The AI pattern catalog names the usual dispensable units: puffery and significance claims, chatbot artifacts, filler, hedges stacked beyond the first, generic conclusions and recaps, promises of updates that name no time or place, and preamble before the point. A substantive claim is not dispensable just because it has no evidence. "It significantly improves performance" stays, at the strength the source gives it, and goes on the report's `Claims without evidence:` list so the author can support it. "A groundbreaking release" is decoration and goes.

## Protected elements

Lock these before you rewrite. A small change to one can cause a large error.

| Class | Examples | Rule |
| :-- | :-- | :-- |
| Numbers, dates, times | `5%`, `$2.3m`, `0.05`, `30 June`, `15:00 UTC` | Keep exactly |
| Ranges and comparisons | `10-15`, `>50`, `at least`, `up to`, `less than` | Keep the meaning exactly |
| Units | `ms`, `GB`, `kWh` | Keep each value with its unit |
| Negation | `not`, `never`, `no`, `without` | Keep |
| Modality | `must`, `shall`, `may`, `should`, `can`, `might`, `expect` | Keep the strength. In a rule or policy, an obligation keeps "must"; a bare command fits only step-by-step instructions |
| Conditions | `if`, `unless`, `only when`, `provided that` | Keep the scope |
| Exceptions | `except`, `other than`, carve-outs | Keep |
| Quantifiers | `all`, `each`, `some`, `any`, `only` | Keep |
| Certainty | `preliminary`, `estimated`, `about`, `appears`, `unverified` | Keep |
| Named entities | People, teams, products, places | Keep |
| Defined terms | `Customer Data`, `Effective Date` | Keep the term and its capitals |
| Attribution | Who said, found or decided it | Keep it with its claim |
| Actors | Who must act and who is addressed: "the on-call engineer", "each engineer", "anybody" | Keep. Do not turn them into "you" or "we" |
| Citations and links | `[14]`, `(Smith, 2025)`, URLs, `#482`, ticket IDs | Keep each with the claim it supports |
| Quotations | Text inside quotation marks | Keep word for word |
| Code | Commands, paths, flags, identifiers, API fields, placeholders such as `%s` or `{name}` | Keep literally, also in a subject line or heading |

Change the form of a protected element only when its value stays identical, as in "forty-eight (48) hours" to "48 hours", or "shall" to "must" for an obligation. List every such change in the report.

Keep a technical term when a plainer word would change its scope: "hash", "OAuth", "idempotent" and "p95" have no exact plain substitute. Explain an unfamiliar term once if this reader needs it. Spell out an acronym used once, and often drop the acronym. Define an acronym used often at its first use.

## Compress, paraphrase or keep

| Situation | Compress | Paraphrase | Keep wording |
| :-- | :-: | :-: | :-: |
| Exact repetition | Yes | Rarely | No |
| Empty introduction | Yes | Sometimes | No |
| Long ordinary words | Sometimes | Yes | Rarely |
| Tangled sentence | Sometimes | Yes | Rarely |
| Jargon with an exact plain equivalent | No | Yes | Sometimes |
| Technical term with no exact substitute | No | Explain around it | Yes |
| Legal defined term | Rarely | Very cautiously | Yes |
| Number or unit | No | Format only, value unchanged | Yes |
| Negation, condition or exception | No | Cautiously | Usually |
| `must`, `may`, `should` | No | Only an equal modal | Usually |
| Citation or link | No | No | Yes |
| Direct quotation | No | Only if you drop the quotation marks and say so | Yes |
| Safety instruction | Only redundant text | Cautiously | Often |
| Qualifier such as "preliminary" or "estimated" | No | Exact equivalent only | Usually |
| Slogan or deliberate rhetorical phrase | Maybe | Maybe | Yes if voice matters |

## Edit order

Work in this order. Much wordiness goes before you change the wording of what stays, which is safer than paraphrasing every sentence:

1. Delete the dispensable units.
2. Merge units that say the same thing, so each fact appears once. A title, subject line or heading counts: the text under it must not repeat it.
3. Reorder for the reader: result or action, then conditions, then explanation, then background.
4. Simplify syntax: actor, action, object, condition. Split a sentence that carries two main ideas.
5. Simplify words: use a plainer word only when it means exactly the same here.
6. Recheck the protected elements and the tone.

For each phrase: delete it if that changes no meaning or tone. Otherwise replace it with a simpler exact equivalent. Otherwise restructure it if the scope stays the same. Otherwise keep it.

> **Before:** It is important to note that the deadline for submitting the form is Friday, and applicants should therefore make sure that they submit the form by Friday.
>
> **After:** Applicants should submit the form by Friday.

The second half only repeated the deadline, so merging it loses nothing. "Should" stays, because a deadline the source states as advice must not become an order.

## Preserve tone

Meaning includes force as well as facts. "Send the document today" and "Could you send the document today?" ask for the same action with different force. Keep the politeness, urgency, uncertainty, confidence, apology, enthusiasm, authority, diplomatic distance or persuasion the source carries. Cut unnecessary politeness, not all politeness: "We sincerely apologise for any inconvenience this delay may cause you" becomes "We apologise for the delay", not nothing.

> **Before:** I just wanted to reach out to let you know that unfortunately we are not going to be able to complete the migration by the originally anticipated date of Thursday because we encountered an unexpected issue during database testing. We currently expect that we should be able to complete it by Monday. We sincerely apologise for any inconvenience that this delay may cause you.
>
> **After:** We cannot complete the migration by Thursday because database testing found an unexpected issue. We now expect to finish by Monday. We apologise for the delay.

The original deadline, the cause, the new estimate and the apology stay. "Expect" stays rather than becoming the more certain "will".

## Verify

Check the result against the ledger before you shorten it again.

| Gate | Requirement |
| :-- | :-- |
| Essential recall | Every essential unit of the source can be recovered from the result |
| Support precision | The source supports every claim in the result |
| Protected accuracy | Every protected element is correct |
| Contradictions | None |
| Citations | Each citation, link and attribution stays with the claim it supports |
| Purpose and tone | The text keeps the purpose and the force of the source |

Check both directions. Source to result: can every essential unit be recovered? Result to source: is every claim supported? A text can pass one and fail the other: it can omit half the source with every remaining claim true, or keep everything and add a claim the source never made.

Ask these questions of the source and of the result. A different answer is a defect:

- Who does the action, and what action is required?
- When must it happen, and in what order?
- What caused the event?
- What quantity and unit are stated?
- What condition triggers the rule, and what exceptions apply?
- How certain is the claim, and who is its source?
- What limitation is stated?
- What does the reader do next?

Then assume the result is subtly wrong. Look for the smallest wording difference that could cause a different action, deadline or number, a stronger or weaker claim, a lost exception or uncertainty, changed attribution, or a changed technical or legal scope. Restore what was lost, then run the checks again.

Readability formulas, word overlap and embedding similarity do not prove that two texts carry the same information. Use the gates and the questions.

## Final cut

Only after every gate passes, cut further, from the largest unit down. Try to drop or merge each sentence: two sentences with the same actor or condition often become one, and a sentence that only repeats a duty goes ("Each engineer must run it. They should not skip it." becomes "Each engineer must run it."). Keep a duty's conditions and deadline in the sentence that states the duty: "The engineer must notify the team. They must do so within 48 hours." becomes "The engineer must notify the team within 48 hours." Split a long sentence only where the new sentence needs no repeated subject and modal. Then try each clause, then each word, including words that restate a heading or subject line and soft fillers such as "send over" or "so much". Keep a cut only if every gate still passes. Stop when nothing else can go.

The text is ready when these answers hold. Check the fifth last:

1. Can the reader recover every fact and instruction they need? Yes.
2. Could anything in the result be false while the source is true? No.
3. Could the reader take a materially different action because of the result? No.
4. Do certainty, conditions, exceptions, attribution and tone keep their force? Yes.
5. Is every remaining word needed for meaning, use or tone? Yes.

## High-risk text

For legal, regulatory, contract, safety, medical or financial text, also keep the actors, defined terms, modal verbs, conditions, exceptions, thresholds, time relations, remedies, cross-references and jurisdiction words. Keep the wording of each condition, threshold and exception as the source gives it, without ellipsis, and shorten only the words around them. Never trade legal or safety precision for brevity. Tell the user in one line that a qualified reviewer must check the result before it is used.

> **Before:** Notwithstanding any other provision of this Agreement, the Supplier shall notify the Customer in writing without undue delay and, in any event, not later than forty-eight (48) hours after becoming aware of any actual or suspected Security Incident that affects, or is reasonably likely to affect, Customer Data.
>
> **After:** Despite any other term of this Agreement, the Supplier must notify the Customer in writing without undue delay and no later than 48 hours after becoming aware of any actual or suspected Security Incident that affects, or is reasonably likely to affect, Customer Data.

"The Supplier must report incidents within 48 hours" is shorter, and it deletes the written form, the duty to act without undue delay, suspected incidents and the "reasonably likely" threshold.

Keep the text out of external tools and services, and keep the attribution of quoted or third-party material.

---

## Source

Condensed from a lossless plain-language rewriting method built on [ISO 24495-1:2023](https://www.iso.org/standard/78907.html), [ISO 24495-2:2025](https://www.iso.org/standard/85774.html) and [ISO 24495-3:2026](https://www.iso.org/standard/86938.html), [Digital.gov plain-language guidance](https://digital.gov/guides/plain-language/writing), [W3C clear-content guidance](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/) and QA-based factual-consistency research ([QAFactEval](https://aclanthology.org/2022.naacl-main.187/)).
