# Review checklist

Binary checklist for evaluating Claude Code skill definitions. Each check is pass/fail.

The NDJSON column shows check IDs emitted by validation scripts in JSON output. IDs follow `{PREFIX}-{slug}` format (e.g., `FM-name-present`). Wildcard entries like `PP-*` represent multiple sub-checks. Manual checks show `-`.

## Table of contents

- [Critical checks](#critical-checks)
  - [Frontmatter validation](#frontmatter-validation)
  - [Content safety](#content-safety)
- [Important checks](#important-checks)
  - [Manual checks](#manual-checks)
  - [Script and file hygiene](#script-and-file-hygiene)
  - [Tool and safety declarations](#tool-and-safety-declarations)
  - [Automated: preprocessing (I18)](#automated-preprocessing-i18)
  - [Automated: read gates (I19)](#automated-read-gates-i19)
  - [Automated: script lint (I20)](#automated-script-lint-i20)
  - [Automated: AskUserQuestion (I21)](#automated-askuserquestion-i21)
  - [Automated: flag coverage (I22)](#automated-flag-coverage-i22)
  - [Automated: hooks (I23)](#automated-hooks-i23)
  - [Automated: size checks (I24-I25)](#automated-size-checks-i24-i25)
- [Polish checks](#polish-checks)
  - [Reference file quality](#reference-file-quality)
  - [Design quality](#design-quality)
  - [Fork candidate analysis (P9)](#fork-candidate-analysis-p9)
  - [Hook guardrails (P10)](#hook-guardrails-p10)

---

## Critical checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements from the Agent Skills specification and Anthropic best practices.

| ID | NDJSON | Check | Source |
| :-- | :-- | :-- | :-- |
| C1 | FM-desc-present, FM-desc-trigger | Description includes what the skill does AND when-to-use trigger phrases (skip trigger check if `disable-model-invocation: true`) | Anthropic Best Practices, Agent Skills Spec |
| C2 | RF-body-lines | SKILL.md body under 500 lines (excluding frontmatter); see I24 for character limit | Agent Skills Spec, Claude Code Docs |
| C3 | FR-resolves | All file references in SKILL.md resolve to actual files | Agent Skills Spec |
| C4 | FM-name-* | Name field valid format and matches directory name | Agent Skills Spec |
| C5 | - | No generic content Claude already knows ("write clean code", "handle errors") | Anthropic skill-creator, Context Engineering |
| C6 | CT-no-grading | Not structured as a scoring rubric with points, weights, or letter grades | Anthropic Best Practices |
| C7 | CT-no-secrets | No secrets or credentials in skill files (API keys, tokens, private keys) | Anthropic Best Practices |

### How to evaluate

#### Frontmatter validation

Read the SKILL.md frontmatter first. Confirm the `description` field contains both a functional summary and at least one trigger phrase (e.g., "Use when..."). Exception: if `disable-model-invocation: true` is set, trigger phrases are not required since the skill cannot be auto-invoked. Count body lines excluding the YAML frontmatter block and verify < 500. Verify the `name` field is kebab-case and matches the parent directory name exactly.

#### Content safety

**C3 (file refs):** Grep for file paths referenced in the body and confirm each resolves relative to the skill directory.

**C5 (filler):** Scan for filler instructions that restate LLM defaults - if removing a sentence changes nothing about behavior, it fails C5.

**C6 (grading):** Scan for grading-style patterns: point values, percentage weights, letter-grade scales, scoring rubric keywords. If two or more signals appear, the skill is structured as a scoring rubric rather than an imperative workflow - it fails C6.

**C7 (secrets):** Scan SKILL.md and all bundled files for secrets: AWS access keys (`AKIA...`), API keys (`sk-...`, `api_key=`), bearer tokens, private key blocks (`-----BEGIN...KEY-----`), inline passwords or tokens. Any match fails C7.

---

## Important checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect skill quality.

| ID | NDJSON | Check | Source |
| :-- | :-- | :-- | :-- |
| I1 | - | Imperative form throughout ("Parse input" not "You should parse") | Anthropic skill-creator |
| I2 | - | Progressive disclosure - complex skills use references/ for details | Agent Skills Spec, Context Engineering |
| I3 | - | Concrete examples showing inputs → outputs | Anthropic Best Practices, Context Engineering |
| I4 | - | No prose duplication between SKILL.md and references (code blocks OK) | Anthropic skill-creator |
| I5 | - | Explicit read directives for workflow-critical references ("Read X before phase Y") | Empirical finding |
| I6 | SD-invocation-prefix, SD-no-bash | Scripts invoked directly via `"${CLAUDE_SKILL_DIR}/scripts/..."`, never `bash` prefix | SAI Convention |
| I7 | - | Appropriate degrees of freedom (guardrails match task fragility) | Anthropic Best Practices |
| I8 | - | Feedback loops for quality-critical steps | Anthropic Best Practices |
| I9 | FM-tools-present | allowed-tools not over-broad (only tools actually needed) | Anthropic Best Practices |
| I10 | - | Consistent terminology (same concept = same word) | Anthropic Best Practices |
| I11 | CF-state-xdg | Persistent state uses XDG paths, not relative or cache-relative paths | SAI Convention, Plugin Cache Architecture |
| I12 | SD-executable | All runnable entrypoints in scripts/ have executable bit set | SAI Convention |
| I13 | CT-no-echo | No useless echo wrapping literals (`$(echo "text")`, not `$(echo "${VAR}")`) | ShellCheck SC2116 |
| I14 | RF-phase-numbering | Consistent phase/step numbering between SKILL.md and references | Anthropic Best Practices |
| I15 | FR-link-format | Reference file paths use markdown links, not inline code, for progressive disclosure | Agent Skills Spec, Progressive Disclosure |
| I16 | CF-tools-usage | allowed-tools only lists tools actually referenced in the skill body | Anthropic Best Practices |
| I17 | CF-side-effect | Side-effect skills have `disable-model-invocation: true` in frontmatter | Anthropic Best Practices |
| I18 | PP-* | Preprocessing directives follow best practices (error handling, output limits, no secrets, no mutations, no slow/hanging commands) | Claude Code Docs, Community Best Practices |
| I19 | RG-* | Reference read gate analysis: gate presence, passive mentions, orphan files, dead bundled-only listings, use-before-gate ordering, gate purpose text, multi-flow coverage | Empirical finding, I5 automated complement |
| I20 | CL-aggregate | Bundled scripts pass static analysis (shellcheck for .sh, ruff for .py; critical/medium severity) | SAI Script Audit, ShellCheck, Ruff |
| I21 | AQ-* | AskUserQuestion declared when body implies user interaction, not used in spawned agents, required args have ask-or-fallback | SAI Convention, Skill Authoring Guide |
| I22 | FC-* | Flag coverage: every --flag in argument-hint documented in Arguments, every documented flag in argument-hint, every documented flag referenced in workflow | SAI Convention |
| I23 | HK-* | Hooks configuration: valid events, correct structure, scripts exist/executable, hook patterns (stdin parsing, stop guard, exit codes, error prefix consistency) | SAI Convention, Skill Authoring Guide |
| I24 | RF-body-chars | SKILL.md body under 20,000 characters (roughly 5,000 tokens) | Skills Research, Context Engineering |
| I25 | FM-desc-length | Description field under 1,024 characters | Agent Skills Spec |

### How to evaluate

#### Manual checks

**I1 (imperative form):** Scan the SKILL.md body for second-person phrasing ("you should", "you can") - every instruction should be imperative.

**I2 (progressive disclosure):** Check whether the SKILL.md exceeds ~150 lines; if so, verify that detail-heavy sections (examples, search patterns, rubrics) are extracted to references/.

**I3 (examples):** Look for at least one concrete input -> output example.

**I4 (no duplication):** Diff the SKILL.md against each reference file for duplicated paragraphs or tables.

**I5 (read directives):** Verify that any reference file used during execution has an explicit "Read references/X before Phase N" directive.

**I7 (degrees of freedom):** Compare the task fragility against the guardrails provided. High-risk tasks need stricter constraints; low-risk creative tasks need more freedom.

**I8 (feedback loops):** For quality-critical steps, verify there is a verification or re-check mechanism.

**I10 (terminology):** Confirm the same concept uses the same term throughout (e.g., don't alternate between "score" and "grade").

**I11 (XDG state):** If the skill writes persistent state or artifacts (state files, generated output, tracking files), verify it uses `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` - not `./findings/`, `${CLAUDE_SKILL_DIR}/findings/`, or any relative path. Plugin cache directories are replaced on version updates; relative paths are ambiguous and may resolve to the cache.

**I14 (phase numbering):** If SKILL.md and a reference file both define numbered phases via section headers, verify the phase numbers match. Mismatched numbering confuses the agent when both files are loaded.

#### Script and file hygiene

**I6 (script prefix):** Check script invocations use `"${CLAUDE_SKILL_DIR}/scripts/..."` directly without a `bash` prefix.

**I12 (executable bit):** Verify all runnable entrypoints in scripts/ have the executable bit set.

**I13 (useless echo):** Scan bash/sh code blocks for useless echo wrapping literal strings - `VAR="$(echo "text")"` should be `VAR="text"` (ShellCheck SC2116). Do NOT flag `$(echo "${VAR:-default}")` - in a skills context, the agent interprets code blocks as intent descriptions (see [GitHub #23813](https://github.com/anthropics/claude-code/issues/23813)), and the subshell wrapper can affect agent behavior even when it is a no-op in bash.

**I15 (link format):** Scan the body (outside fenced code blocks) for backtick-wrapped reference file paths like `` `references/foo.md` `` - these should use markdown link syntax `[references/foo.md](references/foo.md)` so Claude Code recognizes them for progressive disclosure (on-demand loading).

#### Tool and safety declarations

**I9 (over-broad tools):** Compare the `allowed-tools` list against actual tool usage in the body - flag tools listed but never used.

**I16 (tool cross-reference):** Cross-reference the `allowed-tools` list against the skill body: if `Task` is listed, verify the body mentions spawning agents, tasks, or subagents; if `ToolSearch` is listed, verify the body mentions loading deferred or MCP tools. Flag listed tools with no corresponding usage.

**I17 (side-effect guard):** If the skill body contains destructive or infrastructure-modifying command patterns (k3d cluster operations, git reset, git branch -d/-D, git apply --cached, git clean, git push --force, kubectl delete/drain/cordon, helm uninstall, rm -rf), verify that `disable-model-invocation: true` is present in the frontmatter. Without this guard the model may auto-invoke the skill.

#### Automated: preprocessing (I18)

Automated by `check-preprocessing.py`. If the skill uses `` !`command` `` preprocessing directives (outside fenced code blocks), the script validates each directive for:

- **PP-syntax:** Preprocessing directive syntax is valid
- **PP-err-handling:** Error handling on commands that depend on external state
- **PP-output-limit:** Output limiting on commands that could produce large output
- **PP-secret-leak:** No secret-revealing env var expansion like `$API_KEY` or `$DB_PASSWORD`
- **PP-mutation:** No state-changing commands at load time like `git commit` or `kubectl apply`
- **PP-slow-cmd:** No slow commands that block loading like `npm test` or `docker build`
- **PP-redundant-dir:** No redundant `` !`echo "${CLAUDE_SKILL_DIR}..."` `` wrapping since CLAUDE_SKILL_DIR is already a load-time substitution
- **PP-interactive:** No interactive commands that hang like `ssh` or `sudo` without `-n`

#### Automated: read gates (I19)

Automated by `check-read-gates.py`. Runs 7 sub-checks against all `references/*.md` and `examples/*.md` files:

- **RG-gate-present:** Every markdown-linked reference has an explicit load directive (Read, Contents of, path to, Load)
- **RG-passive:** No passive weak mentions (See, are in, Consult, per, from, available in, described in, defined in, documented in) appear before the reference's gate line
- **RG-orphan:** No files on disk are missing from SKILL.md entirely
- **RG-dead:** No references appear only in the bundled resources section without being used in the workflow
- **RG-use-order:** No reference is cited in the workflow before its read gate appears (line number comparison)
- **RG-purpose:** Read gates explain why (not bare gates ending with just the ref path)
- **RG-flow:** For multi-flow skills (multiple `## Workflow` headers), each flow that references a file has its own gate

#### Automated: script lint (I20)

Automated by `check-lint.py`. If the skill has a `scripts/` directory, runs with `--severity medium`. Detects 32 shell antipattern classes: pipe delimiters corrupting data (S01), suppressed exit codes (S02), sed range crashes on empty variables (S03), JSON output without escaping (S05-S06), space-delimited lists instead of arrays (S07), unquoted expansions (S08-S10), grep treating variables as regex (S11), missing pipefail guards (S12), heredoc/jq injection (S16-S17), mktemp without cleanup traps (S15), and more.

Also runs shellcheck (if installed) at `-S warning` severity on .sh files; shellcheck errors map to critical, warnings to medium. Use `--no-shellcheck` to skip. For .py files, runs ruff (if installed); ruff E/F codes map to critical, W to medium. Use `--no-ruff` to skip. Any critical or medium finding fails the check.

#### Automated: AskUserQuestion (I21)

Automated by `check-ask-user.py`. Runs 9 sub-checks covering AskUserQuestion usage consistency:

- **AQ-declaration:** AskUserQuestion appears in `allowed-tools` if and only if the body references it (directly or via implicit patterns)
- **AQ-implicit:** Natural-language phrases like "ask the user", "prompt the user", "let the user choose" imply user interaction but AskUserQuestion is missing from allowed-tools
- **AQ-required-arg:** Required positional arguments with no default have an ask/prompt mechanism or fallback when AskUserQuestion is declared
- **AQ-spawned-agent:** AskUserQuestion not mentioned inside spawned agent instruction sections (agents cannot interact with users)
- **AQ-option-structure:** AskUserQuestion usage sites have options/choices documented nearby
- **AQ-destructive:** Side-effect skills (`disable-model-invocation: true`) with destructive command patterns have a confirmation mechanism
- **AQ-ambiguity:** Ambiguous situations described in the body have resolution mechanisms within 5 lines
- **AQ-multiselect** (informational): `multiSelect` usage has grouping guidance
- **AQ-wizard** (informational): Confirmation wizard patterns have explicit loop termination

#### Automated: flag coverage (I22)

Automated by `check-flag-coverage.py`. Compares three zones of flag declaration:

- **FC-hint-doc:** Every `--flag` in the `argument-hint` frontmatter field must appear in the Arguments section body
- **FC-doc-hint:** Every `--flag` in the Arguments section must appear in `argument-hint`
- **FC-doc-workflow:** Every `--flag` in the Arguments section must be referenced somewhere in the workflow body (excluding the Arguments section itself and Example Invocations)

Section detection skips fenced code block headers to avoid false positives from bash comments. Only `--flag` style arguments are checked; positional arguments are not validated.

#### Automated: hooks (I23)

Automated by `check-hooks.py`. Runs 11 sub-checks against the hooks frontmatter block and all referenced hook scripts:

- **HK-events:** All event names must be from the valid set (PreToolUse, PostToolUse, PostToolUseFailure, SubagentStart, SubagentStop, Stop)
- **HK-structure:** Matcher-based events (all except Stop) must have a `matcher:` field; Stop must not
- **HK-type:** Every hook entry needs `type: "command"` with a non-empty `command:` field
- **HK-resolve:** All command paths resolve to existing files after `${CLAUDE_SKILL_DIR}` substitution
- **HK-exec:** All resolved scripts have the executable bit set
- **HK-duplicate:** No duplicate event+matcher combinations
- **HK-stdin:** Every hook script parses stdin JSON (e.g., `input="$(cat)"`)
- **HK-loop:** Stop and SubagentStop scripts must check `stop_hook_active` to prevent infinite recursion
- **HK-exit:** PreToolUse scripts must not use `exit 2` (which discards all JSON output including deny reasons)
- **HK-perm:** PostToolUse/PostToolUseFailure scripts must not output `permissionDecision` (not supported for post hooks)
- **HK-prefix:** All error codes across hook scripts use a single consistent `[PREFIX###]` format

Skills with no `hooks:` frontmatter emit `total: 0` and skip.

#### Automated: size checks (I24-I25)

Automated by `check-references.py` (I24) and `validate.py` frontmatter checks (I25).

**I24:** SKILL.md body must be under 20,000 characters. The ~5,000 token limit matters more than line count for how much context the agent retains from skill content. Skills exceeding this limit should extract content to reference files.

**I25:** The `description` frontmatter field must be under 1,024 characters. Long descriptions waste context when Claude Code loads them for auto-invocation matching.

---

## Polish checks

Informational findings. These are only scored when running with `--thorough` and do not affect the pass/fail verdict.

| ID | NDJSON | Check | Source |
| :-- | :-- | :-- | :-- |
| P1 | RF-long-ref-toc | Long references (>100 lines) have table of contents | Agent Skills Spec |
| P2 | - | One default + one escape hatch (not five options) | Anthropic Best Practices |
| P3 | FR-mentions-file | SKILL.md mentions all bundled resources | Agent Skills Spec |
| P4 | - | No time-sensitive info without deprecation plan | Anthropic skill-creator |
| P5 | FM-desc-voice | Description uses third-person form | Anthropic Best Practices |
| P6 | FR-no-backslash | No Windows-style backslash paths in file references | Anthropic Best Practices |
| P7 | - | Scripts handle errors explicitly, no unexplained magic constants | Anthropic Best Practices |
| P8 | RF-dup-codeblocks-info | No duplicated code blocks (3+ lines) between SKILL.md and references | Anthropic Best Practices |
| P9 | FK-recommendation-info | Consider `context: fork` + `agent` field for context isolation | Agent Skills Spec |
| P10 | HK-suggestion-info | Side-effect skills without hooks could benefit from hook-based guardrails | SAI Convention |

### How to evaluate

#### Reference file quality

**P1 (TOC):** Count lines in each reference file - any over 100 lines should start with a TOC linking to its sections.

**P3 (bundled mentions):** Cross-reference the skill directory listing against mentions in SKILL.md - every file should be referenced at least once.

**P5 (description form):** Confirm the `description` frontmatter uses third-person ("Aggregates daily news...") rather than second-person ("Helps you aggregate...").

**P6 (path format):** Scan for Windows-style backslash paths (`scripts\helper.py`, `reference\guide.md`) - always use forward slashes for cross-platform compatibility.

**P8 (code duplication):** Extract fenced code blocks (3+ lines) from SKILL.md and compare against reference files. Duplicates are informational - progressive disclosure means reference files are loaded independently ([Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)), so each file should be self-contained. Low-freedom operational code blocks (kubectl, script invocations) should remain wherever the agent needs them. Only flag duplicates for manual review, never auto-remove.

#### Design quality

**P2 (options):** For option-heavy instructions, verify there is one clear default path and at most one alternative, not a menu of choices.

**P4 (time-sensitive):** Flag hardcoded dates, version numbers, or URLs without a note on when to update them.

**P7 (error handling):** For skills with scripts, check that scripts handle expected error conditions rather than letting Claude infer fixes from raw failures ("solve, don't punt"). Flag any numeric constants without inline comments explaining the value ("voodoo constants").

#### Fork candidate analysis (P9)

Automated by `check-fork-candidate.py`. Analyzes six positive signals (high phase count, structured output, data gathering, manual subagent usage, heavy reference loading, self-contained inputs), four blockers (already forked, conversation-dependent, tiny skill, background knowledge), and one counter-signal (side-effect skill).

A "strong" recommendation means 3+ effective positive signals with no blockers - suggest adding `context: fork` and `agent` to frontmatter. A "soft" recommendation (2 effective) means fork is worth considering. Report the recommendation and detected signals.

#### Hook guardrails (P10)

If the skill has `disable-model-invocation: true` and a `scripts/` directory but no `hooks:` frontmatter block, suggest adding skill-scoped hooks for guardrails. This is informational only - hooks are not required.
