# rightsize

Audits work against simplicity rules and reports what is overbuilt and what is oversimplified. The target is the minimum adequate system: it meets the required outcomes and constraints with the least cognitive, structural, coordination, operational and change burden. A smaller part count alone does not prove that a system is simpler, and a removed safeguard is a defect, not a simplification.

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

In Claude Code and Copilot CLI use `/rightsize`, in Codex `$rightsize`, or ask in plain words ("is this overengineered?", "can this design be simpler?"). The skill runs in the current conversation, starts no subagents and changes no files.

`audit` is the only subcommand and the default, so `/rightsize` and `/rightsize audit` are the same.

```text
/rightsize                          # audit the work in this conversation
/rightsize audit docs/architecture.md
/rightsize audit #123               # a pull request
/rightsize audit main..feature      # a commit range
/rightsize audit <pasted plan, design or process>
```

With no target, the skill audits the latest work in the conversation. For code that the agent implemented in the session, it collects every file the session created, edited or deleted, including changes it already committed, and audits the current files and their diff. It leaves out changes that the session did not make. Other work in the conversation, such as a plan or a process under discussion, works the same way. With no such work, it audits the uncommitted changes, then the current branch against its base. It asks only when it cannot tell which of two targets you mean.

## What it checks

About 70 rules in 12 groups, in [references/rules.md](skills/rightsize/references/rules.md):

- Any work: purpose and constraints (P), measuring the whole system (M), the complexity admission test (N), the reduction order eliminate, combine, default, standardize, encapsulate, automate, optimize (R), boundaries (B), interfaces and public surface (I), requisite variety (V), delivery in small steps (D), and pruning (E)
- New software projects: the one-page brief, the boring default topology with its component budget, and the evolution ladder (G)
- Software: tests and telemetry (T), docs and onboarding (K)

## Report

```text
## Rightsize audit: <target>
Scope, and a verdict: Adequate, Overbuilt, Oversimplified or Mixed
Broken rules: a table with the rule, status, severity, evidence (file:line or quote) and the smallest fix
Other issues, Gaps, Suggestions (ranked by value for effort), Keep (justified complexity)
A summary line with the counts
```

Each finding needs evidence. A finding without evidence becomes a gap. Before it reports, the skill tries to refute each finding against the work's requirements, and it lists the complexity that survives under Keep.
