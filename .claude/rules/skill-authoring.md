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

Reference: [claude/humanize/skills/humanize/SKILL.md](claude/humanize/skills/humanize/SKILL.md) for a complete example.

### Invocation control

| Setting | User invokes | Claude invokes | Description in context |
| :-- | :-- | :-- | :-- |
| (default) | yes | yes | yes |
| `disable-model-invocation: true` | yes | no | no |
| `user-invocable: false` | no | yes | yes |

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

Reference: [claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md](claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md) for a 20-phase example.

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

Reference: [claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md](claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md) for the pattern.

## Reference file best practices

- Keep SKILL.md under 500 lines - move detailed content to separate files
- Link reference files with markdown links: `[references/foo.md](references/foo.md)`
- Do NOT use inline code paths (`` `references/foo.md` ``) - Claude Code uses markdown links for progressive disclosure
- Each reference file must be self-contained - never use cross-references like "Use X from SKILL.md Phase N"
- `${CLAUDE_SKILL_DIR}` substitution does NOT work in reference files - agent reads them via Read tool
- Add explicit read gates: "Read [references/foo.md](references/foo.md) before starting Phase 3"

## AskUserQuestion patterns

Use AskUserQuestion when the skill needs user input or approval. Include it in `allowed-tools` for any skill that asks questions.

### When to ask

- **Missing required input**: a required argument was not provided. Ask for it instead of guessing.
- **Ambiguity**: multiple valid interpretations or matches. Present the options and let the user pick.
- **Deviation approval**: the skill needs to change its planned behavior. Get explicit approval before acting.
- **Confirmation gate**: a destructive or irreversible action is about to happen. Confirm first.

### Pattern catalog

**Binary choice** - two options with descriptions explaining the tradeoff:

```
Use AskUserQuestion:
  - Question: "patchutils is not installed. Install it now?"
  - Option 1: "Yes, install" - "Full hunk filtering. Most reliable."
  - Option 2: "No, use fallback" - "Pure-bash parsing. Some modes unavailable."
```

**Dynamic selection** - run a command, parse output, present results as options:

```
Run `git worktree list`, parse the output, and present available
worktrees via AskUserQuestion (each option shows path and branch).
```

**Multi-select with grouping** - use `multiSelect` when the user can pick multiple items. Group by confidence or priority:

```
Use AskUserQuestion with multiSelect to present detected variants.
Group by strength:
- Strong signals (pre-selected): distinct code paths, different output
- Moderate signals (tagged [uncertain]): present with evidence
- Weak signals: mention in description, don't offer as options
```

**Confirmation wizard** - present a summary, offer actions, loop until confirmed:

```
Present the full summary via AskUserQuestion.
Options:
- "Confirm and save"
- "Add a group"
- "Remove a group"
- "Edit a group"
If user picks add/remove/edit: handle the change, then present again.
Loop until user confirms.
```

### Guidelines

- Write the question as a direct sentence, not a paragraph. Put context in option descriptions.
- Each option description should state the consequence, not restate the question.
- For dynamic options (from CLI output, file lists), show enough context per option for the user to decide without switching tools (e.g., path + branch, not just a name).
- Pre-select options that are recommended. Tag uncertain options explicitly.
- Skills with `disable-model-invocation: true` commonly use AskUserQuestion for deviation gates - the user invoked the skill intentionally, so interrupting for approval is expected.
- Do not use AskUserQuestion in spawned agents (Task tool). Agents cannot interact with the user. Use `STATUS: NEEDS_INPUT` patterns instead if the agent hits ambiguity.

## Extended thinking

Include the word "ultrathink" anywhere in skill content to enable extended thinking. Use for complex reasoning skills (multi-tier evaluation, prompt engineering, deep analysis). Increases token usage and response time.

## External integrations

When using MCP tools (Notion, Slack, etc.):

- Document required MCP tools in SKILL.md
- Load deferred tools: `ToolSearch` → `select:mcp__*`
- Verify integration success before updating state

## Tool Usage Patterns

- **AskUserQuestion**: missing input, ambiguity, deviation approval, confirmation gates (see patterns above)
- **WebSearch + WebFetch**: information gathering
- **Read**: config, templates, state files
- **Write**: outputs and state
- **Bash**: git operations, CLI tools
- **Grep/Glob**: file search and verification
- **Task**: spawn verification agents, parallel research

## Skill-scoped hooks

Skill-scoped hooks provide deterministic enforcement of rules that the agent might forget during long runs. A PreToolUse hook that denies an operation physically blocks it regardless of agent behavior.

### Hook script patterns

**Combine related checks into one script** when they share the same event and matcher. For example, multiple PreToolUse/Bash checks (bare kubectl, --validate=false, unrecorded commands) belong in a single `guard-bash.sh`. This avoids spawning multiple processes per tool call.

**Parse stdin JSON once** at the top of every hook script:

```bash
input="$(cat)"
command="$(printf '%s' "${input}" | jq -r '.tool_input.command // ""')"
```

The stdin JSON contains `hook_event_name`, `tool_name`, `tool_input`, `tool_response` (PostToolUse), `error` (PostToolUseFailure), `session_id`, and `last_assistant_message` (SubagentStop).

### Exit codes and output

Exit 2 ignores ALL stdout JSON. Use structured JSON output with exit 0 instead.

**PreToolUse** uses `hookSpecificOutput` with `permissionDecision`:

| Scenario | Exit code | permissionDecision | Effect |
| :-- | :-- | :-- | :-- |
| Block | 0 | `"deny"` | Claude sees reason + fix hint in JSON |
| Warn | 0 | `"allow"` | additionalContext adds context, cmd runs |
| Ask | 0 | `"ask"` | Permission prompt shown to user |
| Clean pass | 0 | (no output) | No overhead |

**PostToolUse, PostToolUseFailure, SubagentStop** use top-level `decision`/`reason` for blocking and `systemMessage` for warnings. They do NOT use `hookSpecificOutput`.

**Stop** hooks use exit 2 + stderr message to force continue (no JSON output parsed on exit 2).

### Universal output fields

These fields work across all hook events: `suppressOutput` (boolean, hide hook output), `systemMessage` (string, shown to user/agent), `continue` (boolean), `stopReason` (string).

### Audit hooks

For silent logging hooks, output `{"suppressOutput":true}` to avoid cluttering the conversation. Log to NDJSON files in `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/`.

### Path syntax in frontmatter

Use `$CLAUDE_PROJECT_DIR` in hook command paths. This is an env var resolved at runtime by the shell.

```yaml
command: "$CLAUDE_PROJECT_DIR/.claude/skills/my-skill/scripts/hooks/my-hook.sh"
```

**Tested path styles (project-local skills):**

| Style | Works? | Why |
| :-- | :-- | :-- |
| `$CLAUDE_PROJECT_DIR/path/to/hook` | Yes | Env var resolved by shell at runtime |
| Absolute hardcoded path | Yes | Always works, not portable |
| `${CLAUDE_SKILL_DIR}/path/to/hook` | No | String substitution applies to body, not hooks |
| Relative (`scripts/hooks/foo.sh`) | No | cwd is project root, not SKILL.md directory |

Four handler types exist: `command`, `http`, `prompt`, `agent`.

### Known limitations

**Plugin hooks are broken** (GitHub issue #17688). Hooks defined in SKILL.md frontmatter do not fire when the skill is loaded via a plugin (`--plugin-dir` or marketplace install). The plugin loader omits the `cH5()` hooks parser call. Only project-local skills (`.claude/skills/`) fire hooks. No fix as of Claude Code 2.1.63.

| Component | Location | Hooks |
| :-- | :-- | :-- |
| Project skill | `.claude/skills/` | Work |
| Project agent | `.claude/agents/` | Work |
| Plugin skill (any) | `--plugin-dir` | Broken |
| Plugin agent (any) | marketplace | Broken |

### Error codes

Use a consistent prefix per skill (e.g., `PLG001` for my-plugin). Follow the `[CODE] message. Hint.` format in `permissionDecisionReason`.

### Environment variables

Available as env vars inside hook scripts at runtime:

- `CLAUDE_PROJECT_DIR` - project root (always available, use for hook paths)
- `CLAUDE_PLUGIN_ROOT` - plugin root (plugin hooks only, broken per #17688)

NOT available as env vars in hook scripts (body-only string substitution):

- `CLAUDE_SKILL_DIR` - only substituted in SKILL.md body content
- `CLAUDE_SESSION_ID` - only substituted in SKILL.md body content

### Infinite loop prevention

SubagentStop and Stop hooks must check `stop_hook_active` from stdin JSON. If true, exit 0 immediately to prevent recursive hook firing.

## Plugin Integration

- Install: `claude --plugin-dir claude/{plugin-name}/`
- Invoke: `/{skill-name} [args]`
- Arguments: parsed from `$ARGUMENTS` env var
- Tool restrictions: `allowed-tools` frontmatter
- Version: independent semver per plugin
