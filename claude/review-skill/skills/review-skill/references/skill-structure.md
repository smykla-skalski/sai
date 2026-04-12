# Contents

1. [Canonical skill layout](#canonical-skill-layout)
2. [Why resources live alongside SKILL.md](#why-resources-live-alongside-skillmd)
3. [Plugin vs skill directories](#plugin-vs-skill-directories)
4. [Path resolution at runtime](#path-resolution-at-runtime)
5. [String substitutions in skill content](#string-substitutions-in-skill-content)
6. [Frontmatter fields](#frontmatter-fields)
7. [Progressive loading](#progressive-loading)
8. [Compaction behavior](#compaction-behavior)
9. [Extended thinking](#extended-thinking)
10. [Hook field reference](#hook-field-reference)
11. [Custom agents](#custom-agents)
12. [Sources](#sources)

---

## Canonical skill layout

Per the Agent Skills specification and Anthropic's official documentation, the canonical skill directory structure is:

```
skill-name/
├── SKILL.md           # Required - entrypoint
├── references/        # Documentation loaded into context on demand
├── scripts/           # Executable code (Python, Bash, etc.)
├── assets/            # Files used in output (templates, icons, fonts)
└── examples/          # Example files showing expected format
```

All bundled resources live **alongside SKILL.md** in the skill directory. This applies whether the skill is standalone, project-scoped, personal, or part of a plugin.

Plugins can also have a `bin/` directory at the plugin root (not inside the skill) whose executables are added to the Bash tool's PATH while the plugin is enabled.

## Why resources live alongside SKILL.md

1. **Runtime path resolution.** Claude Code provides the skill's base path at invocation time, pointing to the directory containing SKILL.md. Relative paths in SKILL.md (`references/api.md`, `scripts/validate.py`) resolve from this directory.

2. **Progressive loading.** Bundled resources are not loaded automatically. Claude reads them on demand when SKILL.md references them. Placing them alongside SKILL.md makes the reference paths straightforward.

3. **Self-contained skills.** A skill directory is a portable unit. Moving `skill-name/` to another location (different plugin, project `.claude/skills/`, personal `~/.claude/skills/`) should work without path adjustments.

## Plugin vs skill directories

A plugin is a container that can hold one or more skills:

```
my-plugin/                          # Plugin root
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest
├── skills/                         # Default skill scan location
│   └── my-skill/                   # Skill directory
│       ├── SKILL.md                # Skill entrypoint
│       ├── references/             # Skill-scoped references
│       │   └── api-spec.md
│       └── scripts/                # Skill-scoped scripts
│           └── helper.sh
├── agents/                         # Subagent definitions
├── hooks/hooks.json                # Hook configurations
├── bin/                            # Executables added to PATH
├── .mcp.json                       # MCP server definitions
├── .lsp.json                       # LSP server configurations
└── README.md                       # Plugin docs (NOT in skill dir)
```

Two distinct levels exist:

| Location | Purpose | Path variable |
| :-- | :-- | :-- |
| `{plugin-root}/` | Plugin metadata, hooks, MCP, agents | `${CLAUDE_PLUGIN_ROOT}` |
| `{plugin-root}/skills/{name}/` | Skill entrypoint, resources | `${CLAUDE_SKILL_DIR}` |

## Path resolution at runtime

When a skill is invoked, Claude Code provides the skill's **base path** in the system context. This path points to the directory containing SKILL.md, not the plugin root.

| Context | Available path | Resolves to |
| :-- | :-- | :-- |
| Hook/MCP/LSP JSON configs | `${CLAUDE_PLUGIN_ROOT}` | Plugin root directory (changes on update) |
| Hook/MCP/LSP JSON configs | `${CLAUDE_PLUGIN_DATA}` | Persistent data directory (survives updates) |
| Skill markdown content | `${CLAUDE_SKILL_DIR}` | Skill directory (contains SKILL.md) |

`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` are available in hook commands, MCP server configs, and LSP server configs. They are also exported as environment variables to hook processes and server subprocesses.

`${CLAUDE_SKILL_DIR}` is an official string substitution available in SKILL.md content. Claude Code replaces it with the literal absolute path to the skill directory before the agent sees the content. Use it for script invocations and file references in SKILL.md. It is not available in reference files - those are read by the agent via the Read tool without substitution.

## String substitutions in skill content

These placeholders are replaced by Claude Code before the agent receives the skill content:

| Variable | Description |
| :-- | :-- |
| `$ARGUMENTS` | Full argument string passed when invoking the skill |
| `$ARGUMENTS[N]` | Access a specific argument by 0-based index (shell-style quoting) |
| `$N` | Shorthand for `$ARGUMENTS[N]` (e.g., `$0` for first argument) |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing this skill's SKILL.md |

If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: <value>`.

## Frontmatter fields

All fields are optional. Only `description` is recommended.

| Field | Description |
| :-- | :-- |
| `name` | Display name. Lowercase letters, numbers, hyphens. Max 64 chars. Defaults to directory name. |
| `description` | What the skill does and when to use it. Truncated at 250 chars in the skill listing. Max 1,024 chars. Front-load the key use case. |
| `argument-hint` | Hint shown during autocomplete (e.g., `[issue-number]`). |
| `disable-model-invocation` | Set `true` to prevent Claude from auto-loading this skill. |
| `user-invocable` | Set `false` to hide from the `/` menu. |
| `allowed-tools` | Tools pre-approved when skill is active. Space-separated string or YAML list. |
| `model` | Model to use when this skill is active. |
| `effort` | Effort level override: `low`, `medium`, `high`, `max` (max is Opus 4.6 only). |
| `context` | Set to `fork` to run in a forked subagent context. |
| `agent` | Subagent type when `context: fork`. Built-in: `Explore`, `Plan`, `general-purpose`. Also accepts custom agent names from `.claude/agents/`. |
| `hooks` | Hooks scoped to this skill's lifecycle. |
| `paths` | Glob patterns limiting when this skill auto-activates. Comma-separated string or YAML list. |
| `shell` | Shell for preprocessing commands: `bash` (default) or `powershell`. |
| `compatibility` | Environment requirements (Agent Skills spec). Max 500 chars. |

## Progressive loading

Skills use a three-level progressive disclosure system:

1. **Metadata (always in context, ~100 tokens).** The `name` and `description` from YAML frontmatter are always loaded into the available skills list. Descriptions are truncated at 250 characters in the listing. The total budget for all skill descriptions scales at 1% of the context window (fallback 8,000 chars), configurable via `SLASH_COMMAND_TOOL_CHAR_BUDGET`.

2. **SKILL.md body (loaded on trigger, target <5k tokens).** The full markdown content loads when the user invokes `/skill-name` or when Claude determines the skill is relevant. Keep the body under 5,000 tokens for full compaction survival.

3. **Bundled resources (loaded on demand, unlimited).** Files in `references/`, `scripts/`, `assets/`, `examples/` are read only when Claude decides they are needed, based on references in SKILL.md. This is why SKILL.md should mention all bundled files.

## Compaction behavior

When auto-compaction fires, Claude Code re-attaches the most recent invocation of each skill after the summary:

- Each skill gets at most **5,000 tokens** preserved.
- All re-attached skills share a combined budget of **25,000 tokens**.
- The budget fills starting from the **most recently invoked** skill.
- Older skills can be dropped entirely if many were invoked in one session.

Skills exceeding 5,000 tokens in their body will lose content after compaction. Extract detail-heavy sections to `references/` files so the core instructions survive.

## Extended thinking

Include the word `ultrathink` anywhere in a skill's SKILL.md content to set effort to `high` for that turn. Works on Opus 4.6 and Sonnet 4.6. Has no effect if the session effort is already `high` or `max`. This is a one-shot keyword - it does not persist across turns. The `effort` frontmatter field is the persistent alternative.

Words like "think", "think hard", and "think more" do NOT allocate thinking tokens. Only `ultrathink` is a recognized keyword.

## Hook field reference

Skill-scoped hooks are declared in frontmatter under the `hooks:` key. Each hook entry has a `type` and type-specific fields.

**Common fields (all types):**

| Field | Type | Description |
| :-- | :-- | :-- |
| `type` | string, required | `command`, `http`, `prompt`, or `agent` |
| `if` | string | Permission rule filter (e.g. `Bash(git *)`, `Edit(*.ts)`). Only evaluated on tool events: PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionDenied. A hook with `if` set never runs on other events. |
| `timeout` | number | Seconds before canceling. Defaults: 600 (command), 30 (prompt), 60 (agent). |
| `statusMessage` | string | Custom spinner text while the hook runs. |
| `once` | boolean | Run once per session then removed. Skills only, not agents. |

**Command-specific fields:**

| Field | Type | Description |
| :-- | :-- | :-- |
| `command` | string, required | Shell command to execute. |
| `async` | boolean | Run in background without blocking. |
| `shell` | string | `bash` (default) or `powershell`. |

**HTTP-specific fields:**

| Field | Type | Description |
| :-- | :-- | :-- |
| `url` | string, required | URL to POST to. |
| `headers` | object | Key-value HTTP headers. Values support `$VAR_NAME` or `${VAR_NAME}` interpolation. |
| `allowedEnvVars` | array | Env var names allowed for header interpolation. Unlisted vars resolve to empty string. |

**Prompt/agent-specific fields:**

| Field | Type | Description |
| :-- | :-- | :-- |
| `prompt` | string, required | Prompt text sent to the model. `$ARGUMENTS` is the placeholder for hook input JSON. |
| `model` | string | Model to use. Defaults to a fast model. |

Agent hooks get tool access; prompt hooks do not. Agent timeout defaults to 60s; prompt to 30s.

## Custom agents

Custom agent definitions live in `.claude/agents/` (project scope) or `~/.claude/agents/` (personal scope), or in a plugin's `agents/` directory. Each file is Markdown with YAML frontmatter.

Key frontmatter fields: `name` (required), `description` (required), `tools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`.

A skill with `context: fork` and `agent: my-custom-agent` runs in an isolated context using that custom agent's configuration.

## Sources

- [Extend Claude with skills](https://code.claude.com/docs/en/skills) - Claude Code official docs
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) - Claude Code official docs
- [Hooks reference](https://code.claude.com/docs/en/hooks) - Claude Code official docs
- [Subagents reference](https://code.claude.com/docs/en/sub-agents) - Claude Code official docs
- [Agent Skills specification](https://agentskills.io/specification) - Open standard
- [Skill Creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) - Anthropic's skills repo
