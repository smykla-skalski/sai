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
# Add the marketplace
/plugin marketplace add git@github.com:smykla-skalski/skills.git

# Install the plugin
/plugin install sai@sai-skills

# Restart Claude Code to load the plugin
```

Or for local development:

```bash
# Install from local directory
claude --plugin-dir /path/to/this/repo
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

### review-claude-md

Audit, score, and fix CLAUDE.md files against a 100-point rubric based on official Anthropic best practices and community guidelines. Iterates until the target grade is achieved.

**Usage**: `/sai:review-claude-md [path/to/repo] [--score-only] [--strict] [--target 95|A+]`

### review-skill

Audit, score, and fix Claude Code skill definitions (SKILL.md) against a 100-point rubric based on the official Agent Skills specification, Anthropic's skill-creator, and community guidelines. Iterates until the target grade is achieved.

**Usage**: `/sai:review-skill [path/to/skill] [--score-only] [--strict] [--target 95|A+]`

## Plugin Structure

```
.
├── .claude-plugin/
│   ├── plugin.json         # Plugin metadata
│   └── marketplace.json    # Marketplace configuration
├── skills/
│   ├── ai-daily-digest/    # AI news digest skill
│   │   ├── SKILL.md
│   │   ├── sources.md
│   │   └── output-template.md
│   ├── review-claude-md/   # CLAUDE.md review & fix skill
│   │   └── SKILL.md
│   └── review-skill/       # Skill definition review & fix
│       └── SKILL.md
└── findings/               # Runtime state (gitignored)
```

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed documentation on:

- Creating new skills
- Skill definition format
- Workflow patterns
- State management
- Testing and contribution guidelines

## Repository

- **GitHub**: git@github.com:smykla-skalski/skills.git
- **Marketplace ID**: `sai-skills`
- **Plugin Name**: `sai`

## Contributing

To contribute new skills or improvements:

1. Fork the repository
2. Create a feature branch
3. Add your skill to `skills/` directory
4. Follow the skill definition format in CLAUDE.md
5. Test locally with `claude --plugin-dir .`
6. Submit a pull request
