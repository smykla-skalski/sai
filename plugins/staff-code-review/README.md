# staff-code-review

Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, observability, security, and cross-team impact.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io) and nine bundled agents, so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **Triage pass** — six mental model questions (Tanya Reilly) before line-by-line review
- **Codebase research** — caller counts, existing patterns, test coverage, git history, ADR context
- **Deep review across seven dimensions** — Architecture, Reliability, Security, Performance, Backward Compatibility, Conventions, Dead Code. In Claude Code each runs in parallel as a council persona (Evans, Hebert, Willison, Gregg, Siracusa, antirez, tef) when the [council](../council/) plugin is installed, otherwise as the bundled dimension reviewer
- **Two adversaries** — a **Code Adversary** runs alongside the dimension reviewers and red-teams the change itself, assuming it's broken and hunting for the concrete bug with a failing input. A **Findings Adversary** runs after synthesis and red-teams the findings, killing false positives, right-sizing inflated severities, and dropping hallucinated locations that would break GitHub posting. Skip both with `--no-adversary`
- **Translation pass** — council-persona reviews are converted to conventional comments without losing technical content
- **Conventional comments** — `blocking:`, `issue:`, `question:`, `suggestion:`, `thought:`, `nit:`, `praise:`
- **Humanized comments** — uses the [humanize](../humanize/) plugin's pattern catalog when it is installed next to this one
- **Pending GitHub review** — for PR URLs, posts inline comments as a draft review you submit yourself
- **Design doc detection** — flags PRs that should have had an RFC/design doc first

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install staff-code-review@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add staff-code-review@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/staff-code-review/` directly:

```bash
ln -s /path/to/sai/plugins/staff-code-review/skills/staff-code-review ~/.config/opencode/skills/staff-code-review
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/staff-code-review/`

### Optional plugins

- [council](../council/) — Claude Code uses its personas for the seven dimensions. Without it, the bundled dimension reviewers run instead
- [humanize](../humanize/) — install it from the same marketplace (or symlink it next to this skill for opencode) to humanize review comments with its pattern catalog. `scripts/find_humanize_refs.py` finds it in every agent's install layout; without it, Claude Code skips the pass and other agents humanize inline without the catalog

## Usage

In Claude Code and Copilot CLI use `/staff-code-review`, in Codex `$staff-code-review`, or ask in plain words ("staff review this PR").

```text
/staff-code-review <PR URL> [--no-adversary]
/staff-code-review <file path> [--no-adversary]
```

Triggers on: "review this PR", "review these changes", "staff review", "thorough code review", sharing a GitHub PR URL for review.

## Subagents per agent

| Agent | Dimension reviewers | Adversaries |
| :-- | :-- | :-- |
| Claude Code | Parallel: `council:*` persona, then bundled `staff-code-review:<dimension>-reviewer`, then `general-purpose` with the mandate | Named agents `staff-code-review:code-adversary` and `:review-adversary`, `general-purpose` fallback |
| Copilot CLI | Bundled `staff-code-review:<dimension>-reviewer` agents, one at a time | Same named agents, one at a time |
| Codex | Inline lens passes from `references/agents/`, or one `spawn_agent` at a time | Inline, or one `spawn_agent` at a time |
| opencode | One `task` call at a time with the built-in `general` subagent, or inline | Same |

Only Claude Code fans out. Codex and Copilot CLI run sequentially by default because their fan-out is unreliable at nine reviewers.

## Files

- `agents/*.md` - Claude Code and Copilot CLI definitions for the seven dimension reviewers, the Code Adversary, and the Findings Adversary (`review-adversary`)
- `plugin.json` - root manifest for Codex and Copilot CLI. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/staff-code-review/references/agents/*.md` - the same mandates for Codex, opencode, and the `general-purpose` fallback. Each must stay identical to its agent body; `tests/test_staff_code_review.py` enforces it
- `skills/staff-code-review/references/` - dimension checklists, deep references, and the persona translator prompt
- `skills/staff-code-review/scripts/parse_review_comments.py` - extracts inline comments for the GitHub review
- `skills/staff-code-review/scripts/find_humanize_refs.py` - locates the humanize plugin's references

## License

MIT
