# kubecon-cfp

Interactive KubeCon CFP submission writer with data-driven insights from 1,100+ accepted talks across 7 KubeCon events (2024-2025).

## What it does

Guides through the full CFP workflow: topic assessment against acceptance data, interactive refinement, title crafting with proven patterns, abstract writing (Hook→Promise→Payoff), benefits section, and review scoring against official criteria.

## Installation

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install kubecon-cfp@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add kubecon-cfp@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/kubecon-cfp/` directly:

```bash
ln -s /path/to/sai/plugins/kubecon-cfp/skills/kubecon-cfp ~/.config/opencode/skills/kubecon-cfp
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/kubecon-cfp/`

## Usage

The skill runs only when invoked explicitly: `/kubecon-cfp` in Claude Code and Copilot CLI, `$kubecon-cfp` in Codex. Where the agent has no question tool, it asks the refinement questions in plain text; where it has no subagent tool, the optional competitive analysis runs inline.

```bash
# Basic topic
/kubecon-cfp "API gateway migration to Gateway API at scale"

# With track and format
/kubecon-cfp "eBPF-based network policies" --track Security --format lightning

# Review an existing draft
/kubecon-cfp --review

# Tutorial format
/kubecon-cfp "hands-on Cilium service mesh" --track Connectivity --format tutorial
```

Submissions are saved to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/kubecon-cfp/submissions/`.

## License

MIT - See [../../LICENSE](../../LICENSE)
