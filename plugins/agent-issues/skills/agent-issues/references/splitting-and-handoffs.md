# Splitting work and handing it to agents

Read this when a goal looks like more than one issue, when the user asks to split, and for `--brief`. Splitting well is the highest-leverage move: right seams make every child shippable alone, wrong seams give children that each look reviewable and none that delivers value.

Evidence strength for each rule is in [evidence.md](evidence.md). Vertical slicing and the numeric size guides are inference and heuristics, not measured results; the direction (small, self-contained, one change per agent) is well supported.

## Contents

- When to split
- Two is a dependency, three or more is a group
- Slice vertically
- Where to cut
- Order the slices
- Make each child self-contained
- Spikes
- Post-split check
- Mechanics
- Subagent briefs

## When to split

Split when any of these holds, not when the prose got long:

- The goal names two capabilities (an "and" or an "or").
- The outcomes are uncountable or run well past six.
- It mixes a feature with a cross-cutting quality change.
- An embedded unknown has to be researched before it can be estimated.
- It would not fit one reviewable diff.
- A competent engineer would need much more than about three hours (a heuristic from agent-product guidance; failure rates rise with files and lines changed).

One agent should own one change. Multiple changes at once risk partial results or an exhausted context.

## Two is a dependency, three or more is a group

Two related issues are a dependency, not a group. Sequence them and record a native blocked-by relationship. Do not build an umbrella over two.

Three or more standalone issues justify an umbrella. The umbrella keeps the ordinary issue shape at goal level and does not list its children in the body. Attach children as native sub-issues so GitHub renders the list and progress.

## Slice vertically

Each child delivers one observable behavior through every layer it touches. A child named for a layer or a step ("add the API", "write the tests", "build the form") is the usual bad cut: each looks reviewable and none ships, so value and integration risk pile onto the last child.

The check: the moment this child merges, can a user or operator do or see something they could not before? If not, the cut was horizontal; re-slice.

For agents this is a correctness rule. A later child may be picked up by a fresh agent with no memory of the first, so every child leaves the default branch releasable.

## Where to cut

Try these in order; the first that yields two valuable halves wins.

- **Spike.** An unknown blocks estimation. Split off a timeboxed research issue first.
- **Path.** Ship the main path; defer alternate and error paths.
- **Interface.** One UI, API or CLI surface at a time, each end to end.
- **Data.** One data type, format or source first.
- **Rules.** Ship the simple rule set; add elaborate cases later.
- **Also:** workflow steps (thin end-to-end first), operations (create, read, update, delete), simple version before the hard variant, correct before fast, happy path before edge handling.

Worked example. "Add team billing to the dashboard" cut by layer gives a schema issue, an API issue and a settings-page issue, and nobody can bill anything until the last lands. Cut by what a user can do: show the current plan and price, let an admin change plan, show invoice history. Each merges with something new visible, and the first is the walking skeleton.

## Order the slices

Land the thinnest end-to-end slice first (the walking skeleton), so integration risk is retired early. Then order so the default branch stays releasable after each merge. Where dependencies leave a choice, land the slice that retires the most uncertainty first, not the easiest. Dependency is the hard constraint and risk the tiebreaker.

Before recording a dependency, check whether a vertical re-slice dissolves it. A skeleton slice that ships user-visible value is a legitimate dependency. A dependency on a layer slice is the smell.

## Make each child self-contained

An implementer often starts from the child alone and assumes it shares state with the parent when it does not.

- Inline every decision, constraint and non-goal the child needs. Do not rely on the umbrella body.
- Restate hard constraints as short must and must-not lines, not narrative. Prose summaries lose constraints more often than structured lines.
- Include the verification command and the stop-and-flag triggers in the child.
- If a document must be read, say "read `<path>` first" in the child. A passive link is rarely followed.
- Do not name the umbrella in prose. The native sub-issue link shows it on both sides.
- Do not describe blocking relationships in prose; record them natively.

## Spikes

When an unknown blocks estimation, the unknown is the first issue. A spike is timeboxed, produces a decision or an answer rather than shipped behavior, and is titled and scoped as research. Expect to discard its code.

## Post-split check

- Both halves smaller, each standing alone. One real child plus a trivial leftover means the seam is wrong.
- Each child passes "can a user or operator do something new" on its own.
- Each child passes the readiness gate in [issue-rules.md](issue-rules.md) without reading the umbrella.
- The cold-read gate runs once on the umbrella or the largest child, not on every child (see [cold-read.md](cold-read.md)).

## Mechanics

Set every relationship natively and at creation. Create the umbrella first and read its number back, then each child already linked:

```bash
gh issue create --repo <owner>/<repo> --title "<umbrella>" --body-file <scratch>/umbrella.md
gh issue create --repo <owner>/<repo> --title "<child A>" --body-file <scratch>/a.md --parent 100
gh issue create --repo <owner>/<repo> --title "<child B>" --body-file <scratch>/b.md --parent 100 --blocked-by 101
```

- `--parent` takes one issue number or URL. `--blocked-by` and `--blocking` take comma-separated numbers or URLs. A child can only be blocked by an issue that already exists, so create the umbrella and then the skeleton first.
- For existing issues use `gh issue edit` with `--parent`, `--add-sub-issue`, `--add-blocked-by`, `--add-blocking` and the matching `--remove-*` flags.
- These flags need `gh` 2.94 or newer. GitHub.com supports them; GitHub Enterprise Server needs 3.17 or newer for sub-issues and 3.19 or newer for blocking.
- Fallback for an older `gh` on a platform that has sub-issues: attach through the REST endpoint (`POST repos/<owner>/<repo>/issues/<umbrella>/sub_issues` with the child's numeric `sub_issue_id`) and record dependencies as `Depends on #<n>` prose.
- Below GHES 3.17 there is no native relationship. List the children in the umbrella body, record dependencies as prose, and say the platform predates sub-issues.

Verify after creating: the umbrella shows its sub-issues and the blocks landed.

## Subagent briefs

`--brief` writes the prompt for a subagent or another agent session. Nothing is filed. A brief is the agent's entire context, so it follows the issue rules with these additions.

Every brief states:

- **Objective**, as an outcome, with the reason it matters.
- **Output format.** What to return and where. Prefer writing results to a file and returning a short reference over returning bulk text.
- **Tools and sources.** Which to use, and which not to.
- **Boundaries.** What is in scope, what is not, what must not be touched.
- **Verification.** The check that proves the work, runnable by the agent.
- **Decisions already made.** Inline them. Implicit decisions are what conflict between agents.
- **Stop and flag.** What to report instead of guessing.

Handoff hygiene:

- Pass artifacts (a diff, a file, a test) rather than a long transcript. Escalating work is cheapest and strongest when the next agent gets the code state plus a short brief.
- Keep writes single-threaded per area. Additional agents add analysis or review, not parallel edits to the same files.
- Review in a fresh context. A reviewer that did not write the code finds more.
- Restate critical constraints after any long run or compaction. Put must-survive constraints in a file the agent re-reads.
- Tell the agent to read what matters by name. Do not rely on links or on it discovering a document.
- Tell the agent when not to act: if the work is already done, do nothing and say so.
