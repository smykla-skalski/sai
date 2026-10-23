# Issue rules

How one issue is shaped. The reader is a coding agent that has none of the author's context, will follow what is written, and will not reliably ask. The test: could someone who never spoke to the author build this and know when they are done, from the issue alone?

Why each rule exists, and how strong the evidence is, is in [evidence.md](evidence.md).

## Title

`type(scope): summary`, using the repo's own types and scopes.

- Imperative, present tense, lowercase after the colon, no trailing period, under 70 characters.
- Name a user-visible capability or a defect and its symptom, not a layer or a bare noun. "fix(auth): reject expired refresh tokens" is a title. "fix(auth): auth bug" is not.
- Lead with the verb and object so the title survives truncation. Prefer a result verb (add, remove, stop, prevent, allow) over a layer verb (update, improve, handle, refactor).
- One deliverable per title. A summary that needs "and", "or" or a comma to join a second clause is two issues.
- Pick the type from the change class, not the diff size or file type.
- Use a scope the repo already names. Flag a coined scope to the user.

## Body

Five sections. Omit any that is empty. A one-line fix may need only Problem and Expected outcome.

```markdown
## Problem

2 to 4 sentences. User-visible impact and why it matters. No unverified solution.

## Expected outcome

- Observable behavior. Check: `<command>`, or "given X, returns Y".
- Existing behavior preserved. Check: `<suite or command>` stays green.

## Constraints

- Decided: <locked choices>.
- Your call: <choices the implementer may make>.
- Do not: <task-specific prohibitions>.

## Starting points

- Verified: `<path or symbol>`, <one clause on why>. Pattern to copy: `<existing example>`.
- Hypothesis, verified by `<repro or test>`: <cause>.

## Stop and flag

- Stop and report instead of proceeding if: <trigger>.
- No change needed if: <precondition already true on the default branch>.
```

Keep one physical line per paragraph and per bullet.

### Problem

Two to four sentences of prose, present tense, active voice. State what goes wrong or what is missing, for whom, and why it matters.

- No unverified solution. A proposed fix in the problem statement stops the implementer from looking for a better one.
- A cause that an executed check supports may go here or under Starting points, labelled with the check.
- If a reader cannot tell what goes wrong today, the issue is not ready.

### Expected outcome

Observable behavior, one named check per bullet. Each bullet must be passable or failable by someone who never read the issue.

- Name the check: a command, a test, a screenshot to compare, or an example input and output ("given `user@.com`, `isValid` returns false").
- Describe behavior, not mechanism. "Tab moves focus in reading order in every view" passes. "Call the focus helper in the sidebar" does not.
- Prefer outcomes that name the failure they prevent. They survive a rewrite of the implementation.
- Quantify any quality word. "Fast", "simple", "reliable" and "secure" carry a threshold and a way to read it, or they go.
- A criterion must not pin an implementation. If a correct alternative solution would fail the check, rewrite the check.
- A bare "tests pass" is not an outcome. Say which behavior the tests prove and which command runs them.

**Cover the states the change meets.** Before the list is final, add an outcome for each state the change will really hit:

- Empty or first-run: no data, first use, nothing selected.
- Boundary: zero, one, the maximum, one past it, duplicates.
- Invalid or unauthorized input, and each error the change can raise, with what the caller sees.

Leave out a state that cannot occur. Do not leave one out because it was inconvenient to write. Visible tests tend to saturate on the happy path, so the held-out cases are the ones you must name.

**Guard what already works.** When the change sits next to behavior a plausible implementation could break, add one outcome naming the exact suite or command that must stay green: "existing session handling preserved. Check: `make test-auth` stays green". A bare "existing behavior still holds" cannot be verified.

If covering the real states needs more than about six outcomes, treat it as a split signal (a heuristic, not a measured limit).

### Constraints

Task-specific only. Repo-wide rules live elsewhere.

- **Decided versus your call.** A flat list reads as all mandatory or all optional, and the implementer guesses wrong either way. Say which choices the author locked and which are open.
- **Do not.** Task-specific prohibitions: files or areas to leave alone, an interface that must not change, an adjacent issue that covers a nearby concern.
- **Do not restate repo-wide rules.** "No unrelated refactors", "do not edit tests to make them pass" and "stop and flag on a spec and test conflict" belong in the root `AGENTS.md` or `CLAUDE.md`, as three to five short negative lines, and for hard prohibitions in a hook, a read-only test directory or a CI check. If the repo lacks them, tell the user once in Open items; do not paste them into every issue.
- **Name the instance, not the rule.** "The tests in `internal/auth/` are the contract. If they contradict this spec, stop and report." applies a generic rule to this task.
- **Exceptions are explicit.** If the issue must override a repo-wide rule, write "Exception to AGENTS.md rule `<rule>`: <why>". Never leave two layers contradicting each other.
- **Point at files that will not auto-load.** If a path-scoped or nested instruction file matters here, say "read `path/AGENTS.md` first". Files that are not loaded automatically are rarely opened unprompted.

### Starting points

Non-binding pointers that save a real search. This is where verified paths and symbols go.

- Every entry was checked in this session (grep, run, read). Anything unchecked is dropped or moved to Open items.
- Never line numbers. They are stale at the next commit.
- A component or subsystem name is always safe. An exact path is allowed when verified and labelled a starting point that may have moved.
- A precedent to copy ("follow the way `X` does it") beats a paragraph describing the style.
- A cause appears only with its verification: "Hypothesis, verified by `go test ./auth -run TestRefresh`: the refresh path reads the cached expiry".
- No step lists, no function-by-function plan. Pointers say where to look, not what to type.

### Stop and flag

The implementer will not reliably notice that the spec is wrong, so name the triggers.

- **Conflicts.** A stated outcome contradicts an existing test, or the spec is infeasible: stop and report instead of working around it.
- **Missing decisions.** A choice the issue does not make would change the work materially: stop and ask.
- **One-way doors.** Anything expensive or impossible to reverse, such as a published version, a public interface, a destructive migration or a production change: stop and ask, never guess.
- **No change needed if.** Name the precondition that makes the work unnecessary (the behavior already holds on the default branch, the flag already exists). Agents tend to edit even when no change is warranted.

State the signal the implementer should use, for example a final message that begins "Blocked:" with the reason.

## Bug reports

A bug keeps Problem and replaces Expected outcome with:

- `## Reproduction`: an executable repro (a command, a script or a failing test) run from a clean, named state, with the output you observed. Numbered prose steps are a fallback when nothing executable exists.
- `## Expected behavior`
- `## Actual behavior`

Record the environment when it matters and whether this ever worked, since a regression and a never-worked bug send the implementer to different places. A bug without a reproduction is a research task; title and scope it as one. If the report does not supply a detail you need, ask the reporter. A fabricated repro step or environment sends the implementer the wrong way.

## What stays out

- Line numbers, and any path or symbol you did not verify.
- Step-by-step implementation checklists.
- Acceptance checks that only one implementation can pass.
- Repo-wide rules the root instruction file already holds.
- Repo facts the implementer can read in a minute (architecture overviews, restated README).
- Generic "verify your work" or "be careful" lines. Give the done-criterion instead.
- Emphasis shouting (CAPS, "CRITICAL"). If one instruction keeps being skipped, mark that one line.
- The same point in a second section.

Keep the verified, non-discoverable facts: an approach already tried and rejected and why, an external quirk, a hidden coupling. Two sentences, no more.

## Length

There is no word cap. Judge by content: every sentence is a behavior, a constraint, a check, a pointer or a stop trigger. A long issue made of those stays whole. A long issue that is really two deliverables splits. A terse issue can still describe enormous work, so size is judged by the change, using the split tells in [splitting-and-handoffs.md](splitting-and-handoffs.md).

## Model notes

These come from vendor guidance and drift with model versions; re-test on the model that will implement.

- Strong recent models do best with the complete specification up front. Do not plan to add requirements mid-task.
- They tend to add scope, tests and files nobody asked for. A Do-not line or a non-goal in Constraints is the countermeasure.
- Do not add procedural "double-check" instructions. Supply the criterion that proves the work and let the model verify.

## Readiness gate

Before showing a draft, answer yes to all:

- Could someone who never spoke to the author build this and know when they are done?
- Does every outcome name a check?
- Is every pointer verified, and every unverified fact in Open items?
- Is each locked choice marked, and each one-way door guarded?
- Is it one deliverable?

If not, the missing piece is an unstated outcome or constraint. Add that, not prose.

## Example

```markdown
fix(auth): reject expired refresh tokens

## Problem

A refresh token past its expiry is still exchanged for a new access token. A leaked, old token keeps working until the server restarts.

## Expected outcome

- An expired refresh token returns 401 with error code `token_expired`. Check: `go test ./internal/auth -run TestRefreshExpired`.
- A valid refresh token still returns 200 with a new access token. Check: `go test ./internal/auth -run TestRefreshValid` stays green.
- Existing session handling is preserved. Check: `make test-auth` stays green.
- A token expiring exactly now is treated as expired.

## Constraints

- Decided: the response shape and error code in the first outcome.
- Your call: where the expiry check lives.
- Do not: change the token format or the database schema.

## Starting points

- Verified: `internal/auth/refresh.go` handles the exchange. Pattern to copy: how `internal/auth/access.go` rejects expired access tokens.

## Stop and flag

- Stop and report if the existing tests assume expired refresh tokens succeed.
- No change needed if `TestRefreshExpired` already exists and passes on the default branch.
```
