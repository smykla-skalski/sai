# Document rules

These rules come from research on software design documents, lightweight docs for small teams, small-team planning and decisions, shipping to a fixed end date, and personas and user stories. Their main sources are Google-style design docs, Rust RFCs, Kubernetes Enhancement Proposals (KEPs), MADR and Nygard decision records, arc42, Oxide RFDs, GitLab design documents, Shape Up, DSDM MoSCoW, the GOV.UK service manual, INVEST and the Three Cs, Nielsen Norman Group personas, Lethbridge et al. and Buchgeher et al. on documentation decay, and Digital.gov reader tests.

## Core definition

The best document is the smallest one that lets its intended readers understand the problem, the decision, the important trade-offs and what happens when the design meets reality. Its depth grows with the consequences of failure, not with the template. Standardize the questions a document answers, not its page count.

## Applicability

Group W applies to any document or message that proposes, records or runs work: a design doc, decision record, pitch, plan, proposal, RFC, spec, user stories, persona, runbook, postmortem, process or policy, or a chat message, Slack post, email or issue comment about work. It does not apply to code. The type table below gives the parts each type needs.

## W - Documents

| ID | Rule | Broken when |
| --- | --- | --- |
| W1 | Pick the smallest document type whose review surface matches the risk, reach and lifetime of the decision | KEP- or arc42-level ceremony on a local or reversible decision, or a hard-to-reverse decision (datastore, public API shape, auth, tenancy, personal data, security) recorded only in chat or one line |
| W2 | Put the point first: the first lines give the problem, the proposed decision and its main consequence, so that a reader finds the decision within a minute | The document opens with history, APIs, schemas, classes or a table of contents, and the decision is buried |
| W3 | State the problem as observable pain for named people before any solution, and turn a requested solution back into the problem it solves | The document only announces a solution ("build a map", "add Kafka"), or the problem is generic ("improve scalability") |
| W4 | Make scope and success explicit: goals, non-goals and one or two observable success signals | There are no non-goals, or nobody can tell when the work is done or whether it worked |
| W5 | Separate facts from assumptions: hard constraints with their source, assumptions marked as assumptions, unknowns as open questions with who decides and by when | An assumption reads as fact ("admins hate mobile"), a number or owner has no source, or a gap is papered over |
| W6 | Argue against the proposal: the serious alternatives and "do nothing", each with why it lost, and the drawbacks of the chosen option | Only the chosen option appears, or the alternatives are straw men |
| W7 | Make consequences concrete and testable: what fails, who notices, what happens next | "Failures are handled appropriately", "the design is resilient", "it should scale" |
| W8 | Cover operation in proportion to risk: security and privacy, failure behavior, observability, resource limits | A production-facing change says nothing about how it fails or how anyone sees it fail, or a local change carries a full readiness section |
| W9 | Give a release and return path: rollout steps, rollback, the evidence to accept the change. A rollback keeps the safeguards: idempotency records, queued work, audit events, duplicate controls | There is no rollback, or the rollback drops data, safeguards or work in flight |
| W10 | Record the decision: owner, status, date, confidence, open questions and a "revisit if" trigger | No owner or status, or a provisional choice has no trigger to revisit it |
| W11 | Every section and sentence carries information for this reader, and says each fact once (the opening summary is the one allowed preview): specialist detail (APIs, schemas) comes after the shared explanation, and links replace copies | Headings with "TBD" or "N/A", sections kept only because a template has them, pasted implementation, the same fact in two places |
| W12 | Keep each diagram to the relationships the argument needs, and explain it in text | A diagram needs a verbal tour, or the text depends on an image to make its point |
| W13 | Use one term for one concept, define an unfamiliar term or acronym where the reader first needs it, and name the actor ("the API rejects the request") | Synonyms for one thing, undefined acronyms, or a passive voice that hides who acts |
| W14 | Keep the document where the work happens: dated records (decisions, pitches, postmortems) are never edited, only superseded; living docs (README, handbook, architecture page, runbooks) fit about one screen and name an owner and a last-reviewed date; "how" steps become scripts that CI runs | A page detached from the change it describes, an accepted record rewritten, a living doc with no owner, or setup steps only as prose that nobody runs |
| W15 | Write for comprehension, not completeness: a representative reader can state the problem, the decision, why the alternatives lost, the main risk and the return path without the author | A reader must ask the author what the document means |

Severity follows the rules catalog: a missing return path or safeguard on a stateful or production change is High.

## Types

Use the type the user names. Otherwise use the smallest type that fits. Use the repository's own template for a type when it has one.

| Type | Use when | Size | Parts, in order |
| --- | --- | --- | --- |
| Decision log line | A decision that is easy to reverse, often made in chat or a call | One line, written within a day | Date, "In the context of <X>, we chose <A> over <B> to get <benefit>, accepting <cost>. Revisit if <trigger>.", status, link |
| Decision record (ADR) | One hard-to-reverse decision | One page, 300 to 1,200 words | Title as a noun phrase; date, status, deciders, confidence; one-sentence summary; context in 2 to 5 sentences; options, one line each with why chosen or rejected; consequences: easier, harder, accepted cost; revisit if |
| Pitch | A bet of more than about a week or with two or more people, above all with a fixed end date | One page | Owner, status, decide-by date; appetite (the time the problem is worth, set before the design) and end date; one-sentence bet; frame: the problem as facts, the outcome; shape: solution sketch, must-haves, nice-to-haves marked to cut first, no-gos, rabbit holes solved or fenced off; open questions; decision |
| Short design doc | A change inside one system or component, with low risk | 300 to 1,000 words | Owner, status, date; summary; problem; goals and non-goals; decision with failure behavior; alternatives; risks and rollout; open questions |
| Design doc | A substantial feature across several components | 1,500 to 3,000 words, less when that says enough | Owner, status, date; summary; context and problem; goals and non-goals; constraints; proposed design with failure behavior; alternatives and trade-offs; risks and operations; rollout and rollback; open questions |
| Expanded design doc | A broad or high-risk change to a production platform | Longer only as the risk demands | A design doc plus testing, upgrade and downgrade, monitoring, scalability and troubleshooting |
| Plan or kickoff | The start of a project or bet | One page | Problem; outcome signal; appetite and end date; the quality floor that never moves (data integrity, security, accessibility, availability); non-goals; decision owners and who breaks a deadlock; hard constraints apart from assumptions; the top three unknowns, each with an owner and the next cheap test; what is true when it is done, user value and handover included; stop condition. At the end date the only outcomes are ship, cut and ship, stop, or reshape |
| User stories | Agreeing on small, testable results | One card per story | A real actor (a role or persona, not "user"); the behavior, not the implementation; the reason; observable acceptance criteria with error and boundary cases, Given-When-Then for rules; a vertical slice, not a layer; criteria apart from the team's definition of done; a quality need as a measurable constraint, not "As a database"; distant stories kept coarse |
| Persona | A shared picture of users that drives decisions | The smallest useful set | Behavioral summary, goals, behaviors, constraints, pain points, evidence links, confidence (an assumption-based persona is marked unvalidated), owner. No decorative demographics, invented quotes or population shares without statistics |
| Runbook | A failure or manual fix that has happened, plus deploy, rollback and restore | One page | Owner and last-reviewed date; what the alert means and the user impact; numbered if-then steps with copy-pasteable commands and their expected output; when and to whom to escalate |
| Postmortem | An incident, within 48 hours | One page | Impact, timeline, the conditions that caused it with no blame, actions with owners |
| Process or policy | A written procedure for people | As short as the steps allow | Purpose; who it applies to; the steps in order with owners and decisions; the route for exceptions; how to check that it works |
| Message | A chat message, Slack post, email or issue comment that proposes, plans, decides or explains work | As short as it can be, often 1 to 5 sentences | The point or the ask first; the decision with its reason, owner and date; what the reader must do and by when; open questions. Answer a request with a date, not "will do". No headings in a short message |

## Short design doc

```markdown
# <Title>

Status: <Draft | In review | Accepted> · Owner: <name> · Updated: <date>

<Summary: the problem, the decision and its main consequence, in 2 to 4 sentences.>

## Problem
## Goals and non-goals
## Decision
## Alternatives
## Risks and rollout
## Open questions
```

Add a section only when it carries information for this reader. In each section, prefer a concrete consequence ("after three failed deliveries, stop and alert the owner") to a property ("the design is resilient").
