---
name: staff-resume
description: Build and refine staff-level engineering resumes through interactive coaching, research-backed best practices, and per-job tailoring. Use when building, improving, or tailoring a resume for Staff/Principal engineer roles.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. No scripts needed. Web search and fetch are optional (fresh research and job postings); without network access it falls back to the bundled reference and pasted text.
argument-hint: "<resume-path> [--job-url URL] [--mode coach|tailor|full]"
user-invocable: true
allowed-tools: AskUserQuestion Edit Glob Read WebFetch WebSearch Write
context: fork
agent: general-purpose
metadata:
  short-description: Coach and tailor staff resumes
---


# Staff Resume Builder



## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Scope
4. Phase 1: Load Context
5. Phase 2: Research Best Practices
6. Phase 3: Gap Analysis
7. Phase 4: Interactive Coaching Session
8. Phase 5: Job-Specific Tailoring (if job-url provided)
9. Phase 6: Generate Output
10. Keyword Coverage
11. Key Customizations Made
12. Interview Talking Points
13. Honest Assessment
14. Phase 7: Final Review
15. Error Handling
16. Sources

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
