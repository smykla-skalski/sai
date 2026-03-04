# Implementation Plan Template

## Contents

- [Structure](#structure)
- [Decision Trees](#decision-trees)
  - [Command Discovery](#command-discovery)
  - [Git Remote Selection](#git-remote-selection)
  - [Branch Name Generation](#branch-name-generation)
- [Phase Guidelines](#phase-guidelines)
- [Technical Context Guidelines](#technical-context-guidelines)

Use this template when constructing implementation plans in Phase 4.

## Structure

````markdown
# Implementation Spec: {Action-oriented summary, 5-10 words}

## Workflow Commands

| Action     | Command                  |
|:-----------|:-------------------------|
| Lint       | `{exact command}`        |
| Fix/Format | `{exact command or N/A}` |
| Test       | `{exact command}`        |

## Git Configuration

| Setting        | Value                          |
|:---------------|:-------------------------------|
| Base Branch    | `{main or master}`             |
| Feature Branch | `{type/slug}`                  |
| Push Remote    | `{origin or upstream}`         |
| Worktree Path  | `{path or N/A if no worktree}` |

## Progress Tracker

- [x] Investigation: {Brief outcome}
- [ ] **NEXT**: {Specific first action}
- [ ] {Subsequent step}
- [ ] {Final cleanup step}

**Blockers/Deviations:** None

## Technical Context

{Problem/solution context, rationale, file paths (repo-relative), key functions as pseudocode, architectural decisions, assumptions needing verification}

## Execution Plan

### Phase 1: Setup & {Name}

- [ ] Setup: Create worktree at `{worktree_path}` with branch `{feature_branch}` (or checkout branch if no worktree)
- [ ] {Step}: {Action with specific file paths}
- [ ] {Step}: {Action}
- [ ] Verify: {Run tests/lint, expected outcome}

### Phase N: Cleanup & PR

- [ ] Final verification: Run full test suite
- [ ] Commit remaining changes
- [ ] Push to remote
- [ ] Create PR (if requested)
- [ ] Cleanup: Run `/clean-gone` to remove merged branches and worktrees

## Open Questions

- {Questions that arose but weren't blockers}

## Files to Modify

- `{repo/relative/path}` — {brief reason}
````

## Decision Trees

### Command Discovery

```text
Makefile exists?
├─ YES → parse targets (lint, test, format, check)
└─ NO  → Taskfile.yml exists?
         ├─ YES → parse tasks (task lint, task test, task fmt)
         └─ NO  → package.json exists?
                  ├─ YES → parse scripts section
                  └─ NO  → .mise.toml exists?
                           ├─ YES → parse [tasks] section
                           └─ NO  → CI config exists?
                                    ├─ YES → extract commands from CI
                                    └─ NO  → AskUserQuestion
```

### Git Remote Selection

```text
upstream remote exists?
├─ YES → use upstream (fork workflow)
└─ NO  → use origin (direct contributor)
```

### Branch Name Generation

```text
Task mentions:
├─ "add", "implement", "new", "create"  → feat/{slug}
├─ "fix", "resolve", "patch", "bug"     → fix/{slug}
├─ "update", "upgrade", "deps", "bump"  → chore/{slug}
├─ "document", "readme", "guide"        → docs/{slug}
├─ "test", "spec", "coverage"           → test/{slug}
├─ "refactor", "reorganize", "clean"    → refactor/{slug}
├─ "ci", "pipeline", "workflow"         → ci/{slug}
└─ unclear                              → AskUserQuestion
```

## Phase Guidelines

- **3-7 phases total**, each with 3-7 steps
- **≤10 files per phase**
- **Phase 1 must start with**: worktree/branch setup step
- **Every phase ends with**: verification step (run tests/lint with expected outcome)
- **Final phase must include**: cleanup step using `/clean-gone`
- **Progress Tracker**: Exactly one `**NEXT**:` pointer, max 20 lines

## Technical Context Guidelines

- Use pseudocode for key functions, not verbatim code
- Include repo-relative file paths, never absolute
- Document rationale for architectural decisions
- Note assumptions that need verification
- Goal: a fresh executor session can start immediately without re-investigation
