# agent-issues

Write, improve and split GitHub issues, and write briefs for subagents, so that coding agents can implement them without asking questions.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **Interview, then verify.** Asks only the questions the repo cannot answer, then checks the premise, searches for duplicates, greps every named path and symbol, and runs the repro before anything goes in the issue.
- **Runnable done-checks.** Each outcome names a command, a test or an example input and output. Edge and error states are covered, and the suite that must stay green is named.
- **Honest hints.** Verified anchors are allowed as non-binding starting points. A cause appears only with the check that supports it. No line numbers, no step lists.
- **Stop and flag.** Concrete triggers for spec and test conflicts, missing decisions and one-way doors, plus a "no change needed if" precondition.
- **Layer-aware constraints.** Repo-wide rules stay in the root `AGENTS.md` or `CLAUDE.md` (or a hook). The issue names the task-specific instance instead of repeating them.
- **Vertical slices.** Oversized work is cut into self-contained, shippable children with native sub-issue and blocked-by relationships set at creation.
- **Threshold-gated cold-read.** A fresh-context reviewer restates the task and tags questions, but only when size or risk warrants it. A cheap self-check always runs.
- **Repo templates win the container.** Issue forms and templates keep their fields and order; the quality bar applies inside them.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install agent-issues@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add agent-issues@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/agent-issues/` directly:

```bash
ln -s /path/to/sai/plugins/agent-issues/skills/agent-issues ~/.config/opencode/skills/agent-issues
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/agent-issues/` (or `copilot --plugin-dir ...`)

## Usage

In Claude Code and Copilot CLI use `/agent-issues`, in Codex `$agent-issues`, or ask in plain words ("write an issue for this", "split this issue").

```text
/agent-issues add retry with backoff to the webhook sender
/agent-issues https://github.com/owner/repo/issues/42
/agent-issues https://github.com/owner/repo/issues/42 --draft
/agent-issues --brief refactor the parser tests into table-driven form
```

| Flag | Purpose |
| :-- | :-- |
| (positional) | A description to turn into an issue, or an issue URL or number to improve |
| `--draft` | Produce the draft and stop. Never touch GitHub |
| `--file` | Filing is already authorized. File after the checks pass without waiting for a go-ahead |
| `--brief` | Write a subagent brief. Nothing is filed |
| `--cold-read` | Force the cold-read review below the threshold |
| `--no-cold-read` | Skip the cold-read review. The self-check still runs |

By default the skill shows the full draft and waits for a go-ahead before it files or edits anything.

## Compatibility

| Capability | Claude Code | Copilot CLI | Codex | opencode |
| :-- | :-- | :-- | :-- | :-- |
| Interview questions | `AskUserQuestion` | Plain-text questions | Plain-text questions | Plain-text questions |
| Cold-read reviewer | Read-only subagent | Read-only subagent if available | Inline pass, reduced independence | Subagent if available, else inline |
| Filing and relationships | `gh` | `gh` | `gh` (escalate if the sandbox blocks it) | `gh` |

Without `gh`, or without auth, the skill produces the draft only. Without a way to ask the user (headless run), unresolved questions go to Open items and nothing is filed.

## Scope

- Covers issues, splitting and umbrellas, and subagent briefs.
- Does not write pull request descriptions. Use the repository's own PR template.
- Tracker mechanics are GitHub (`gh`). For other trackers it produces the markdown draft.

## Layout

```text
agent-issues/
├── plugin.json
├── .claude-plugin/plugin.json
└── skills/agent-issues/
    ├── SKILL.md
    ├── agents/openai.yaml
    └── references/
        ├── workflow.md               # procedure, flags, agent fallbacks
        ├── issue-rules.md            # title, body shape, bug variant, what stays out
        ├── splitting-and-handoffs.md # vertical slicing, relationships, subagent briefs
        ├── cold-read.md              # self-check, gate threshold, reviewer prompt
        ├── templates-and-forms.md    # repo templates and issue forms
        ├── writing-pass.md           # line rule and writing checklist
        └── evidence.md               # rule-to-evidence map and re-validation design
```

## Evidence

Every rule is tagged by evidence strength in [references/evidence.md](./skills/agent-issues/references/evidence.md). Several rules are inference or heuristics, with no direct study. The file lists what is unproven and how to re-test a rule on your own repositories.
