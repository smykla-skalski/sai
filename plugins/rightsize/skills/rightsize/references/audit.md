# Audit

Check work against the simplicity rules and report what is overbuilt and what is oversimplified. Read only: never edit files, commit, comment on a PR or apply a fix.

## Phase 1: Find the target

Use the first case that applies:

1. The target is named: file or directory paths, a PR number or URL, a branch or commit range, pasted text (plan, design, process, policy), or a description of the work.
2. No target: audit the work in this conversation, the latest substantive work product or subject: code the agent implemented, a plan or design it presented, a system or process under discussion. The user's latest messages weigh most. For code, list every file the session created, edited or deleted, from its edit and write calls and the commands it ran. Include changes it already committed: find its commits with `git log` and diff from their parent. Audit the current files and that diff, not your memory of them, and leave out changes the session did not make.
3. No work in the conversation: the uncommitted changes, else the current branch against its base branch.
4. Nothing found, or two or more equally likely targets: ask once with AskUserQuestion, one option per candidate. Never audit a guess silently.

## Phase 2: Read the rules and the work

Read [references/rules.md](rules.md) in full. When the request is about a document itself, such as its length, structure or type, also read [references/documents.md](documents.md) in full. Then read enough of the work to judge it. For code, read the diff and its surroundings: callers, helpers it could reuse, manifests, dependency, deployment and config files. For a document, read all of it. Note what the work must do: its outcome, users and hard constraints, stated or plainly implied.

Pick the groups: P, M, N, R, B, I, V, D and E always; G for a new software project, service, component or initial architecture; T and K for software; W only when the request is about a document itself.

## Phase 3: Check every rule

Check each rule in the chosen groups, one at a time, in both directions: what the work adds without a current reason, and what it removes or skips that a requirement, failure mode or real case needs. Check what the user asked for the same way: a request for a mechanism ("add a cache", "make it configurable three ways") is not a reason by itself, only the need behind it is. Give each rule one status:

- Broken: evidence shows the violation.
- At risk: partly broken, or the next likely change breaks it.
- Gap: the rule needs information that the work leaves out, such as a success measure, non-goals, a baseline or a ledger row.
- Holds.

Evidence is a `file:line`, a quote, a command output or a specific message in the conversation. Without evidence, a finding is a Gap, not a Broken rule.

## Phase 4: Challenge the findings

Try to refute each Broken and At-risk finding. Does a stated or plainly implied requirement, constraint or measurement justify the element (N2)? For a requested mechanism, keep the finding and say that it was requested. Would the fix remove variety that a real case needs (V1 to V3)? Drop or downgrade each finding that fails. Complexity that survives goes in Keep, so that nobody removes it later.

## Phase 5: Report

Use this structure. Leave out an empty section, except Broken rules:

```markdown
## Rightsize audit: <target>

Scope: <what you audited, how you found it, groups checked>
Verdict: <Adequate | Overbuilt | Oversimplified | Mixed> - <one sentence>

### Broken rules

| # | Rule | Status | Severity | Evidence | Fix |
| --- | --- | --- | --- | --- | --- |
| 1 | N6 One-implementation abstraction | Broken | Medium | `notify/factory.py:12` builds only `EmailNotifier` | Call `EmailNotifier` directly and delete the factory |

### Other issues

### Gaps

### Suggestions

1. #3 - free, removes most of the wait

### Keep

<N> broken (<H> high, <M> medium, <L> low), <N> at risk, <N> gaps. Groups: P M N R B I V D E
```

Write the shortest report that loses no finding: say each thing once, in one place.

- Scope: one sentence.
- Rule: the ID and a short name. Status: Broken or At risk. Sort by severity, then by the size of the burden. One row per root problem: put repeats of one violation in one row with every location. A row whose fix would be "removed by #N" belongs in row N's evidence instead.
- Evidence: a location or a quote of at most 15 words, plus the fact that makes it a violation. Fix: exactly one sentence of at most 25 words with the smallest effective change, in the order eliminate, combine, default, standardize, encapsulate, automate, optimize. Never suggest removing a safeguard to reduce a count.
- Other issues: at most three, one sentence each, only for problems that map to no row, such as a trade-off presented as a simplification.
- Gaps: only missing information that could change a finding, a severity or the verdict, and that no row already covers. One line each: what is missing, the rules it blocks, the next check.
- Suggestions: row numbers in the order to apply them, ranked by value for effort, each with a reason of at most eight words. Never describe a fix again. Add a ledger row (owner, cost, rollback path, removal trigger) for complexity that stays without one.
- Keep: only complexity that someone could be tempted to remove and that no Fix already keeps, one line each with its reason.
- With no broken rule, say so in the verdict and put one row `None` in the table.

The report is the whole reply. Do not add an offer or a question after it. This is not a bug hunt: report a correctness or security defect only when a broken rule causes it, such as a removed check.
