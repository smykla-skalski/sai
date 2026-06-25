# SAI - Skills for Agentic Intelligence

A collection of Claude Code plugins and Codex skills for development workflows, automation, and productivity.

## Overview

This monorepo contains independent plugins, each providing specialized capabilities:

Repository layout:
- `claude/` contains the self-contained plugin packages used by Claude Code and Copilot CLI marketplace installs.
- `codex/` contains Codex/Codex Desktop skills and shared native agent definitions.
- `plugins/` contains Codex-compatible packages and special multi-surface bundles such as `plugins/council/`.

| Plugin                  | Description                                                                             | Installation Path      |
|:------------------------|:----------------------------------------------------------------------------------------|:-----------------------|
| **ai-daily-digest**     | Daily AI news digest covering technical advances, business news, and engineering impact | `claude/ai-daily-digest/`     |
| **council**             | Run a council review when explicitly requested, through 27 sourced engineering and UX reviewer agents (antirez, tef, Muratori, Hebert, Meadows, Chin, Norman, Nielsen, Krug, Watson, Tognazzini, Tufte, etc.), and synthesize convergence, disagreement, and concrete next moves | `claude/council/`             |
| **service-mesh-debug**  | Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul) | `claude/service-mesh-debug/`  |
| **generate-claude-md**  | Generate a lean, high-signal CLAUDE.md from codebase analysis (built to pass review-claude-md) | `claude/generate-claude-md/`  |
| **gh-review-comments**  | List, reply to, resolve, and create GitHub PR review comment threads                    | `claude/gh-review-comments/`  |
| **git-clean-gone**      | Clean up local branches with deleted remote tracking and their worktrees               | `claude/git-clean-gone/`      |
| **git-stage-hunk**      | Non-interactive hunk staging for selective git add without TTY                          | `claude/git-stage-hunk/`      |
| **go-code-review**      | Auto-review Go code for 100+ common mistakes from 100go.co                              | `claude/go-code-review/`      |
| **humanize**            | Make text sound natural by removing AI writing patterns                                 | `claude/humanize/`            |
| **kubecon-cfp**         | Interactive KubeCon CFP submission writer with data-driven insights                    | `claude/kubecon-cfp/`         |
| **promptgen**           | Turn rough instructions into optimized, evidence-based AI prompts                       | `claude/promptgen/`           |
| **refactor-council**    | Refactoring review through 7 sourced refactoring personas (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout, Tornhill): scans smells + git hotspots, synthesizes a safety-first plan, then an adversary red-teams it | `claude/refactor-council/`    |
| **review-claude-md**    | Audit and fix CLAUDE.md files using tiered binary checklist                             | `claude/review-claude-md/`    |
| **staff-code-review**   | Staff-engineer-level code review: architecture, reliability, security, cross-team impact | `claude/staff-code-review/`   |
| **staff-resume**        | Build and refine staff-level engineering resumes through interactive coaching           | `claude/staff-resume/`        |
| **test-writer**         | Write behavior-driven tests with table-driven patterns and minimal mocking             | `claude/test-writer/`         |

Codex skills:

| Skill                  | Description                                                                      | Source Path                  |
|:-----------------------|:---------------------------------------------------------------------------------|:-----------------------------|
| **council**            | Run native Codex reviewer-agent councils and synthesize concrete next moves | `plugins/council/skills/council/` |
| **refactor-council**   | Refactoring review through 7 personas + adversary; sequential by default on Codex for reliable execution | `codex/refactor-council/` |
| **gh-review-comments** | Manage GitHub PR review threads with bundled gh CLI scripts                      | `codex/gh-review-comments/`  |
| **promptgen**           | Turn rough instructions into stronger prompts using the Claude promptgen source workflow | `codex/promptgen/`            |

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
/plugin install ai-daily-digest@sai
/plugin install council@sai
/plugin install service-mesh-debug@sai

# (Codex marketplace also provides /plugin install council@sai for Codex sessions)
/plugin install generate-claude-md@sai
/plugin install gh-review-comments@sai
/plugin install git-clean-gone@sai
/plugin install git-stage-hunk@sai
/plugin install go-code-review@sai
/plugin install humanize@sai
/plugin install kubecon-cfp@sai
/plugin install promptgen@sai
/plugin install refactor-council@sai
/plugin install review-claude-md@sai
/plugin install staff-code-review@sai
/plugin install staff-resume@sai
/plugin install test-writer@sai
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/claude/ai-daily-digest
claude --plugin-dir /path/to/sai/claude/council
claude --plugin-dir /path/to/sai/claude/service-mesh-debug
claude --plugin-dir /path/to/sai/claude/generate-claude-md
claude --plugin-dir /path/to/sai/claude/gh-review-comments
claude --plugin-dir /path/to/sai/claude/git-clean-gone
claude --plugin-dir /path/to/sai/claude/git-stage-hunk
claude --plugin-dir /path/to/sai/claude/go-code-review
claude --plugin-dir /path/to/sai/claude/humanize
claude --plugin-dir /path/to/sai/claude/kubecon-cfp
claude --plugin-dir /path/to/sai/claude/promptgen
claude --plugin-dir /path/to/sai/claude/refactor-council
claude --plugin-dir /path/to/sai/claude/review-claude-md
claude --plugin-dir /path/to/sai/claude/staff-code-review
claude --plugin-dir /path/to/sai/claude/staff-resume
claude --plugin-dir /path/to/sai/claude/test-writer

# Copilot CLI can load the same self-contained plugin directories directly.
copilot --plugin-dir /path/to/sai/claude/staff-code-review

# Council and Refactor Council also have dedicated multi-surface bundles.
copilot --plugin-dir /path/to/sai/plugins/council
copilot --plugin-dir /path/to/sai/plugins/refactor-council
```

## Plugins

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation ->](./claude/ai-daily-digest/README.md)

### council

Run a council review when explicitly requested, through 27 sourced engineering and UX reviewer agents - antirez, tef, Casey Muratori, Fred Hebert, Donella Meadows, Cedric Chin, Alexis King, John Hughes, Eric Evans, Mark Seemann with Scott Wlaschin, Hillel Wayne, Kief Morris with Yevgeniy Brikman, Gary Bernhardt with Beck and Fowler, Brendan Gregg, Simon Willison, Charity Majors, Chris Eidhof with Florian Kugler, Mike Ash, Brent Simmons, Don Norman, Bruce Tognazzini, Steve Krug, Jakob Nielsen, Léonie Watson, Val Head, John Siracusa, and Edward Tufte. Each reviewer is built from the writer's primary public corpus and argues from their actual positions. The orchestrator synthesizes one integrated review across opposed lenses.

**Usage**: `/council [core|auto|core-eng|core-ux|core-mix|all|debate] <problem-description|@file>`

Codex usage is `$council [core|auto|core-eng|core-ux|core-mix|all|debate] <problem-description|@file>`. `core` remains the default; fixed `core-*` modes always run all 6 selected reviewers, while `auto` is explicit and selects exactly 6 best-fit reviewers. Codex Council spawns native reviewer agents directly from installed Codex agent definitions at high reasoning effort, passes the same complete bounded review bundle to every reviewer, validates each finished report, strips transport markers, and synthesizes disagreement with the mandatory Council headings even when reviewers agree. Reviewers may read only directly connected exact files named in the assignment; they must not wander the repo, read memory/prior sessions/persona dossiers, or run tests/builds. Runs broader than 6 reviewers require explicit current-run approval; if approval is unavailable, Codex Council stops with exactly `Council not run: broad council approval not granted.` While reviewers are active, the Codex orchestrator stays alive, performs per-reviewer health checks at least once per minute, nudges drifting or stalled reviewers with `followup_task`, and may emit sparse `Council progress:` updates without raw reviewer payloads.

Copilot CLI usage should normally start with `/council [core|auto|core-eng|core-ux|core-mix|all|debate] <problem-description|@file>`, which keeps you in your current working session and makes the current session agent act as the council orchestrator for the bundled reviewer agents. Council is opt-in review work: do not use it as a generic commit, pre-commit, or approval gate unless the user explicitly asked for council. Runs broader than 6 reviewers must receive explicit AskUserQuestion approval in the current run; if that approval is unavailable, `/council` stops instead of silently shrinking itself. While reviewers are running, the orchestrator checks reviewer state on roughly a one-minute cadence, nudges reviewers that drift broad, stall, or circle without progress, and may emit sparse `Council progress:` updates so the run does not look stuck. Follow-up council challenges and blocker checks stay inside the same skill flow and must come back as synthesized council output, not raw reviewer blocks. The Copilot plugin bundles `plugins/council/copilot-skills/council/SKILL.md` and 27 reviewer `.agent.md` profiles, so the reviewer personas are native custom-agent definitions rather than being rebuilt inside the parent prompt. Those reviewer profiles appear as namespaced custom agents such as `council:antirez-simplicity-reviewer`; that visibility is intentional so the current session agent can invoke them directly.

[Claude documentation ->](./claude/council/README.md) · [Codex skill ->](./plugins/council/skills/council/SKILL.md)

### service-mesh-debug

Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul). Covers 11 root causes: timing races, xDS propagation delays, Gomega misuse (`Expect` inside `Eventually`), pod availability races, mTLS/SDS cert delivery, Envoy circuit breakers, and outlier detection ejection. Includes Python scripts for live Envoy sidecar diagnostics.

**Usage**: `/service-mesh-debug` (auto-triggers on flaky test mentions, `test/e2e/` paths, intermittent CI failures, 503 errors, mTLS failures)

[Full documentation ->](./claude/service-mesh-debug/README.md)

### gh-review-comments

List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Manage code review feedback, reply to reviewer remarks, resolve conversations.

**Usage**: `/gh-review-comments owner/repo 42 [--reply "message"] [--resolve] [--author login]`

[Full documentation ->](./claude/gh-review-comments/README.md)

### git-clean-gone

Clean up local branches with deleted remote tracking and their worktrees. Detects gone branches, squash-merged PRs, and rebased branches.

**Usage**: `/git-clean-gone [--dry-run] [--no-worktrees]`

[Full documentation ->](./claude/git-clean-gone/README.md)

### git-stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Lists hunks with stable IDs, then stages by ID, pattern, file, or line range. Works in scripted and multi-agent environments where `git add -p` is unavailable.

**Usage**: `/git-stage-hunk [--list] [--hunk H1,H2] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--dry-run]`

[Full documentation ->](./claude/git-stage-hunk/README.md)

### go-code-review

Auto-review Go code for 100+ common mistakes from [100go.co](https://100go.co/). Auto-triggers when reviewing `.go` files or Go PRs. Checks error handling, concurrency, interfaces, performance, testing, and stdlib usage with severity tiers and direct mistake references.

**Usage**: `/go-code-review` (auto-triggers on `.go` files and Go PRs)

[Full documentation ->](./claude/go-code-review/README.md)

### humanize

Make text sound natural by removing AI writing patterns. Based on Wikipedia's Signs of AI Writing guide - detects 24 patterns across content, language, style, communication, and filler categories.

**Usage**: `/humanize path/to/file.md [--score-only] [--inline]`

[Full documentation ->](./claude/humanize/README.md)

### kubecon-cfp

Interactive KubeCon CFP submission writer with data-driven insights from 1,100+ accepted talks across 7 KubeCon events (2024-2025). Guides through topic assessment, title crafting, abstract writing, and review scoring.

**Usage**: `/kubecon-cfp [topic or talk idea] [--track AI|Security|Platform|...] [--format session|lightning|tutorial|panel] [--review]`

[Full documentation ->](./claude/kubecon-cfp/README.md)

### promptgen

Turn rough instructions into optimized, evidence-based AI prompts with outcome contracts, model fit, safety boundaries, and verification rules. Copies to clipboard.

**Usage**: `/promptgen <instructions> [--for claude|gpt|codex|generic] [--research light|deep] [--verbose] [--no-copy] [--examples] [--raw]`

[Full documentation ->](./claude/promptgen/README.md)

### refactor-council

Refactoring review through seven sourced refactoring-and-architecture persona agents - Martin Fowler, Robert C. Martin (Uncle Bob), Michael Feathers, Kent Beck, Sandi Metz, John Ousterhout, and Adam Tornhill. Scans the target for code smells and git hotspots, reviews it through opposed lenses (small-functions vs deep-modules, DRY vs duplication, what-to-refactor vs where-to-refactor), synthesizes a safety-first sequenced refactoring plan, then runs a separate adversary agent that red-teams the plan before returning it.

**Usage**: `/refactor-council <path|@file|directory> [--no-scan] [--no-adversary] [--since 12.month] [--personas a,b,c]`

[Full documentation ->](./claude/refactor-council/README.md)

### generate-claude-md

Generate a lean, high-signal CLAUDE.md from codebase analysis. The generator counterpart to `review-claude-md` — it targets the same best-practices rubric the reviewer audits against, with a bundled validator that enforces the reviewer's Critical checks, so output is built to pass that audit. Produces exact commands, an architecture map, and real gotchas while avoiding README duplication, directory trees, and generic advice. Non-destructive: never overwrites an existing CLAUDE.md without `--force`.

**Usage**: `/generate-claude-md [path/to/repo] [--update] [--force] [--rules] [--dry-run]`

[Full documentation ->](./claude/generate-claude-md/README.md)

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation ->](./claude/review-claude-md/README.md)

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

**Usage**: `/test-writer [file-or-function] [--review] [--lang go|python|ts|java|rust]`

[Full documentation ->](./claude/test-writer/README.md)

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
