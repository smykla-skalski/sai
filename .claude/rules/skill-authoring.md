# Skill Authoring Guide

## SKILL.md Frontmatter (Required)

```yaml
---
name: skill-name           # Kebab-case identifier
description: Brief desc    # One sentence, include use cases
argument-hint: "[--flags]" # Optional CLI-style hint
allowed-tools: Read, Write, Bash, Grep, Glob  # Comma-separated
user-invocable: true       # Boolean
---
```

Reference: `humanize/skills/humanize/SKILL.md` for a complete example.

## SKILL.md Body Structure

1. Overview: what the skill does
2. Arguments: parse from `$ARGUMENTS`, document flags
3. State Files: location, format, purpose (if any)
4. Workflow: numbered phases for execution
5. Output Requirements: format and validation
6. Error Handling: failure modes and recovery
7. Example Invocations: usage examples

## Phase-Based Execution

Organize complex skills into numbered phases:

- Phase 1: Setup — read config, parse args, load state
- Phase N: Data collection — gather from sources
- Phase N+1: Synthesis — process and deduplicate
- Phase N+2: Output — create artifacts
- Phase N+3: State persistence — save tracking files
- Phase N+4: Verification — spawn separate agent for QA

Reference: `ai-daily-digest/skills/ai-daily-digest/SKILL.md` for a 20-phase example.

## State Management

Skills that run periodically track state in `{plugin-name}/findings/`:

- Use hidden files (`.last-run`, `.covered-items`)
- Document state file format in SKILL.md
- Read on startup, update on successful completion only
- Keep state files bounded (e.g., last 300 entries)

## External Integrations

When using MCP tools (Notion, Slack, etc.):

- Document required MCP tools in SKILL.md
- Load deferred tools: `ToolSearch` → `select:mcp__*`
- Verify integration success before updating state

## Tool Usage Patterns

- **WebSearch + WebFetch**: information gathering
- **Read**: config, templates, state files
- **Write**: outputs and state
- **Bash**: git operations, CLI tools
- **Grep/Glob**: file search and verification
- **Task**: spawn verification agents, parallel research

## Plugin Integration

- Install: `claude --plugin-dir {plugin-name}/`
- Invoke: `/{skill-name} [args]`
- Arguments: parsed from `$ARGUMENTS` env var
- Tool restrictions: `allowed-tools` frontmatter
- Version: independent semver per plugin
