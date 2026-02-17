# SAI - Skills for Agentic Intelligence

A collection of independent Claude Code plugins for development workflows, automation, and productivity.

## Overview

This monorepo contains 4 independent plugins, each providing specialized capabilities:

| Plugin | Description | Installation Path |
|--------|-------------|-------------------|
| **ai-daily-digest** | Daily AI news digest covering technical advances, business news, and engineering impact | `ai-daily-digest/` |
| **gh-review-comments** | List, reply to, resolve, and create GitHub PR review comment threads | `gh-review-comments/` |
| **review-claude-md** | Audit and fix CLAUDE.md files using tiered binary checklist | `review-claude-md/` |
| **review-skill** | Review and fix Claude Code skill definitions using tiered binary checklist | `review-skill/` |

## Installation

Install plugins individually by pointing to their directory:

```bash
# Install ai-daily-digest
claude --plugin-dir /path/to/sai/ai-daily-digest

# Install gh-review-comments
claude --plugin-dir /path/to/sai/gh-review-comments

# Install review-claude-md
claude --plugin-dir /path/to/sai/review-claude-md

# Install review-skill
claude --plugin-dir /path/to/sai/review-skill
```

Each plugin is independent - install only what you need.

## Plugins

### ai-daily-digest

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters.

**Usage**: `/ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

[Full documentation →](./ai-daily-digest/README.md)

### gh-review-comments

List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Manage code review feedback, reply to reviewer remarks, resolve conversations.

**Usage**: `/gh-review-comments list <pr-url>`, `/gh-review-comments reply <pr-url> <thread-id> <message>`

[Full documentation →](./gh-review-comments/README.md)

### review-claude-md

Audit and fix CLAUDE.md files using tiered binary checklist based on Anthropic best practices and community guidelines.

**Usage**: `/review-claude-md [path/to/CLAUDE.md]`

[Full documentation →](./review-claude-md/README.md)

### review-skill

Review and fix Claude Code skill definitions (SKILL.md) using tiered binary checklist based on Agent Skills specification.

**Usage**: `/review-skill [path/to/SKILL.md]`

[Full documentation →](./review-skill/README.md)

## Repository Structure

```
.
├── ai-daily-digest/
│   ├── .claude-plugin/plugin.json
│   ├── SKILL.md
│   ├── sources.md
│   ├── output-template.md
│   ├── references/
│   ├── findings/            # gitignored runtime state
│   └── README.md
├── gh-review-comments/
│   ├── .claude-plugin/plugin.json
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── README.md
├── review-claude-md/
│   ├── .claude-plugin/plugin.json
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── README.md
├── review-skill/
│   ├── .claude-plugin/plugin.json
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── README.md
├── CLAUDE.md              # Development guide
├── CONTRIBUTING.md
└── README.md
```

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
4. Test locally with `claude --plugin-dir {plugin-name}/`
5. Submit a pull request

## License

MIT - See [LICENSE](./LICENSE)

## Repository

- **GitHub**: https://github.com/smykla-skalski/sai
