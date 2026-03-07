# Check ID mapping

Maps every JSON check name emitted by validation scripts to its checklist criterion and source script. Use this to identify which checks are automated and which require manual evaluation.

## Table of contents

- [Automated checks](#automated-checks)
- [Manual checks](#manual-checks)
- [Signal IDs](#signal-ids)

## Automated checks

| Check ID | Tier | Script | Description |
| :-- | :-- | :-- | :-- |
| FM-name-present | C4 | validate.py | Name field exists |
| FM-name-format | C4 | validate.py | Name is valid kebab-case |
| FM-name-matches-dir | C4 | validate.py | Name matches parent directory |
| FM-desc-present | C1 | validate.py | Description field exists |
| FM-desc-trigger | C1 | validate.py | Description has trigger phrases (skipped if DMI) |
| FM-desc-length | I25 | validate.py | Description under 1,024 chars |
| FM-desc-voice | P5 | validate.py | Description uses third-person form |
| FM-tools-present | I9 | validate.py | allowed-tools field exists |
| FM-invocable-present | - | validate.py | user-invocable field exists |
| CF-tools-usage | I16 | check-config.py | Listed tools are actually used in body |
| CF-side-effect | I17 | check-config.py | Side-effect skills have DMI guard |
| CF-state-xdg | I11 | check-config.py | Persistent state uses XDG paths |
| BP-example-tags | I26 | check-best-practices.py | Example tags present in SKILL.md body |
| BP-over-prompting | I27 | check-best-practices.py | Aggressive all-caps prompting avoided |
| BP-negative-instr-info | P11 | check-best-practices.py | Negative instruction density signal |
| BP-error-section-info | P12 | check-best-practices.py | Error section heading presence signal |
| BP-scope-boundary-info | P13 | check-best-practices.py | Scope-boundary language signal |
| BP-constraint-refresh-info | P14 | check-best-practices.py | Constraint refresh signal for 4+ phases |
| CT-no-grading | C6 | check-content.py | No scoring rubric patterns |
| CT-no-secrets | C7 | check-content.py | No secrets in skill files |
| CT-no-echo | I13 | check-content.py | No useless echo wrapping |
| CT-long-prose | - | check-content.py | No prose lines over 300 chars |
| FR-resolves | C3 | check-file-refs.py | File references resolve to actual files |
| FR-link-format | I15 | check-file-refs.py | References use markdown links |
| FR-mentions-file | P3 | check-file-refs.py | SKILL.md mentions all bundled resources |
| FR-no-backslash | P6 | check-file-refs.py | No backslash paths |
| FR-no-disallowed | - | check-file-refs.py | No disallowed path patterns |
| FR-one-level | - | check-file-refs.py | References don't cross-reference other refs |
| SD-invocation-prefix | I6 | check-scripts-dir.py | Scripts use CLAUDE_SKILL_DIR prefix |
| SD-no-bash | I6 | check-scripts-dir.py | No bash/python3 prefix on invocations |
| SD-executable | I12 | check-scripts-dir.py | Entrypoints have executable bit |
| SD-legacy-bash-info | P16 | check-scripts-dir.py | Top-level legacy .sh scripts signal |
| RF-body-lines | C2 | check-references.py | Body under 500 lines |
| RF-body-chars | I24 | check-references.py | Body under 20,000 chars |
| RF-phase-numbering | I14 | check-references.py | Consistent phase numbering |
| RF-long-ref-toc | P1 | check-references.py | Long references have TOC |
| RF-dup-codeblocks-info | P8 | check-references.py | No duplicated code blocks |
| RF-dup-tables-info | P15 | check-references.py | No duplicated markdown tables |
| PP-* | I18 | check-preprocessing.py | Preprocessing directive hygiene (8 sub-checks) |
| RG-gate-present | I19 | check-read-gates.py | References have explicit read gates |
| RG-passive | I19 | check-read-gates.py | No passive mentions before gate |
| RG-orphan | I19 | check-read-gates.py | No files missing from SKILL.md |
| RG-dead | I19 | check-read-gates.py | No dead bundled-only listings |
| RG-use-order | I19 | check-read-gates.py | No use-before-gate ordering |
| RG-purpose | I19 | check-read-gates.py | Gates explain why |
| RG-flow | I19 | check-read-gates.py | Multi-flow gates per flow |
| CL-aggregate | I20 | check-lint.py | Scripts pass static analysis |
| AQ-declaration | I21 | check-ask-user.py | AskUserQuestion in allowed-tools iff used |
| AQ-implicit | I21 | check-ask-user.py | Implicit user interaction matches declaration |
| AQ-required-arg | I21 | check-ask-user.py | Required args have ask/fallback |
| AQ-spawned-agent | I21 | check-ask-user.py | No AUQ in spawned agent sections |
| AQ-option-structure | I21 | check-ask-user.py | Usage sites have options documented |
| AQ-destructive | I21 | check-ask-user.py | Destructive skills have confirmation |
| AQ-ambiguity | I21 | check-ask-user.py | Ambiguous situations have resolution |
| AQ-multiselect | I21 | check-ask-user.py | multiSelect has grouping guidance |
| AQ-wizard | I21 | check-ask-user.py | Wizard patterns have loop termination |
| FC-hint-doc | I22 | check-flag-coverage.py | Hint flags appear in Arguments |
| FC-doc-hint | I22 | check-flag-coverage.py | Documented flags appear in hint |
| FC-doc-workflow | I22 | check-flag-coverage.py | Documented flags referenced in workflow |
| FC-example-flags | I28 | check-flag-coverage.py | Example invocations cover documented flags |
| HK-events | I23 | check-hooks.py | Valid event names |
| HK-structure | I23 | check-hooks.py | Correct matcher structure |
| HK-type | I23 | check-hooks.py | Hook type and command present |
| HK-resolve | I23 | check-hooks.py | Command paths resolve |
| HK-exec | I23 | check-hooks.py | Scripts are executable |
| HK-duplicate | I23 | check-hooks.py | No duplicate event+matcher pairs |
| HK-stdin | I23 | check-hooks.py | Scripts parse stdin JSON |
| HK-loop | I23 | check-hooks.py | Stop hooks check stop_hook_active |
| HK-exit | I23 | check-hooks.py | PreToolUse avoids exit 2 |
| HK-perm | I23 | check-hooks.py | PostToolUse avoids permissionDecision |
| HK-prefix | I23 | check-hooks.py | Consistent error code prefix |
| HK-suggestion-info | P10 | check-hooks.py | Hooks recommended for side-effect skills |
| FK-recommendation-info | P9 | check-fork-candidate.py | Fork candidate analysis |

## Manual checks

These checks require human or agent evaluation - no automated script covers them.

| Tier | Description |
| :-- | :-- |
| C5 | No generic filler content Claude already knows |
| I1 | Imperative form throughout |
| I2 | Progressive disclosure for complex skills |
| I3 | Concrete input/output examples |
| I4 | No prose duplication between SKILL.md and references |
| I5 | Explicit read directives for workflow-critical references |
| I7 | Appropriate degrees of freedom |
| I8 | Feedback loops for quality-critical steps |
| I10 | Consistent terminology |
| I29 | WHY rationale on non-obvious constraints |
| P2 | One default + one escape hatch |
| P4 | No time-sensitive info without deprecation plan |
| P7 | Scripts handle errors, no magic constants |
| P17 | Body section order follows recommended flow |

## Signal IDs

Fork candidate signals emitted by `check-fork-candidate.py`:

| Signal | Type | Description |
| :-- | :-- | :-- |
| FK-P1 | positive | High phase count |
| FK-P2 | positive | Structured output format |
| FK-P3 | positive | Data gathering phases |
| FK-P4 | positive | Manual subagent usage |
| FK-P5 | positive | Heavy reference loading |
| FK-P6 | positive | Self-contained inputs |
| FK-B1 | blocker | Already forked |
| FK-B2 | blocker | Conversation-dependent |
| FK-B3 | blocker | Tiny skill |
| FK-B4 | blocker | Background knowledge required |
| FK-N1 | negative | Side-effect skill |
| FK-N2 | negative | AskUserQuestion actively used |
| FK-N3 | negative | Write/Edit actively used |
