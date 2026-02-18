# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository is a **monorepo of Claude Code plugins** called **SAI (Skills for Agentic Intelligence)**. Each plugin contains a single skill for agentic programming workflows. Skills are specialized capabilities that agents (like Claude Code) can invoke to perform complex, multi-step tasks such as code review automation, documentation generation, PR management, project maintenance, and development workflow optimization.

## Plugin Architecture

Each plugin follows the Claude Code plugin structure:

- **Plugin metadata**: `{plugin-name}/.claude-plugin/plugin.json` defines name, version, and description
- **Skill definition**: `{plugin-name}/SKILL.md` at plugin root (flat structure)
- **Supporting files**: `{plugin-name}/references/`, `{plugin-name}/scripts/`, etc.
- **Runtime state**: `{plugin-name}/findings/` (gitignored)
- **Independent versioning**: Each plugin has its own version

## Repository Structure

```
.
├── ai-daily-digest/
│   ├── .claude-plugin/
│   │   └── plugin.json     # Plugin metadata
│   ├── SKILL.md            # Skill definition at plugin root
│   ├── sources.md          # Data sources, search patterns
│   ├── output-template.md  # Output format template
│   ├── references/         # Supporting documentation
│   ├── findings/           # Runtime state (gitignored)
│   └── README.md           # Plugin-specific docs
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
├── CLAUDE.md               # This file - development guide
├── CONTRIBUTING.md
└── README.md
```

## Skill Definition Format

Each skill MUST have a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: skill-name
description: Brief description of what the skill does and when to use it
argument-hint: "[--flag value] [optional-args]"
allowed-tools: WebSearch, WebFetch, Read, Write, Bash, Grep, Glob
user-invocable: true
---

# Skill Name

Detailed skill instructions...
```

### Frontmatter Fields

- **name** (required): Kebab-case skill identifier (e.g., `ai-daily-digest`)
- **description** (required): One-sentence summary including use cases
- **argument-hint** (optional): Command-line style hint for arguments
- **allowed-tools** (required): Comma-separated list of tools the skill can use
- **user-invocable** (required): Boolean - whether users can invoke via `/skill-name`

### Skill Body Structure

The SKILL.md body should contain:

1. **Overview section**: What the skill does
2. **Arguments section**: Parse from `$ARGUMENTS` with supported flags
3. **State Files section**: Document any persistent state files (location, format, purpose)
4. **Workflow section**: Step-by-step phases for execution
5. **Output Requirements**: Format, validation, delivery
6. **Error Handling**: Failure modes and recovery
7. **Example Invocations**: Usage examples

## Skill Workflow Patterns

### Phase-Based Execution

Complex skills should be organized into numbered phases (see `ai-daily-digest/SKILL.md` for reference):

- **Phase 1: Setup** - Read config, parse args, load state
- **Phase N: Data Collection** - Gather information from sources
- **Phase N+1: Synthesis** - Process and deduplicate
- **Phase N+2: Output Generation** - Create artifacts
- **Phase N+3: State Persistence** - Save tracking files
- **Phase N+4: Verification** - Spawn verification agent if needed

### State Management

Skills that run periodically should track state in `{plugin-name}/findings/`:

- Use hidden files for state (`.last-run`, `.covered-items`)
- Document state file format in SKILL.md
- Read state on startup, update on successful completion
- Keep state files under size limits (e.g., last 300 entries)

### External Integrations

When integrating with external services (Notion, Slack, etc.):

- Document required MCP tools in SKILL.md
- Use deferred tool loading pattern (`ToolSearch` → `select:mcp__*`)
- Verify integration success before updating state
- Include integration step in workflow phases

## Creating New Plugins

When adding a new plugin to the SAI monorepo:

1. Create plugin directory: `mkdir {plugin-name}/`
2. Create `.claude-plugin/plugin.json` with metadata (start at v1.0.0)
3. Create `SKILL.md` at plugin root with required frontmatter
4. Add supporting files if needed (references/, scripts/, templates)
5. Create `findings/` directory if plugin needs runtime state
6. Create `README.md` with installation and usage instructions
7. Update root `README.md` to list the new plugin
8. Test: `claude --plugin-dir {plugin-name}/`

## Conventions from Existing Skills

### ai-daily-digest Skill

This skill demonstrates several important patterns:

- **Multi-phase workflow** with 20 distinct phases
- **State tracking** using `.last-run` and `.covered-stories` files
- **Deduplication** via story IDs and covered URL tracking
- **External integration** with Notion API
- **Verification agent** spawned for quality assurance
- **Source management** via separate `sources.md` file
- **Output templating** with markdown template file
- **Date-based variations** (Friday weekly recap mode)

Key architectural decisions:

- Deduplication happens BEFORE digest generation (Phase 16)
- State files updated AFTER verification passes (Phase 20)
- Verification agent is separate to avoid polluting context
- Story IDs enable fuzzy matching across different URLs

## Tool Usage Patterns

Skills commonly use these tool patterns:

- **WebSearch + WebFetch**: Information gathering from web sources
- **Read**: Loading configuration, templates, and state files
- **Write**: Saving outputs and state files
- **Bash**: Git operations, file system commands, external CLI tools
- **Grep**: Searching within files for verification
- **Glob**: Finding files by pattern
- **Task (spawning agents)**: Verification, parallel research tasks

## Integration Points

### Claude Code Plugin System

Each plugin integrates with Claude Code via:

- **Plugin installation**: `claude --plugin-dir {plugin-name}/`
- **Skill invocation**: `/{plugin-name} [args]` or `/{skill-name} [args]`
- **Argument parsing**: From `$ARGUMENTS` environment variable
- **Tool restrictions**: Via `allowed-tools` frontmatter
- **User invocability**: Via `user-invocable: true`
- **Version management**: Independent semantic versioning per plugin

### MCP (Model Context Protocol) Tools

Skills can use MCP-provided tools:

- Notion API: `mcp__notion__notion-create-pages`
- Other integrations as needed
- Load via `ToolSearch` before first use

## Common Pitfalls

- **Don't update state prematurely**: Update tracking files AFTER successful completion
- **Verify external integrations**: Confirm API calls succeed before marking complete
- **Deduplicate early**: Filter duplicates BEFORE generating output
- **Use verification agents**: Spawn separate agents for quality checks to avoid context pollution
- **Document state format**: Future skill runs depend on parsing state correctly
- **Handle missing state gracefully**: First run often has no state files
