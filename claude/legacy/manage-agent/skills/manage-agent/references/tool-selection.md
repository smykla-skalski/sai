# Tool & Model Selection Guide

## Agent Type to Tools

| Agent Type    | Recommended Tools                     | Rationale                 |
|:--------------|:--------------------------------------|:--------------------------|
| Reviewer      | Read, Grep, Glob                      | Read-only analysis        |
| Researcher    | Read, Grep, Glob, WebFetch, WebSearch | Information gathering     |
| Planner       | Read, Grep, Glob, Bash, Write         | Investigate and document  |
| Implementer   | Read, Edit, Write, Bash, Grep, Glob   | Create and execute        |
| Documentation | Read, Write, Edit, Glob, WebFetch     | Research and write        |
| Handover      | Read, Grep, Glob, Bash, Write         | Extract context and write |

**Note**: Never include `AskUserQuestion` in agent tools — it is filtered from subagents. Agents use `STATUS: NEEDS_INPUT` pattern instead.

## Model Selection

| Model  | Use Case                                         | Cost/Speed        |
|:-------|:-------------------------------------------------|:------------------|
| haiku  | Simple, frequent-use, well-defined tasks         | Fastest, cheapest |
| sonnet | Balanced complexity, most agents, default choice | Standard          |
| opus   | Complex analysis, deep reasoning, orchestration  | Most capable      |

### Decision Flow

```text
Complex orchestration or deep reasoning?
├─ YES → opus
└─ NO  → Frequent use, simple task?
         ├─ YES → haiku
         └─ NO  → sonnet (default)
```

## Least Privilege Principle

- Start with the minimum tool set for the agent type
- Only add tools if the agent's workflow explicitly requires them
- If the agent needs to write files: include Write (and Edit for modifications)
- If the agent needs shell access: include Bash (and scope with permission mode if possible)
- If the agent only reads/analyzes: use Read, Grep, Glob only
