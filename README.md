# SAI - Skills for Agentic Intelligence

A collection of Claude Code plugins and Codex skills for development workflows, automation, and productivity.

## Overview

This monorepo contains independent plugins, each providing specialized capabilities:

Repository layout:
- `plugins/{name}/` with a root `plugin.json` is a portable package: one directory that Claude Code, Codex, Copilot CLI and opencode all load (currently `adversarial-review`, `adversarial-test`, `council`, `generate-claude-md`, `gh-review-comments`, `git-clean-gone`, `git-stage-hunk`, `go-code-review`, `humanize`, `kubecon-cfp`, `kup`, `service-mesh-debug`, `ship-issue` and `test-writer`). New and migrated plugins use this layout; see [CONTRIBUTING.md](./CONTRIBUTING.md#portable-plugin-layout).
- `claude/` contains the legacy self-contained plugin packages used by Claude Code and Copilot CLI marketplace installs.
- `codex/` contains legacy Codex/Codex Desktop skills.
- Other `plugins/` directories are Codex-compatible wrappers and special multi-surface bundles such as `plugins/refactor-council/`.

| Plugin                  | Description                                                                             | Installation Path      |
|:------------------------|:----------------------------------------------------------------------------------------|:-----------------------|
| **adversarial-review**  | Fast two-pass adversarial code review: Code Adversary subagent hunts the bug, clean-context Findings Adversary subagent refutes false positives | `plugins/adversarial-review/` |
| **adversarial-test**    | Adversarial manual testing: clean-context Test Adversary subagent runs the real product surface and tries to break it; reproductions are rerun before they count | `plugins/adversarial-test/`   |
| **ai-daily-digest**     | Daily AI news digest covering technical advances, business news, and engineering impact | `claude/ai-daily-digest/`     |
| **council**             | Run a council review when explicitly requested, through 27 sourced engineering and UX reviewer agents (antirez, tef, Muratori, Hebert, Meadows, Chin, Norman, Nielsen, Krug, Watson, Tognazzini, Tufte, etc.), and synthesize convergence, disagreement, and concrete next moves | `plugins/council/`            |
| **service-mesh-debug**  | Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul) | `plugins/service-mesh-debug/` |
| **generate-claude-md**  | Generate a lean, high-signal CLAUDE.md from codebase analysis (built to pass review-claude-md) | `plugins/generate-claude-md/` |
| **gh-review-comments**  | List, reply to, resolve, and create GitHub PR review comment threads                    | `plugins/gh-review-comments/`  |
| **git-clean-gone**      | Clean up local branches with deleted remote tracking and their worktrees               | `plugins/git-clean-gone/`     |
| **git-stage-hunk**      | Non-interactive hunk staging for selective git add without TTY                          | `plugins/git-stage-hunk/`     |
| **go-code-review**      | Auto-review Go code for 100+ common mistakes from 100go.co                              | `plugins/go-code-review/`     |
| **humanize**            | Make text sound natural by removing AI writing patterns                                 | `plugins/humanize/`           |
| **kubecon-cfp**         | Interactive KubeCon CFP submission writer with data-driven insights                    | `plugins/kubecon-cfp/`        |
| **kup**                 | Fill the monthly KUP report (Polish creative-work tax deduction) from merged GitHub PRs into a Google Sheet | `plugins/kup/`                |
| **promptgen**           | Turn rough instructions into optimized, evidence-based AI prompts                       | `plugins/promptgen/`          |
| **refactor-council**    | Refactoring review through 7 sourced refactoring personas (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout, Tornhill): scans smells + git hotspots, synthesizes a safety-first plan, then an adversary red-teams it | `claude/refactor-council/`    |
| **review-claude-md**    | Audit and fix CLAUDE.md files using tiered binary checklist                             | `claude/review-claude-md/`    |
| **staff-code-review**   | Staff-engineer-level code review: architecture, reliability, security, cross-team impact | `claude/staff-code-review/`   |
| **staff-resume**        | Build and refine staff-level engineering resumes through interactive coaching           | `claude/staff-resume/`        |
| **ship-issue**          | Ship a GitHub issue through implementation, adversarial review/testing, PR, CI, Copilot review, merge, and closure | `plugins/ship-issue/` |
| **test-writer**         | Write behavior-driven tests with table-driven patterns and minimal mocking             | `plugins/test-writer/`        |

Codex skills:

| Skill                  | Description                                                                      | Source Path                  |
|:-----------------------|:---------------------------------------------------------------------------------|:-----------------------------|
| **adversarial-review** | Two-pass adversarial code review in sequential clean-context subagents (same portable package as Claude Code) | `plugins/adversarial-review/skills/adversarial-review/` |
| **adversarial-test**   | Adversarial manual testing of the real product surface in a clean-context subagent (same portable package as Claude Code) | `plugins/adversarial-test/skills/adversarial-test/` |
| **council**            | Persona reviewer councils run one reviewer at a time on Codex, with strict bounded-input and output rules (same portable package as Claude Code) | `plugins/council/skills/council/` |
| **refactor-council**   | Refactoring review through 7 personas + adversary; sequential by default on Codex for reliable execution | `codex/refactor-council/` |
| **generate-claude-md** | Generate a lean CLAUDE.md from codebase analysis (same portable package as Claude Code) | `plugins/generate-claude-md/skills/generate-claude-md/` |
| **gh-review-comments** | Manage GitHub PR review threads with bundled gh CLI scripts (same portable package as Claude Code) | `plugins/gh-review-comments/skills/gh-review-comments/` |
| **git-clean-gone**     | Clean up stale local branches and worktrees; explicit invocation only (same portable package as Claude Code) | `plugins/git-clean-gone/skills/git-clean-gone/` |
| **git-stage-hunk**     | Stage selected git hunks without a TTY; explicit invocation only (same portable package as Claude Code) | `plugins/git-stage-hunk/skills/git-stage-hunk/` |
| **go-code-review**     | Review Go code for 100+ common mistakes from 100go.co (same portable package as Claude Code) | `plugins/go-code-review/skills/go-code-review/` |
| **humanize**           | Remove AI writing patterns from text (same portable package as Claude Code) | `plugins/humanize/skills/humanize/` |
| **kubecon-cfp**        | Draft and refine KubeCon CFP submissions, explicit invocation only (same portable package as Claude Code) | `plugins/kubecon-cfp/skills/kubecon-cfp/` |
| **kup**                | Fill the monthly KUP report from merged GitHub PRs into a Google Sheet (same portable package as Claude Code) | `plugins/kup/skills/kup/` |
| **promptgen**          | Turn rough instructions into stronger prompts; clipboard copy with print fallback (same portable package as Claude Code) | `plugins/promptgen/skills/promptgen/` |
| **service-mesh-debug** | Diagnose flaky service-mesh e2e tests and connectivity issues with read-only Envoy diagnostic scripts (same portable package as Claude Code) | `plugins/service-mesh-debug/skills/service-mesh-debug/` |
| **ship-issue**         | Ship a GitHub issue through implementation, review, testing, PR, CI, and merge; explicit invocation only (same portable package as Claude Code) | `plugins/ship-issue/skills/ship-issue/` |
| **test-writer**        | Write or review behavior-first tests with table-driven patterns and minimal mocking (same portable package as Claude Code) | `plugins/test-writer/skills/test-writer/` |

## Installation

### Via marketplace

Add the SAI marketplace, then install individual plugins:

These examples use interactive `/plugin ...` commands, which work in both
Copilot CLI and Claude Code sessions.
The equivalent non-interactive forms are `copilot plugin ...` and
`claude plugin ...`.

```bash
# Add the SAI marketplace
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install individual plugins
/plugin install adversarial-review@sai
/plugin install adversarial-test@sai
/plugin install ai-daily-digest@sai
/plugin install council@sai
/plugin install service-mesh-debug@sai
/plugin install generate-claude-md@sai
/plugin install gh-review-comments@sai
/plugin install git-clean-gone@sai
/plugin install git-stage-hunk@sai
/plugin install go-code-review@sai
/plugin install humanize@sai
/plugin install kubecon-cfp@sai
/plugin install kup@sai
/plugin install promptgen@sai
/plugin install refactor-council@sai
/plugin install review-claude-md@sai
/plugin install staff-code-review@sai
/plugin install staff-resume@sai
/plugin install ship-issue@sai
/plugin install test-writer@sai
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/plugins/adversarial-review
claude --plugin-dir /path/to/sai/plugins/adversarial-test
claude --plugin-dir /path/to/sai/claude/ai-daily-digest
claude --plugin-dir /path/to/sai/plugins/council
claude --plugin-dir /path/to/sai/plugins/service-mesh-debug
claude --plugin-dir /path/to/sai/plugins/generate-claude-md
claude --plugin-dir /path/to/sai/plugins/gh-review-comments
claude --plugin-dir /path/to/sai/plugins/git-clean-gone
claude --plugin-dir /path/to/sai/plugins/git-stage-hunk
claude --plugin-dir /path/to/sai/plugins/go-code-review
claude --plugin-dir /path/to/sai/plugins/humanize
claude --plugin-dir /path/to/sai/plugins/kubecon-cfp
claude --plugin-dir /path/to/sai/plugins/kup
claude --plugin-dir /path/to/sai/plugins/promptgen
claude --plugin-dir /path/to/sai/claude/refactor-council
claude --plugin-dir /path/to/sai/claude/review-claude-md
claude --plugin-dir /path/to/sai/claude/staff-code-review
claude --plugin-dir /path/to/sai/claude/staff-resume
claude --plugin-dir /path/to/sai/plugins/ship-issue
claude --plugin-dir /path/to/sai/plugins/test-writer

# Copilot CLI can load the same self-contained plugin directories directly.
copilot --plugin-dir /path/to/sai/claude/staff-code-review

# Skills with agent fan-out also have dedicated multi-surface bundles
# that ship native Copilot reviewer agents (sequential delegation by default).
copilot --plugin-dir /path/to/sai/plugins/refactor-council
copilot --plugin-dir /path/to/sai/plugins/staff-code-review
copilot --plugin-dir /path/to/sai/plugins/plan-critic
copilot --plugin-dir /path/to/sai/plugins/ai-daily-digest
copilot --plugin-dir /path/to/sai/plugins/review-claude-md
```

### OpenCode

OpenCode discovers Agent Skills from `~/.config/opencode/skills/` and `~/.agents/skills/`. Symlink the portable skills:

```bash
ln -s /path/to/sai/plugins/adversarial-review/skills/adversarial-review ~/.config/opencode/skills/adversarial-review
ln -s /path/to/sai/plugins/adversarial-test/skills/adversarial-test ~/.config/opencode/skills/adversarial-test
ln -s /path/to/sai/plugins/council/skills/council ~/.config/opencode/skills/council
ln -s /path/to/sai/plugins/generate-claude-md/skills/generate-claude-md ~/.config/opencode/skills/generate-claude-md
ln -s /path/to/sai/plugins/gh-review-comments/skills/gh-review-comments ~/.config/opencode/skills/gh-review-comments
ln -s /path/to/sai/plugins/git-clean-gone/skills/git-clean-gone ~/.config/opencode/skills/git-clean-gone
ln -s /path/to/sai/plugins/git-stage-hunk/skills/git-stage-hunk ~/.config/opencode/skills/git-stage-hunk
ln -s /path/to/sai/plugins/go-code-review/skills/go-code-review ~/.config/opencode/skills/go-code-review
ln -s /path/to/sai/plugins/humanize/skills/humanize ~/.config/opencode/skills/humanize
ln -s /path/to/sai/plugins/kubecon-cfp/skills/kubecon-cfp ~/.config/opencode/skills/kubecon-cfp
ln -s /path/to/sai/plugins/service-mesh-debug/skills/service-mesh-debug ~/.config/opencode/skills/service-mesh-debug
ln -s /path/to/sai/plugins/ship-issue/skills/ship-issue ~/.config/opencode/skills/ship-issue
ln -s /path/to/sai/plugins/test-writer/skills/test-writer ~/.config/opencode/skills/test-writer
```

## Plugins

### adversarial-review

Fast two-pass adversarial code review. A Code Adversary subagent assumes the change is broken and proves each bug with a failing input; a fresh Findings Adversary subagent sees only those findings and tries to refute them against the source. Leads with `Review Verdict: CLEAN|NEEDS_FIXES`. Runs on Claude Code, Codex, Copilot CLI, and OpenCode from one package; `ship-issue` uses it as its review gate.

**Usage**: `/adversarial-review [<pr-url> | <diff-file> | --base <ref>] [--context <file|text>]`

[Full documentation ->](./plugins/adversarial-review/README.md)

### adversarial-test

Adversarial manual testing. A clean-context Test Adversary subagent derives acceptance criteria from the task, runs the real product surface (service, CLI, sandbox) against isolated temp state, and attacks boundaries, malformed input, repetition, and adjacent flows. Every reproduction is rerun before it counts; a PASS backed only by unit tests or lint is rejected. Leads with `Test Verdict: PASS|FAIL|BLOCKED`. One package for Claude Code, Codex, Copilot CLI and opencode (Codex: `$adversarial-test`); `ship-issue` uses it as its testing gate.

**Usage**: `/adversarial-test [<pr-url> | --base <ref>] [--context <file|text>]`

[Full documentation ->](./plugins/adversarial-test/README.md)

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation ->](./claude/ai-daily-digest/README.md)

### council

Run a council review when explicitly requested, through 27 sourced engineering and UX reviewer agents - antirez, tef, Casey Muratori, Fred Hebert, Donella Meadows, Cedric Chin, Alexis King, John Hughes, Eric Evans, Mark Seemann with Scott Wlaschin, Hillel Wayne, Kief Morris with Yevgeniy Brikman, Gary Bernhardt with Beck and Fowler, Brendan Gregg, Simon Willison, Charity Majors, Chris Eidhof with Florian Kugler, Mike Ash, Brent Simmons, Don Norman, Bruce Tognazzini, Steve Krug, Jakob Nielsen, Léonie Watson, Val Head, John Siracusa, and Edward Tufte. Each reviewer is built from the writer's primary public corpus and argues from their actual positions. The orchestrator synthesizes one integrated review across opposed lenses.

**Usage**: `/council [core|auto|core-eng|core-ux|core-mix|all|debate] <problem-description|@file>`

One package for Claude Code, Codex (`$council`), Copilot CLI and opencode. `core` remains the default; fixed `core-*` modes always run all 6 selected reviewers, while `auto` selects exactly 6 best-fit reviewers. Claude Code and Copilot CLI spawn the 27 bundled persona agents (`council:<slug>`) in parallel; Copilot supervises them about once a minute and nudges drifting reviewers. Codex and opencode spawn generic reviewers one at a time, each given its persona mandate from `skills/council/references/agents/`, and Codex keeps its strict rules: bounded input, stale-agent cleanup before spawning, `Council progress:` lines only, and no raw reviewer payloads. On Copilot, Codex and opencode, runs broader than 6 reviewers need explicit current-run approval; without it the council stops with exactly `Council not run: broad council approval not granted.` Council is opt-in review work, not a commit or approval gate; follow-up challenges come back as synthesized council output.

[Full documentation ->](./plugins/council/README.md)

### service-mesh-debug

Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul). Covers 11 root causes: timing races, xDS propagation delays, Gomega misuse (`Expect` inside `Eventually`), pod availability races, mTLS/SDS cert delivery, Envoy circuit breakers, and outlier detection ejection. Includes Python scripts for live Envoy sidecar diagnostics.

**Usage**: `/service-mesh-debug` (auto-triggers on flaky test mentions, `test/e2e/` paths, intermittent CI failures, 503 errors, mTLS failures; Codex: `$service-mesh-debug`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/service-mesh-debug/README.md)

### gh-review-comments

List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Manage code review feedback, reply to reviewer remarks, resolve conversations.

**Usage**: `/gh-review-comments owner/repo 42 [--reply "message"] [--resolve] [--author login]` (Codex: `$gh-review-comments`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/gh-review-comments/README.md)

### git-clean-gone

Clean up local branches with deleted remote tracking and their worktrees. Detects gone branches, squash-merged PRs, and rebased branches.

**Usage**: `/git-clean-gone [--dry-run] [--no-worktrees]` (Codex: `$git-clean-gone`, explicit invocation only). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/git-clean-gone/README.md)

### git-stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Lists hunks with stable IDs, then stages by ID, pattern, file, or line range. Works in scripted and multi-agent environments where `git add -p` is unavailable.

**Usage**: `/git-stage-hunk [--list] [--hunk H1,H2] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--dry-run]` (Codex: `$git-stage-hunk`, explicit invocation only). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/git-stage-hunk/README.md)

### go-code-review

Auto-review Go code for 100+ common mistakes from [100go.co](https://100go.co/). Auto-triggers when reviewing `.go` files or Go PRs. Checks error handling, concurrency, interfaces, performance, testing, and stdlib usage with severity tiers and direct mistake references.

**Usage**: `/go-code-review` (Codex: `$go-code-review`; auto-triggers on `.go` files and Go PRs). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/go-code-review/README.md)

### humanize

Make text sound natural by removing AI writing patterns. Based on Wikipedia's Signs of AI Writing guide - detects 24 patterns across content, language, style, communication, and filler categories.

**Usage**: `/humanize path/to/file.md [--score-only] [--dry-run]` (Codex: `$humanize`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/humanize/README.md)

### kubecon-cfp

Interactive KubeCon CFP submission writer with data-driven insights from 1,100+ accepted talks across 7 KubeCon events (2024-2025). Guides through topic assessment, title crafting, abstract writing, and review scoring.

**Usage**: `/kubecon-cfp [topic or talk idea] [--track AI|Security|Platform|...] [--format session|lightning|tutorial|panel] [--review]` (Codex: `$kubecon-cfp`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/kubecon-cfp/README.md)

### kup

Fill the monthly KUP report (Koszty Uzyskania Przychodu, the Polish 50% tax deduction for creative work). A bundled script finds the missing month and its row, collects your merged GitHub PRs, drops backports and dependency bumps, and writes the row to your KUP Google Sheet, while the agent writes a Polish creative-work description for each PR. It also reads and edits the sheet cell by cell. A portable Agent Plugin, so the same package installs in Claude Code and Codex (`codex plugin add kup@sai`).

**Usage**: `/kup` or "fill my KUP report", "catch up the KUP sheet", "preview KUP for 2026-03"

[Full documentation ->](./plugins/kup/README.md)

### promptgen

Turn rough instructions into optimized, evidence-based AI prompts with outcome contracts, model fit, safety boundaries, and verification rules. Copies to clipboard. A portable Agent Plugin, so the same package installs in Claude Code and Codex (`codex plugin add promptgen@sai`).

**Usage**: `/promptgen <instructions> [--for claude|gpt|codex|generic] [--research light|deep] [--verbose] [--no-copy] [--examples] [--raw]`

[Full documentation ->](./plugins/promptgen/README.md)

### refactor-council

Refactoring review through seven sourced refactoring-and-architecture persona agents - Martin Fowler, Robert C. Martin (Uncle Bob), Michael Feathers, Kent Beck, Sandi Metz, John Ousterhout, and Adam Tornhill. Scans the target for code smells and git hotspots, reviews it through opposed lenses (small-functions vs deep-modules, DRY vs duplication, what-to-refactor vs where-to-refactor), synthesizes a safety-first sequenced refactoring plan, then runs a separate adversary agent that red-teams the plan before returning it.

**Usage**: `/refactor-council <path|@file|directory> [--no-scan] [--no-adversary] [--since 12.month] [--personas a,b,c]`

[Full documentation ->](./claude/refactor-council/README.md)

### generate-claude-md

Generate a lean, high-signal CLAUDE.md from codebase analysis. The generator counterpart to `review-claude-md` — it targets the same best-practices rubric the reviewer audits against, with a bundled validator that enforces the reviewer's Critical checks, so output is built to pass that audit. Produces exact commands, an architecture map, and real gotchas while avoiding README duplication, directory trees, and generic advice. Non-destructive: never overwrites an existing CLAUDE.md without `--force`.

**Usage**: `/generate-claude-md [path/to/repo] [--output PATH] [--update] [--force] [--rules] [--dry-run]` (Codex: `$generate-claude-md`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/generate-claude-md/README.md)

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation ->](./claude/review-claude-md/README.md)

### ship-issue

Take a GitHub issue, or a task description that becomes one, to a merged PR: implement, pass the `adversarial-review` and `adversarial-test` gates, open a PR, wait for green CI and a Copilot review, fix feedback, merge, and close the issue.

**Usage**: `/ship-issue <github-issue-url | task description>` (Codex: `$ship-issue`, explicit invocation only). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/ship-issue/README.md)

### staff-code-review

Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, observability, security, and cross-team impact. Three-pass workflow: triage, codebase research, parallel deep review across Architecture & Design, Reliability & Operations, and Security & Dependencies.

**Usage**: `/staff-code-review <PR URL>` — also triggers on "review this PR", "staff review", "thorough code review"

[Full documentation ->](./claude/staff-code-review/README.md)

### staff-resume

Build and refine staff-level engineering resumes through interactive coaching, research-backed best practices, and per-job tailoring.

**Usage**: `/staff-resume <resume-path> [--job-url URL] [--mode coach|tailor|full]`

[Full documentation ->](./claude/staff-resume/README.md)

### test-writer

Write tests that verify behavior (not implementation), use table-driven/parameterized patterns, and minimize mocking. Supports Go, Python, TypeScript, Java, and Rust.

**Usage**: `/test-writer [file-or-function] [--review] [--lang go|python|ts|java|rust]` (Codex: `$test-writer`). One package for Claude Code, Codex, Copilot CLI and opencode.

[Full documentation ->](./plugins/test-writer/README.md)

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed documentation on:

- Plugin architecture
- Creating new plugins
- Skill definition format
- Workflow patterns
- State management
- Testing and contribution guidelines

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution workflow.

To contribute:

1. Fork the repository
2. Create a feature branch
3. Add/modify plugin in its directory
4. Test locally with `claude --plugin-dir claude/{plugin-name}/`
5. Submit a pull request

## License

MIT - See [LICENSE](./LICENSE)

## Repository

- **GitHub**: https://github.com/smykla-skalski/sai
