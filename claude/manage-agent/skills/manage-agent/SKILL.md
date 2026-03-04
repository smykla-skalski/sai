---
name: manage-agent
description: Create, modify, or transform Claude Code agent definitions following template standards. Use when creating new agents from descriptions, improving existing agents, or converting prompt templates into production-quality agent definitions with built-in quality validation.
argument-hint: "<file-path|description> [--create|--modify|--transform]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
user-invocable: true
---

# Manage Agent

Create, modify, or transform Claude Code subagent definitions following template standards with built-in quality validation. Supports creating new agents from descriptions, improving existing agents in place, and converting prompt templates into production-quality agent definitions.

## Arguments

Parse from `$ARGUMENTS`:

| Flag          | Default | Purpose                                          |
|:--------------|:--------|:-------------------------------------------------|
| (positional)  | ---     | File path, description, or inline content        |
| `--create`    | auto    | Force create mode (new agent from description)   |
| `--modify`    | auto    | Force modify mode (improve existing agent)       |
| `--transform` | auto    | Force transform mode (convert template to agent) |

## Workflow

### Phase 1: Input Resolution

1. Parse `$ARGUMENTS` for file path, description, and flags.
2. If no input provided, use AskUserQuestion to ask what agent to create or which file to modify.
3. Determine mode (auto-detect if no flag):
   - Path in `.claude/agents/` or `~/.claude/agents/` -> **Modify**: read and improve existing agent
   - Any other file path -> **Transform**: convert to agent definition (source untouched)
   - No file path (description only) -> **Create**: design new agent from scratch

### Phase 2: Read Reference Material

1. Read `references/output-template.md` for the agent definition template and section guidelines.
2. Read `references/tool-selection.md` for tool and model selection guidance.
3. Read `references/quality-checklist.md` for the quality checklist to validate against.

### Phase 3: Design Decisions

For **Create** or **Transform** mode, resolve these decisions (use AskUserQuestion if unclear):

| Question        | Options                                                                | Default           |
|:----------------|:-----------------------------------------------------------------------|:------------------|
| Model           | haiku (simple/frequent), sonnet (balanced), opus (complex)             | sonnet            |
| Tools           | Suggested set based on agent type (see `references/tool-selection.md`) | type-based        |
| Permission mode | default, acceptEdits, bypassPermissions                                | default           |
| Save location   | `.claude/agents/` (project) or `~/.claude/agents/` (global)            | `.claude/agents/` |
| Slash command   | yes: `/command-name` or no                                             | no                |

### Phase 4: Agent Construction

Based on mode:

**Create mode**:

1. Use the output template from `references/output-template.md` as the skeleton.
2. Fill in all sections based on the user's description.
3. Select tools from `references/tool-selection.md` based on agent type.
4. Select model based on complexity guidelines.
5. Write the agent definition to the save location.

**Modify mode**:

1. Read the existing agent definition.
2. Identify gaps against the quality checklist.
3. Improve each section while preserving the agent's intent.
4. Apply changes using Edit tool.

**Transform mode**:

1. Read the source file (do NOT modify the source).
2. Extract the core purpose, constraints, and workflow.
3. Map to the agent template structure.
4. Write the new agent definition to the save location.

### Phase 5: Quality Validation

1. Run the quality checklist from `references/quality-checklist.md` against the output.
2. Check all mandatory sections exist and meet requirements.
3. Check for anti-patterns.
4. If issues found:
   - Auto-fix what can be fixed (section ordering, missing uncertainty handling).
   - Report remaining issues that need manual attention.

### Phase 6: Output

1. Present the completed agent definition.
2. Show quality validation results (verdict, findings).
3. If a slash command was requested, remind user to create it separately.

## Example

```bash
/manage-agent "A code reviewer that checks for security vulnerabilities"
```

Output: new agent definition at `.claude/agents/security-reviewer.md` with verdict-based quality report.

```bash
/manage-agent .claude/agents/session-manager.md --modify
```

Output: improved agent definition with changes applied in place and quality report.

```bash
/manage-agent prompts/old-reviewer.txt --transform
```

Output: new agent definition at `.claude/agents/old-reviewer.md` converted from template, source file untouched.
