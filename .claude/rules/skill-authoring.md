# Skill Authoring Guide

## SKILL.md frontmatter

All fields are optional. Claude Code infers `name` from directory and `description` from the first paragraph if omitted.

```yaml
---
name: skill-name                    # Kebab-case, max 64 chars. Default: directory name
description: Brief desc             # One sentence with use cases. Used for auto-invocation
argument-hint: "[--flags]"          # CLI-style hint shown in autocomplete
allowed-tools: Bash, Glob, Read     # Comma-separated, alphabetical. Tool(specifier) supported
user-invocable: true                # false = hidden from / menu, still auto-invocable
disable-model-invocation: false     # true = user-only, Claude never auto-invokes, description not loaded
model: claude-sonnet-4-6            # Override session model for this skill
context: fork                       # Run in isolated subagent (no conversation history)
agent: general-purpose              # Subagent type when context: fork (Explore, Plan, general-purpose)
hooks:                              # Skill-scoped lifecycle hooks (same format as settings.json)
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: "command"
          command: "echo 'pre-bash hook'"
---
```

Reference: `claude/humanize/skills/humanize/SKILL.md` for a complete example.

### Invocation control

| Setting                          | User invokes | Claude invokes | Description in context |
| :------------------------------- | :----------- | :------------- | :--------------------- |
| (default)                        | yes          | yes            | yes                    |
| `disable-model-invocation: true` | yes          | no             | no                     |
| `user-invocable: false`          | no           | yes            | yes                    |

Use `disable-model-invocation: true` for skills with side effects (cluster creation, branch deletion, staging area changes) to prevent accidental auto-invocation.

### Subagent execution (context: fork)

When `context: fork` is set, the skill runs in an isolated subagent:

- Skill content becomes the subagent's prompt
- Subagent receives NO conversation history
- Must include explicit instructions (not just guidelines)
- Agent type determines execution environment
- Results are summarized and returned to main conversation

This is different from spawning agents with the Task tool inside a skill. Use `context: fork` when the entire skill is self-contained. Use Task-based spawning when only specific phases need isolation.

## String substitutions

Available in SKILL.md content only (not in reference files):

- `$ARGUMENTS` - all arguments passed when invoking the skill
- `$ARGUMENTS[N]` / `$N` - specific argument by 0-based index (`$0` = first)
- `${CLAUDE_SKILL_DIR}` - absolute path to the directory containing SKILL.md (string substitution, not an env var)
- `${CLAUDE_SESSION_ID}` - current session UUID, useful for logging or session-specific files

If `$ARGUMENTS` is not present in content, Claude Code appends `ARGUMENTS: <value>` at the end.

## Shell preprocessing

Commands inside `` !`...` `` run BEFORE skill content is sent to Claude. Output replaces the placeholder.

```yaml
---
name: pr-summary
description: Summarize PR changes
---
## Context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
```

Claude receives the command output, not the commands. Useful for injecting current repo state, but less flexible than Bash tool calls during workflow since it runs at load time only.

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

Reference: `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md` for a 20-phase example.

## State Management

Skills that need persistent state or artifacts MUST use an XDG-compliant path outside the plugin cache. Plugin cache directories are replaced on version updates — any files written there will be lost.

**Persistent data directory pattern:**

```
${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/
```

Resolve this path once in the setup phase via Bash and store as a variable (e.g., `DATA_DIR`). Use the resolved absolute path for all subsequent file operations.

**Do NOT use:**

- `./findings/` — ambiguous, may resolve to plugin cache
- `${CLAUDE_SKILL_DIR}/findings/` — inside plugin cache, lost on update
- Any relative paths for persistent state

**Guidelines:**

- Use hidden files for tracking state (`.last-run`, `.covered-items`)
- Document state file format in SKILL.md
- Read on startup, update on successful completion only
- Keep state files bounded (e.g., last 300 entries)

Reference: `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md` for the pattern.

## Reference file best practices

- Keep SKILL.md under 500 lines - move detailed content to separate files
- Link reference files with markdown links: `[references/foo.md](references/foo.md)`
- Do NOT use inline code paths (`` `references/foo.md` ``) - Claude Code uses markdown links for progressive disclosure
- Each reference file must be self-contained - never use cross-references like "Use X from SKILL.md Phase N"
- `${CLAUDE_SKILL_DIR}` substitution does NOT work in reference files - agent reads them via Read tool
- Add explicit read gates: "Read [references/foo.md](references/foo.md) before starting Phase 3"

## Extended thinking

Include the word "ultrathink" anywhere in skill content to enable extended thinking. Use for complex reasoning skills (multi-tier evaluation, prompt engineering, deep analysis). Increases token usage and response time.

## External integrations

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

- Install: `claude --plugin-dir claude/{plugin-name}/`
- Invoke: `/{skill-name} [args]`
- Arguments: parsed from `$ARGUMENTS` env var
- Tool restrictions: `allowed-tools` frontmatter
- Version: independent semver per plugin
