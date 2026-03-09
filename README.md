# SAI - Skills for Agentic Intelligence

A collection of Claude Code plugins and Codex skills for development workflows, automation, and productivity.

## Overview

This monorepo contains independent plugins, each providing specialized capabilities:

Repository layout:
- `claude/` contains all Claude Code plugins.
- `claude/legacy/` contains inactive plugins (not registered in marketplace).
- `codex/` contains Codex/Codex Desktop skills.

| Plugin                  | Description                                                                             | Installation Path      |
|:------------------------|:----------------------------------------------------------------------------------------|:-----------------------|
| **ai-daily-digest**     | Daily AI news digest covering technical advances, business news, and engineering impact | `claude/ai-daily-digest/`     |
| **gh-review-comments**  | List, reply to, resolve, and create GitHub PR review comment threads                    | `claude/gh-review-comments/`  |
| **git-clean-gone**      | Clean up local branches with deleted remote tracking and their worktrees               | `claude/git-clean-gone/`      |
| **git-stage-hunk**      | Non-interactive hunk staging for selective git add without TTY                          | `claude/git-stage-hunk/`      |
| **humanize**            | Make text sound natural by removing AI writing patterns                                 | `claude/humanize/`            |
| **promptgen**           | Turn rough instructions into optimized, evidence-based AI prompts                       | `claude/promptgen/`           |
| **review-claude-md**    | Audit and fix CLAUDE.md files using tiered binary checklist                             | `claude/review-claude-md/`    |
| **review-skill**        | Review and fix Claude Code skill definitions using tiered binary checklist              | `claude/review-skill/`        |

Codex skills:

| Skill                  | Description                                                                      | Source Path                  |
|:-----------------------|:---------------------------------------------------------------------------------|:-----------------------------|
| **gh-review-comments** | Manage GitHub PR review threads with bundled gh CLI scripts                      | `codex/gh-review-comments/`  |
| **review-skill**       | Audit Codex skills for routing, metadata, shell safety, and approval flow        | `codex/review-skill/`        |

## Installation

### Via marketplace

Add the SAI marketplace, then install individual plugins:

```bash
# Add the SAI marketplace
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install individual plugins
/plugin install sai/ai-daily-digest
/plugin install sai/gh-review-comments
/plugin install sai/git-clean-gone
/plugin install sai/git-stage-hunk
/plugin install sai/humanize
/plugin install sai/promptgen
/plugin install sai/review-claude-md
/plugin install sai/review-skill
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/claude/ai-daily-digest
claude --plugin-dir /path/to/sai/claude/gh-review-comments
claude --plugin-dir /path/to/sai/claude/git-clean-gone
claude --plugin-dir /path/to/sai/claude/git-stage-hunk
claude --plugin-dir /path/to/sai/claude/humanize
claude --plugin-dir /path/to/sai/claude/promptgen
claude --plugin-dir /path/to/sai/claude/review-claude-md
claude --plugin-dir /path/to/sai/claude/review-skill
```

## Plugins

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation ->](./claude/ai-daily-digest/README.md)

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

### humanize

Make text sound natural by removing AI writing patterns. Based on Wikipedia's Signs of AI Writing guide - detects 24 patterns across content, language, style, communication, and filler categories.

**Usage**: `/humanize path/to/file.md [--score-only] [--inline]`

[Full documentation ->](./claude/humanize/README.md)

### promptgen

Turn rough instructions into optimized, evidence-based AI prompts. Built on 35+ academic papers, Anthropic/OpenAI vendor docs, and Mollick/Wharton Prompting Science Reports. Copies to clipboard.

**Usage**: `/promptgen <instructions> [--for claude|gpt|generic] [--verbose] [--no-copy] [--with-examples]`

[Full documentation ->](./claude/promptgen/README.md)

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation ->](./claude/review-claude-md/README.md)

### review-skill

Review and fix Claude Code skill definitions (SKILL.md) using tiered binary checklist based on Agent Skills specification.

**Usage**: `/review-skill [path/to/SKILL.md]`

[Full documentation ->](./claude/review-skill/README.md)

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
