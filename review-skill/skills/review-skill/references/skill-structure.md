# Contents

1. [Canonical skill layout](#canonical-skill-layout)
2. [Why resources live alongside SKILL.md](#why-resources-live-alongside-skillmd)
3. [Plugin vs skill directories](#plugin-vs-skill-directories)
4. [Path resolution at runtime](#path-resolution-at-runtime)
5. [Progressive loading](#progressive-loading)
6. [Sources](#sources)

---

## Canonical skill layout

Per the Agent Skills specification and Anthropic's official documentation, the canonical skill directory structure is:

```
skill-name/
├── SKILL.md           # Required — entrypoint
├── references/        # Documentation loaded into context on demand
├── scripts/           # Executable code (Python, Bash, etc.)
├── assets/            # Files used in output (templates, icons, fonts)
└── examples/          # Example files showing expected format
```

All bundled resources live **alongside SKILL.md** in the skill directory. This applies whether the skill is standalone, project-scoped, personal, or part of a plugin.

## Why resources live alongside SKILL.md

1. **Runtime path resolution.** Claude Code provides the skill's base path at invocation time, pointing to the directory containing SKILL.md. Relative paths in SKILL.md (`references/api.md`, `scripts/validate.sh`) resolve from this directory.

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
└── README.md                       # Plugin docs (NOT in skill dir)
```

Two distinct levels exist:

| Location                       | Purpose                        | Path variable           |
|:-------------------------------|:-------------------------------|:------------------------|
| `{plugin-root}/`               | Plugin metadata, README, hooks | `${CLAUDE_PLUGIN_ROOT}` |
| `{plugin-root}/skills/{name}/` | Skill entrypoint, resources    | Skill base path         |

`${CLAUDE_PLUGIN_ROOT}` is available in hook and MCP JSON configurations only. It is not available inside SKILL.md or command markdown files.

## Path resolution at runtime

When a skill is invoked, Claude Code provides the skill's **base path** in the system context. This path points to the directory containing SKILL.md, not the plugin root.

| Context                | Available path          | Resolves to                         |
|:-----------------------|:------------------------|:------------------------------------|
| Hook/MCP JSON configs  | `${CLAUDE_PLUGIN_ROOT}` | Plugin root directory               |
| Skill invocation       | Base path (automatic)   | Skill directory (contains SKILL.md) |
| Skill markdown content | Relative paths          | From skill directory                |

There is no formal `$SKILL_DIR` environment variable. The SKILL.md body uses relative paths (`references/X`, `scripts/Y`) which Claude resolves from the skill's base path at runtime.

Known issues (as of mid-2025):

- Scripts may fail on first execution with relative paths; Claude retries with absolute paths (GitHub issue #11011)
- Feature request for `CLAUDE_SKILL_ROOT` environment variable exists (GitHub issue #17564)

## Progressive loading

Skills use a three-level progressive disclosure system:

1. **Metadata (always in context, ~100 words).** The `name` and `description` from YAML frontmatter are always loaded into the available skills list.

2. **SKILL.md body (loaded on trigger, target <5k words).** The full markdown content loads when the user invokes `/skill-name` or when Claude determines the skill is relevant.

3. **Bundled resources (loaded on demand, unlimited).** Files in `references/`, `scripts/`, `assets/`, `examples/` are read only when Claude decides they are needed, based on references in SKILL.md. This is why SKILL.md should mention all bundled files.

## Sources

- [Extend Claude with skills](https://code.claude.com/docs/en/skills) — Claude Code official docs
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) — Claude Code official docs
- [Plugin Development SKILL.md](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md) — Anthropic's claude-code repo
- [Plugin Structure SKILL.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/plugin-structure/SKILL.md) — Anthropic's claude-plugins-official repo
- [Skill Creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) — Anthropic's skills repo
- [Inside Claude Code Skills](https://mikhail.io/2025/10/claude-code-skills/) — Mikhail Shilkov deep dive
- [GitHub Issue #11011](https://github.com/anthropics/claude-code/issues/11011) — Skill script path resolution bug
- [GitHub Issue #17564](https://github.com/anthropics/claude-code/issues/17564) — CLAUDE_SKILL_ROOT feature request
