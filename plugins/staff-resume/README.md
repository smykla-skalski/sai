# staff-resume

Build and refine staff-level engineering resumes through interactive coaching, research-backed best practices, and per-job tailoring.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **Gap analysis** against staff-level criteria (scope language, decision authority, impact metrics, cross-team signals)
- **Interactive coaching** — probing questions to mine hidden achievements from each role
- **Bullet rewrites** using XYZ formula with staff-level power verbs
- **Job-specific tailoring** with keyword mapping, ATS optimization, and archetype alignment
- **Staff archetypes** — Tech Lead, Architect, Solver, Right Hand emphasis mapping
- **Multiple summary options** — Platform/Infra, AI Infra Pivot, Open Source focus

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install staff-resume@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add staff-resume@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/staff-resume/` directly:

```bash
ln -s /path/to/sai/plugins/staff-resume/skills/staff-resume ~/.config/opencode/skills/staff-resume
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/staff-resume/`

## Usage

```
/staff-resume path/to/resume.tex
/staff-resume path/to/resume.tex --job-url https://example.com/job
/staff-resume path/to/resume.md --mode tailor --job-url https://example.com/job
/staff-resume path/to/resume.tex --mode full --job-url https://example.com/job
```

In Codex use `$staff-resume` and give the resume path, job URL and mode in plain words. If no resume path is given, the skill asks for one.

### Modes

- **coach** (default) — gap analysis + interactive coaching + bullet rewrites
- **tailor** — job-specific keyword mapping, ATS optimization, archetype alignment
- **full** — both coaching and tailoring

### Other agents

Claude Code runs the skill in a forked subagent and asks questions with AskUserQuestion. On Codex, Copilot CLI and opencode the skill runs in the main agent loop and asks in plain text. Without web search or network access it skips the fresh research, uses the bundled reference, and asks you to paste the job posting. The fallbacks are listed under "Agent compatibility" in the SKILL.md.

## Reference Material

- `skills/staff-resume/references/staff-resume-patterns.md` — hiring manager priorities, senior vs staff language, XYZ formula, archetypes, ATS rules
