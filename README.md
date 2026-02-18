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

### Via marketplace

Add the SAI marketplace, then install individual plugins:

```bash
# Add the SAI marketplace
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install individual plugins
/plugin install sai/ai-daily-digest
/plugin install sai/gh-review-comments
/plugin install sai/review-claude-md
/plugin install sai/review-skill
```

Each plugin is independent - install only what you need.

### Local development

Clone the repository and point directly to plugin directories:

```bash
git clone git@github.com:smykla-skalski/sai.git

claude --plugin-dir /path/to/sai/ai-daily-digest
claude --plugin-dir /path/to/sai/gh-review-comments
claude --plugin-dir /path/to/sai/review-claude-md
claude --plugin-dir /path/to/sai/review-skill
```

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
