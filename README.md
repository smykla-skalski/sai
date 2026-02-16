# SAI - Skills for Agentic Intelligence

A Claude Code plugin providing specialized capabilities for development workflows, automation, and productivity.

## Overview

SAI is a collection of skills that agents can invoke to perform common development tasks:

- Code review automation
- Documentation generation
- PR management
- Project maintenance
- Development workflow optimization
- AI news and insights gathering

## Installation

Install the SAI plugin in Claude Code:

```bash
# Install from this repository
claude --plugin-dir /path/to/this/repo

# Or install from marketplace (once published)
/plugin install sai@sai-skills
```

## Usage

Once installed, invoke skills using the namespaced command format:

```bash
/sai:ai-daily-digest
```

Or without namespace if no conflicts:

```bash
/ai-daily-digest
```

## Available Skills

### ai-daily-digest

Generate curated AI news digests from multiple sources with intelligent deduplication and Notion integration.

**Usage**: `/sai:ai-daily-digest [--date YYYY-MM-DD] [--skip-notion]`

## Plugin Structure

```
.
├── .claude-plugin/
│   ├── plugin.json         # Plugin metadata
│   └── marketplace.json    # Marketplace configuration
├── skills/
│   └── ai-daily-digest/    # Each skill in its own directory
│       ├── SKILL.md        # Skill definition
│       ├── sources.md      # Data sources
│       └── output-template.md
└── findings/               # Runtime state (gitignored)
```

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed documentation on:

- Creating new skills
- Skill definition format
- Workflow patterns
- State management
- Testing and contribution guidelines
