# Workflow

Paths in this file are relative to the skill directory (the one holding SKILL.md).

## Agent compatibility

The workflow is written for Claude Code. On other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the `Invocation arguments` line in the Arguments section of SKILL.md is empty or shows the unreplaced placeholder, take the description, issue reference and flags from the user's request |
| AskUserQuestion | Ask the same question in plain text with the same options and wait for the answer. If you cannot wait (headless run, forked subagent), do not guess: continue with the question recorded under Open items, produce the draft only, and do not file |
| Subagent tool (Agent) | Used only for the cold-read review. Without one, follow the inline fallback in [cold-read.md](cold-read.md) |
| Parallel subagents | Not used. The cold-read review is one reviewer |
| `gh` CLI | Without `gh` or without auth, produce the draft only and say so. Never print commands the user must run unless asked |
| Temp files | Create one scratch directory with `mktemp -d` and put the body file there. Remove it when the task ends |
| `context: fork` | Not used |

Codex note: if the sandbox blocks a `gh` call, request escalation with a short reason, one plain command at a time.

## Arguments

Parse from the invocation arguments, or from the user's request when they are empty.

| Flag | Default | Purpose |
| :-- | :-- | :-- |
| (positional) | none | A description or pasted context to turn into an issue, or an issue URL or number to improve |
| `--draft` | off | Produce the draft and stop. Never touch GitHub |
| `--file` | off | The user already authorized filing. After the checks pass, file without waiting for a go-ahead. Still show the final text and the created URLs |
| `--brief` | off | Write a subagent brief instead of an issue. Nothing is filed |
| `--cold-read` | auto | Force the cold-read review even below the threshold |
| `--no-cold-read` | auto | Skip the cold-read review. The self-check still runs |

## Step 1: detect the mode and read the repository

Pick the mode from what the user gave:

- A description, pasted context or feature idea with no number: **create**.
- An issue URL or number, or "fix", "tighten" or "make this agent-ready": **improve**.
- "split", "break this down", or an issue that fails the split tells in [splitting-and-handoffs.md](splitting-and-handoffs.md): **split**.
- `--brief`, or a request to brief, delegate to or instruct a subagent: **brief**.

If it could be two modes, ask one short question.

Then read the repository's own conventions once and reuse them:

```bash
gh --version
gh repo view --json nameWithOwner,defaultBranchRef,issueTemplates
git log --oneline -40
```

Settle these before drafting:

- **Templates and forms.** Read any issue template or form under `.github/ISSUE_TEMPLATE/` and its `config.yml`. Template handling is in [templates-and-forms.md](templates-and-forms.md); read it now if one exists.
- **Title convention.** Take types and scopes from recent commit and issue titles and any commitlint config. Squash merges often turn the title into the commit subject.
- **Agent instruction files.** Read the root `AGENTS.md` or `CLAUDE.md` and any file they import. These already hold the repo-wide rules, so the issue must not repeat them (see [issue-rules.md](issue-rules.md), Constraints).
- **Verification entry points.** Find the lint, test and build commands (`package.json` scripts, Makefile, contributing guide) so outcomes can name a real check.
- **Relationship support.** Native sub-issues and blocking need `gh` 2.94 or newer; on GitHub Enterprise Server, 3.17 or newer for sub-issues and 3.19 or newer for blocking. Fallbacks are in [splitting-and-handoffs.md](splitting-and-handoffs.md).

Repo conventions in `CLAUDE.md`, `AGENTS.md` or a contributing guide win over this skill's defaults wherever they overlap.

## Step 2: interview, then research and verify

### Interview

Agents rarely ask for what is missing, so the author must. Ask a few questions only when the answer changes the work:

- The observable behavior wanted, and what must not change.
- What failure looks like, including the error and empty states.
- Locked decisions versus the implementer's call.
- Anything hard to reverse: public interface, schema, migration, published version.
- Approaches already tried and rejected, and why.

Do not ask what the repo answers. Do not ask more than four questions at once. If the request already answers them, skip the interview.

### Research and verify

Read the repository enough to scope and slice correctly. Then turn every fact you intend to put in the issue into a checked claim:

- **Premise.** Confirm the problem still exists on the default branch. If it is already fixed or only partly present, say so and stop or reshape the issue. Do not file a stale premise.
- **Duplicates.** Search open and recently closed issues and PRs (`gh issue list --search`, `gh pr list --search`). Link or stop if the work exists.
- **Anchors.** Every file, symbol or pattern you name must exist (grep it). Never write line numbers.
- **Reproduction.** For a bug, run the repro and record what you observed. A bug you cannot reproduce is a research task; title and scope it that way.
- **Cause.** A root cause goes in only if an executed check supports it. Otherwise it is a labelled hypothesis or it stays out.
- **Commands.** Run the check commands you plan to name, or confirm they exist.

Facts that stay unchecked go to the **Open items** list shown to the user. They do not go in the issue as facts.

## Step 3: one issue or several

If the work has more than one deliverable, or trips a split tell, read [splitting-and-handoffs.md](splitting-and-handoffs.md) and propose the slice set before writing any body. Splitting changes everything downstream, so resolve it first.

## Step 4: draft

Read [issue-rules.md](issue-rules.md) and write the title and body. If the repo ships a template, follow [templates-and-forms.md](templates-and-forms.md). For `--brief`, use the brief shape in [splitting-and-handoffs.md](splitting-and-handoffs.md).

## Step 5: self-check and cold-read gate

Always run the self-check from [cold-read.md](cold-read.md). Then evaluate the gate conditions there. Run the review when any condition holds or `--cold-read` was passed, skip it for `--no-cold-read`. Apply only the findings the gate rules allow.

## Step 6: writing pass

Read [writing-pass.md](writing-pass.md) and apply it to every title and body before showing anything.

## Step 7: show, approve, file

Show the user, in one message:

- The full title and body of each issue, exactly as it would be filed.
- Open items and assumptions (unverified facts, questions unanswered).
- The gate result: self-check passed, cold-read run or skipped and why.
- For a split, the slice set with the dependency order.

Then wait for an explicit go-ahead. `--draft` stops here. `--file` proceeds after the checks pass.

To file:

- Pass `--repo <owner>/<repo>` on every mutating call. Without it, a command runs against the repo in the current directory.
- Write each body to a file in the scratch directory and pass `--body-file`, which keeps the exact markdown.
- Set relationships at creation (`--parent`, `--blocked-by`, `--blocking`). Create the umbrella first, read its number back, then each child already linked.
- Do not set labels, issue types or assignees unless the user asked or the repo's template or contributing guide requires it. Name what you are about to set and why.

```bash
gh issue create --repo <owner>/<repo> --title "<title>" --body-file <scratch>/issue.md
gh issue edit <number> --repo <owner>/<repo> --title "<title>" --body-file <scratch>/issue.md
```

## Step 8: read back

Read numbers and URLs from the command output rather than assuming them. After a split, confirm the umbrella lists its sub-issues and that each blocking relationship landed. Remove the scratch directory.

## Output

- The issue text and Open items as above, then the created URLs.
- State plainly what was skipped (cold-read, interview, filing) and why.
- Do not summarize the rules back to the user.

## Hard stops

- The premise is false or already fixed: report and stop.
- The work already exists as an issue or PR: link it and stop.
- A required template field cannot be filled truthfully and the user is unreachable: draft only.
- No `gh` or no auth: draft only.
