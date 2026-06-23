# staff-code-review

Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, observability, security, and cross-team impact.

## Features

- **Triage pass** — six mental model questions (Tanya Reilly) before line-by-line review
- **Codebase research** — caller counts, existing patterns, test coverage, git history, ADR context
- **Parallel deep review with council personas** — seven specialized agents, each routed to a council persona that owns the lens (Evans for Architecture, Hebert for Reliability, Willison for Security, **Gregg for Performance**, Siracusa for Backward Compat, antirez for Conventions, tef for Dead Code). Falls back to `general-purpose` if the council plugin is not installed.
- **Two adversaries** — a **Code Adversary** runs alongside the seven personas and red-teams the change itself, assuming it's broken and hunting for the concrete bug with a failing input. A **Findings Adversary** runs after synthesis and red-teams the findings, killing false positives, right-sizing inflated severities, and dropping hallucinated locations that would break GitHub posting. Skip both with `--no-adversary`.
- **Translation pass** — persona-format reviews are converted to conventional comments without losing technical content
- **Conventional comments** — `blocking:`, `issue:`, `question:`, `suggestion:`, `thought:`, `nit:`, `praise:`
- **Design doc detection** — flags PRs that should have had an RFC/design doc first

## Optional dependency

For maximum review quality, install the [council](../council/) plugin alongside this one. Without it, Pass 2 still runs — it just uses generic `general-purpose` agents instead of opinionated personas.

## Usage

Triggers on: "review this PR", "review these changes", "staff review", "thorough code review", sharing a GitHub PR URL for review.

Also user-invocable:

```
/staff-code-review <PR URL> [--no-adversary]
/staff-code-review <file path> [--no-adversary]
```

## Reference Material

- `agents/code-adversary.md` — red-teams the code change (runs in Pass 2)
- `agents/review-adversary.md` — red-teams the synthesized findings (runs after synthesis)
- `skills/staff-code-review/references/review-dimensions.md` — detailed checklists for each review dimension
