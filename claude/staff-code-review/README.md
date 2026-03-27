# staff-code-review

Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, observability, security, and cross-team impact.

## Features

- **Triage pass** — six mental model questions (Tanya Reilly) before line-by-line review
- **Codebase research** — caller counts, existing patterns, test coverage, git history, ADR context
- **Parallel deep review** — three specialized agents: Architecture & Design, Reliability & Operations, Security & Dependencies
- **Conventional comments** — `blocking:`, `issue:`, `question:`, `suggestion:`, `thought:`, `nit:`, `praise:`
- **Design doc detection** — flags PRs that should have had an RFC/design doc first

## Usage

Triggers on: "review this PR", "review these changes", "staff review", "thorough code review", sharing a GitHub PR URL for review.

Also user-invocable:

```
/staff-code-review <PR URL>
/staff-code-review <file path>
```

## Reference Material

- `skills/staff-code-review/references/review-dimensions.md` — detailed checklists for each review dimension
