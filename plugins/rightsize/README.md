# rightsize

Audits work against simplicity rules and reports what is overbuilt and what is oversimplified. It also writes new documents, such as design docs, decision records and plans, that pass the same rules, and rewrites existing ones. The target is the minimum adequate system: it meets the required outcomes and constraints with the least cognitive, structural, coordination, operational and change burden. A smaller part count alone does not prove that a system is simpler, and a removed safeguard is a defect, not a simplification.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

The rules come from two research reports, on simplifying any system and on simplicity for new software projects. Their sources include Brooks's essential and accidental complexity, Ashby's requisite variety, Parnas's information hiding, Simon's near-decomposability, Fowler's YAGNI and Monolith First, the UK government design principles and Google SRE's end-to-end simplicity.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install rightsize@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add rightsize@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/rightsize/` directly:

```bash
ln -s /path/to/sai/plugins/rightsize/skills/rightsize ~/.config/opencode/skills/rightsize
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/rightsize/`

## Usage

In Claude Code and Copilot CLI use `/rightsize`, in Codex `$rightsize`, or ask in plain words ("is this overengineered?", "write a design doc for this", "rewrite this plan so that it is no bigger than it needs to be"). The skill runs in the current conversation and starts no subagents.

| Subcommand | What it does | Changes files |
| :-- | :-- | :-- |
| `audit` | Checks work, code or a document, and reports the broken rules | No |
| `write` | Writes a new document or message from a brief and the material it names, into a file or the chat | Only the new document |
| `rewrite` | Reworks a document or message (a file, pasted text or a message earlier in the chat) and reports the content changes | Only that document |

The subcommand is optional. Without one, the skill infers it from your request and the conversation: `write` when you ask for a document or message that does not exist yet, `rewrite` when you ask to shorten, simplify or clean up an existing one, in a file or in the chat, and `audit` otherwise, including every question about whether work is too complex. It asks only when two modes are equally likely and one of them would change a file. With `--dry-run`, `write` and `rewrite` print the document in chat instead of writing the file.

```text
/rightsize                          # infer the mode, then use the work in this conversation
/rightsize audit docs/architecture.md
/rightsize audit #123               # a pull request
/rightsize audit main..feature      # a commit range
/rightsize write a decision record for moving search to Postgres full-text search
/rightsize write docs/design/reminders.md from notes/reminders.md
/rightsize rewrite docs/plan.md
/rightsize write a Slack message about the search decision   # printed in the chat
/rightsize rewrite the plan you just posted                  # rewritten in the chat
/rightsize rewrite --dry-run <pasted plan, design or process>
```

With no target, the skill audits the latest work in the conversation. For code that the agent implemented in the session, it collects every file the session created, edited or deleted, including changes it already committed, and audits the current files and their diff. It leaves out changes that the session did not make. Other work in the conversation, such as a plan or a process under discussion, works the same way. With no such work, it audits the uncommitted changes, then the current branch against its base. It asks only when it cannot tell which of two targets you mean.

## What it checks

About 70 rules in 12 groups, in [references/rules.md](skills/rightsize/references/rules.md):

- Any work: purpose and constraints (P), measuring the whole system (M), the complexity admission test (N), the reduction order eliminate, combine, default, standardize, encapsulate, automate, optimize (R), boundaries (B), interfaces and public surface (I), requisite variety (V), delivery in small steps (D), and pruning (E)
- New software projects: the one-page brief, the boring default topology with its component budget, and the evolution ladder (G)
- Software: tests and telemetry (T), docs and onboarding (K)

## Write and rewrite

`write` gathers the material from the request, the conversation and the files it names, and picks the smallest document type that fits the risk: a decision log line, a decision record, a pitch, a design doc, a plan, user stories, a runbook, a procedure or a message such as a Slack post. A document goes into the file you name; a message, or anything without a path, goes into the chat, ready to paste. It starts from the smallest change that meets the need, admits each further element only for a current reason, keeps every required safeguard, and turns unknown facts into open questions instead of inventing them. Speculative ideas go under non-goals or alternatives with the trigger that would admit them.

`rewrite` checks an existing document against the same rules, moves what has no current reason to non-goals or alternatives, restores missing safeguards and parts, and keeps every other fact, number, condition and the author's voice. It edits a file in place, or prints the rewrite of pasted text or of a message earlier in the conversation, and reports each content change with its rule.

Both modes follow the 15 document rules in [references/documents.md](skills/rightsize/references/documents.md), from research on design documents, lightweight docs for small teams, planning to a fixed date, and user stories. The prose follows the [humanize](../humanize/) rules, bundled in `references/prose/` so that the plugin works without humanize installed. A repository test keeps the copies identical.

## Audit report

```text
## Rightsize audit: <target>
Scope, and a verdict: Adequate, Overbuilt, Oversimplified or Mixed
Broken rules: a table with the rule, status, severity, evidence (file:line or quote) and the smallest fix
Other issues, Gaps, Suggestions (ranked by value for effort), Keep (justified complexity)
A summary line with the counts
```

Each finding needs evidence. A finding without evidence becomes a gap. Before it reports, the skill tries to refute each finding against the work's requirements, and it lists the complexity that survives under Keep.
