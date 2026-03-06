# Review Checklist

Binary checklist for evaluating Claude Code skill definitions. Each check is pass/fail.

## Table of Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements from the Agent Skills specification and Anthropic best practices.

| ID  | Check                                                                         | Source                                       |
|:----|:------------------------------------------------------------------------------|:---------------------------------------------|
| C1  | Description includes what the skill does AND when-to-use trigger phrases      | Anthropic Best Practices, Agent Skills Spec  |
| C2  | SKILL.md body under 500 lines (excluding frontmatter)                         | Agent Skills Spec, Claude Code Docs          |
| C3  | All file references in SKILL.md resolve to actual files                       | Agent Skills Spec                            |
| C4  | Name field valid format and matches directory name                            | Agent Skills Spec                            |
| C5  | No generic content Claude already knows ("write clean code", "handle errors") | Anthropic skill-creator, Context Engineering |
| C6  | Not structured as a scoring rubric with points, weights, or letter grades     | Anthropic Best Practices                     |
| C7  | No secrets or credentials in skill files (API keys, tokens, private keys)     | Anthropic Best Practices                     |

### How to evaluate

Read the SKILL.md frontmatter first. Confirm the `description` field contains both a functional summary and at least one trigger phrase (e.g., "Use when..."). Count body lines excluding the YAML frontmatter block and verify < 500. Grep for file paths referenced in the body and confirm each resolves relative to the skill directory. Verify the `name` field is kebab-case and matches the parent directory name exactly. Scan for filler instructions that restate LLM defaults — if removing a sentence changes nothing about behavior, it fails C5. Scan for grading-style patterns: point values, percentage weights, letter-grade scales, scoring rubric keywords. If two or more signals appear, the skill is structured as a scoring rubric rather than an imperative workflow — it fails C6. Scan SKILL.md and all bundled files for secrets: AWS access keys (`AKIA...`), API keys (`sk-...`, `api_key=`), bearer tokens, private key blocks (`-----BEGIN...KEY-----`), inline passwords or tokens. Any match fails C7.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect skill quality.

| ID  | Check                                                                               | Source                                        |
|:----|:------------------------------------------------------------------------------------|:----------------------------------------------|
| I1  | Imperative form throughout ("Parse input" not "You should parse")                   | Anthropic skill-creator                       |
| I2  | Progressive disclosure — complex skills use references/ for details                 | Agent Skills Spec, Context Engineering        |
| I3  | Concrete examples showing inputs → outputs                                          | Anthropic Best Practices, Context Engineering |
| I4  | No prose duplication between SKILL.md and references (code blocks OK)               | Anthropic skill-creator                       |
| I5  | Explicit read directives for workflow-critical references ("Read X before phase Y") | Empirical finding                             |
| I6  | Scripts invoked directly via `"${CLAUDE_SKILL_DIR}/scripts/..."`, never `bash` prefix | SAI Convention                                |
| I7  | Appropriate degrees of freedom (guardrails match task fragility)                    | Anthropic Best Practices                      |
| I8  | Feedback loops for quality-critical steps                                           | Anthropic Best Practices                      |
| I9  | allowed-tools not over-broad (only tools actually needed)                           | Anthropic Best Practices                      |
| I10 | Consistent terminology (same concept = same word)                                   | Anthropic Best Practices                      |
| I11 | Persistent state uses XDG paths, not relative or cache-relative paths               | SAI Convention, Plugin Cache Architecture     |
| I12 | All scripts in scripts/ have executable bit set                                     | SAI Convention                                |
| I13 | No useless echo wrapping literals (`$(echo "text")`, not `$(echo "${VAR}")`)        | ShellCheck SC2116                             |
| I14 | Consistent phase/step numbering between SKILL.md and references                     | Anthropic Best Practices                      |
| I15 | Reference file paths use markdown links, not inline code, for progressive disclosure | Agent Skills Spec, Progressive Disclosure     |
| I16 | allowed-tools only lists tools actually referenced in the skill body                 | Anthropic Best Practices                      |
| I17 | Side-effect skills have `disable-model-invocation: true` in frontmatter              | Anthropic Best Practices                      |
| I18 | Preprocessing directives follow best practices (error handling, output limits, no secrets, no mutations, no slow/hanging commands) | Claude Code Docs, Community Best Practices |
| I19 | Every `references/*.md` linked in the body has an explicit Read directive (Read, Contents of, path to) | Empirical finding, I5 automated complement |

### How to evaluate

Scan the SKILL.md body for second-person phrasing ("you should", "you can") — every instruction should be imperative. Check whether the SKILL.md exceeds ~150 lines; if so, verify that detail-heavy sections (examples, search patterns, rubrics) are extracted to references/. Look for at least one concrete input → output example. Diff the SKILL.md against each reference file for duplicated paragraphs or tables. Verify that any reference file used during execution has an explicit "Read references/X before Phase N" directive. Check script invocations use `"${CLAUDE_SKILL_DIR}/scripts/..."` directly without a `bash` prefix. Verify all scripts in scripts/ have the executable bit set. Compare the `allowed-tools` list against actual tool usage in the body — flag tools listed but never used. Confirm the same concept uses the same term throughout (e.g., don't alternate between "score" and "grade"). If the skill writes persistent state or artifacts (state files, generated output, tracking files), verify it uses `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` — not `./findings/`, `${CLAUDE_SKILL_DIR}/findings/`, or any relative path. Plugin cache directories are replaced on version updates; relative paths are ambiguous and may resolve to the cache. Scan bash/sh code blocks for useless echo wrapping literal strings — `VAR="$(echo "text")"` should be `VAR="text"` (ShellCheck SC2116). Do NOT flag `$(echo "${VAR:-default}")` — in a skills context, the agent interprets code blocks as intent descriptions (see [GitHub #23813](https://github.com/anthropics/claude-code/issues/23813)), and the subshell wrapper can affect agent behavior even when it is a no-op in bash. If SKILL.md and a reference file both define numbered phases via section headers, verify the phase numbers match — mismatched numbering confuses the agent when both files are loaded. Scan the body (outside fenced code blocks) for backtick-wrapped reference file paths like `` `references/foo.md` `` — these should use markdown link syntax `[references/foo.md](references/foo.md)` so Claude Code recognizes them for progressive disclosure (on-demand loading). Cross-reference the `allowed-tools` list against the skill body: if `Task` is listed, verify the body mentions spawning agents, tasks, or subagents; if `ToolSearch` is listed, verify the body mentions loading deferred or MCP tools. Flag listed tools with no corresponding usage. If the skill body contains destructive or infrastructure-modifying command patterns (k3d cluster operations, git reset, git branch -d/-D, git apply --cached, git clean, git push --force, kubectl delete/drain/cordon, helm uninstall, rm -rf), verify that `disable-model-invocation: true` is present in the frontmatter — without this guard the model may auto-invoke the skill. If the skill uses `!`command`` preprocessing directives (outside fenced code blocks), run `check-preprocessing.sh` to validate each directive for: error handling on commands that depend on external state (P-ERR), output limiting on commands that could produce large output (P-OUT), no secret-revealing env var expansion like `$API_KEY` or `$DB_PASSWORD` (P-SEC), no state-changing commands at load time like `git commit` or `kubectl apply` (P-MUT), no slow commands that block loading like `npm test` or `docker build` (P-SLOW), no redundant `!`echo "${CLAUDE_SKILL_DIR}..."`` wrapping since CLAUDE_SKILL_DIR is already a load-time substitution (P-DUP), and no interactive commands that hang like `ssh` or `sudo` without `-n` (P-HANG). For I19 (automated by validate.sh `ref-read-gate` check): extract all `references/*.md` markdown links from the body (via the `(references/file.md)` portion). For each unique file, verify that the body contains at least one explicit read directive — a line matching `Read.*file`, `Contents of.*file`, or `path to.*file` (case-insensitive). Accepted patterns include "Read [ref] before Phase N", "Contents of [ref]" (agent prompt), and "path to [ref]" (agent pass). References that only appear in bundled resource listings or passive mentions ("are in [ref]", "See [ref]") lack explicit directives and are flagged.

---

## Polish Checks

Informational findings. These are only scored when running with `--thorough` and do not affect the pass/fail verdict.

| ID  | Check                                                            | Source                   |
|:----|:-----------------------------------------------------------------|:-------------------------|
| P1  | Long references (>100 lines) have table of contents              | Agent Skills Spec        |
| P2  | One default + one escape hatch (not five options)                | Anthropic Best Practices |
| P3  | SKILL.md mentions all bundled resources                          | Agent Skills Spec        |
| P4  | No time-sensitive info without deprecation plan                  | Anthropic skill-creator  |
| P5  | Description uses third-person form                               | Anthropic Best Practices |
| P6  | No Windows-style backslash paths in file references              | Anthropic Best Practices |
| P7  | Scripts handle errors explicitly, no unexplained magic constants | Anthropic Best Practices |
| P8  | No duplicated code blocks (3+ lines) between SKILL.md and references | Anthropic Best Practices |
| P9  | Consider `context: fork` + `agent` field for context isolation        | Agent Skills Spec        |

### How to evaluate

Count lines in each reference file — any over 100 lines should start with a TOC linking to its sections. For option-heavy instructions, verify there is one clear default path and at most one alternative, not a menu of choices. Cross-reference the skill directory listing against mentions in SKILL.md — every file should be referenced at least once. Flag hardcoded dates, version numbers, or URLs without a note on when to update them. Confirm the `description` frontmatter uses third-person ("Aggregates daily news...") rather than second-person ("Helps you aggregate..."). Scan for Windows-style backslash paths (`scripts\helper.py`, `reference\guide.md`) — always use forward slashes for cross-platform compatibility. For skills with scripts, check that scripts handle expected error conditions rather than letting Claude infer fixes from raw failures ("solve, don't punt"). Flag any numeric constants without inline comments explaining the value ("voodoo constants"). Extract fenced code blocks (3+ lines) from SKILL.md and compare against reference files. Duplicates are informational — progressive disclosure means reference files are loaded independently ([Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)), so each file should be self-contained. Low-freedom operational code blocks (kubectl, script invocations) should remain wherever the agent needs them. Only flag duplicates for manual review, never auto-remove. For P9, run `check-fork-candidate.sh` against the skill directory. The script analyzes six positive signals (high phase count, structured output, data gathering, manual subagent usage, heavy reference loading, self-contained inputs), four blockers (already forked, conversation-dependent, tiny skill, background knowledge), and one counter-signal (side-effect skill). A "strong" recommendation means 3+ effective positive signals with no blockers — suggest adding `context: fork` and `agent` to frontmatter. A "soft" recommendation (2 effective) means fork is worth considering. Report the recommendation and detected signals.
