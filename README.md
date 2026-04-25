# SAI - Skills for Agentic Intelligence

A collection of Claude Code plugins and Codex skills for development workflows, automation, and productivity.

## Overview

This monorepo contains independent plugins, each providing specialized capabilities:

Repository layout:
- `claude/` contains all Claude Code plugins.
- `codex/` contains Codex/Codex Desktop skills.

| Plugin                  | Description                                                                             | Installation Path      |
|:------------------------|:----------------------------------------------------------------------------------------|:-----------------------|
| **ai-daily-digest**     | Daily AI news digest covering technical advances, business news, and engineering impact | `claude/ai-daily-digest/`     |
| **service-mesh-debug**  | Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul) | `claude/service-mesh-debug/`  |
| **gh-review-comments**  | List, reply to, resolve, and create GitHub PR review comment threads                    | `claude/gh-review-comments/`  |
| **git-clean-gone**      | Clean up local branches with deleted remote tracking and their worktrees               | `claude/git-clean-gone/`      |
| **git-stage-hunk**      | Non-interactive hunk staging for selective git add without TTY                          | `claude/git-stage-hunk/`      |
| **go-code-review**      | Auto-review Go code for 100+ common mistakes from 100go.co                              | `claude/go-code-review/`      |
| **humanize**            | Make text sound natural by removing AI writing patterns                                 | `claude/humanize/`            |
| **kubecon-cfp**         | Interactive KubeCon CFP submission writer with data-driven insights                    | `claude/kubecon-cfp/`         |
| **promptgen**           | Turn rough instructions into optimized, evidence-based AI prompts                       | `claude/promptgen/`           |
| **review-claude-md**    | Audit and fix CLAUDE.md files using tiered binary checklist                             | `claude/review-claude-md/`    |
| **review-skill**        | Review and fix Claude Code skill definitions using tiered binary checklist              | `claude/review-skill/`        |
| **slug**                | Generate a semantic slug for the current session and copy `/rename` command to clipboard | `claude/slug/`                |
| **staff-code-review**   | Staff-engineer-level code review: architecture, reliability, security, cross-team impact | `claude/staff-code-review/`   |
| **staff-resume**        | Build and refine staff-level engineering resumes through interactive coaching           | `claude/staff-resume/`        |
| **test-writer**         | Write behavior-driven tests with table-driven patterns and minimal mocking             | `claude/test-writer/`         |

Codex skills:

| Skill                  | Description                                                                      | Source Path                  |
|:-----------------------|:---------------------------------------------------------------------------------|:-----------------------------|
| **gh-review-comments** | Manage GitHub PR review threads with bundled gh CLI scripts                      | `codex/gh-review-comments/`  |
| **promptgen**           | Turn rough instructions into stronger prompts using the Claude promptgen source workflow | `codex/promptgen/`            |
| **review-skill**       | Audit Codex skills for routing, metadata, shell safety, and approval flow        | `codex/review-skill/`        |

## Installation

### Via marketplace

Add the SAI marketplace, then install individual plugins:

```bash
# Add the SAI marketplace
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install individual plugins
/plugin install sai/ai-daily-digest
/plugin install sai/service-mesh-debug
/plugin install sai/gh-review-comments
/plugin install sai/git-clean-gone
/plugin install sai/git-stage-hunk
/plugin install sai/go-code-review
/plugin install sai/humanize
/plugin install sai/kubecon-cfp
/plugin install sai/promptgen
/plugin install sai/review-claude-md
/plugin install sai/review-skill
/plugin install sai/slug
/plugin install sai/staff-code-review
/plugin install sai/staff-resume
/plugin install sai/test-writer
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/claude/ai-daily-digest
claude --plugin-dir /path/to/sai/claude/service-mesh-debug
claude --plugin-dir /path/to/sai/claude/gh-review-comments
claude --plugin-dir /path/to/sai/claude/git-clean-gone
claude --plugin-dir /path/to/sai/claude/git-stage-hunk
claude --plugin-dir /path/to/sai/claude/go-code-review
claude --plugin-dir /path/to/sai/claude/humanize
claude --plugin-dir /path/to/sai/claude/kubecon-cfp
claude --plugin-dir /path/to/sai/claude/promptgen
claude --plugin-dir /path/to/sai/claude/review-claude-md
claude --plugin-dir /path/to/sai/claude/review-skill
claude --plugin-dir /path/to/sai/claude/staff-code-review
claude --plugin-dir /path/to/sai/claude/staff-resume
claude --plugin-dir /path/to/sai/claude/test-writer
```

## Plugins

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation ->](./claude/ai-daily-digest/README.md)

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

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation ->](./claude/review-claude-md/README.md)

### review-skill

Review and fix Claude Code skill definitions (SKILL.md) using tiered binary checklist based on Agent Skills specification.

**Usage**: `/review-skill [path/to/SKILL.md]`

[Full documentation ->](./claude/review-skill/README.md)

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
