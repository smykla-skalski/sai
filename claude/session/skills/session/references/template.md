# Session Handover Template

Use this template to structure the handover document. Strip these comments before output. Omit any section that has no content — do not leave empty headings.

```markdown
# Session Handover: {One-line summary — "Goal: status" format}

## Skill Activation

**MANDATORY FIRST ACTION**: Before proceeding with ANY task, you MUST use the Skill tool to learn the following skills:

**Required (used in previous session):**
- `{skill-name}` — {brief context why it was used}

**Recommended (requested but not yet learned):**
- `{skill-name}` — {why needed}

## Original Request

> {user's exact prompt verbatim — preserve formatting, newlines, code blocks}

## Pending Todos

- [ ] {todo item — in_progress}
- [ ] {todo item — pending}

## Failed Approaches

- Tried {approach}: {failure reason} → {lesson/elimination}

## Environment Constraints

- {Tool}: {version/constraint} — {why it matters}

## Architectural Decisions

- Chose {X} over {Y}: {trade-offs, constraints}

## Investigation Findings

**Files:** `path/file.ext` — {role}
**Functions:** `func(params) -> type`: {behavior}
**Data Flow:** Input → Processing → Output

## Current State

**Stopped At:** {precise stopping point}
**Blockers:** None | {blocker}
**Open Questions:** {questions needing answers}

## Next Steps

1. {Action with file path}
2. {Next action}
3. {Verification}
```

## Section Rules

| Section                 | Include When                           | Omit When                   |
|:------------------------|:---------------------------------------|:----------------------------|
| Skill Activation        | Skills were used or mentioned          | No skills at all            |
| Original Request        | Work stems from a specific user prompt | Continuation/follow-up work |
| Pending Todos           | Incomplete todos exist                 | No todos or all completed   |
| Failed Approaches       | Any failed attempts recorded           | No failed attempts          |
| Environment Constraints | Non-obvious constraints discovered     | None discovered             |
| Architectural Decisions | Design choices were made               | No choices made             |
| Investigation Findings  | Key files/functions documented         | No investigation done       |
| Current State           | Always                                 | Never omit                  |
| Next Steps              | Always                                 | Never omit                  |
