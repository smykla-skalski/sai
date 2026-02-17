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
/plugin marketplace add git@github.com:smykla-skalski/sai.git

# Install the plugin
/plugin install sai@skills

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

Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters. Use daily for staying current on AI developments.

**Usage**: `/sai:ai-daily-digest [--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]`

### gh-review-comments

List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Use when managing code review feedback, replying to reviewer remarks, resolving review conversations, creating reviews with line-level comments, or bulk-processing threads by author.

**Usage**: `/sai:gh-review-comments <owner/repo> <pr-number> [--author <login>] [--reply <message>] [--resolve] [--unresolve] [--create-review] [--thread-id <id>] [--unresolved-only]`

### review-claude-md

Audit and fix CLAUDE.md files using a tiered binary checklist based on official Anthropic best practices and community guidelines. Use when the user asks to "review CLAUDE.md", "audit CLAUDE.md", "score CLAUDE.md", "improve CLAUDE.md", or "fix CLAUDE.md".

**Usage**: `/sai:review-claude-md [path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]`

### review-skill

Review and fix Claude Code skill definitions (SKILL.md) using a tiered binary checklist based on the Agent Skills specification, Anthropic best practices, and community guidelines. Use when auditing, improving, or validating any skill before publishing.

**Usage**: `/sai:review-skill [path/to/skill] [--score-only] [--fix] [--verbose] [--thorough]`

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed documentation on:

- Creating new skills
- Skill definition format
- Workflow patterns
- State management
- Testing and contribution guidelines

## Repository

- **GitHub**: `git@github.com:smykla-skalski/sai.git`
- **Marketplace ID**: `skills`
- **Plugin Name**: `sai`

## Contributing

To contribute new skills or improvements:

1. Fork the repository
2. Create a feature branch
3. Add your skill to `skills/` directory
4. Follow the skill definition format in CLAUDE.md
5. Test locally with `claude --plugin-dir .`
6. Submit a pull request
