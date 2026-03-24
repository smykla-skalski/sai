# kubecon-cfp

Interactive KubeCon CFP submission writer with data-driven insights from 1,100+ accepted talks across 7 KubeCon events (2024-2025).

## What it does

Guides through the full CFP workflow: topic assessment against acceptance data, interactive refinement, title crafting with proven patterns, abstract writing (Hook→Promise→Payoff), benefits section, and review scoring against official criteria.

## Usage

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

## Installation

```bash
/plugin install sai/kubecon-cfp
```

Or for local development:

```bash
claude --plugin-dir /path/to/sai/claude/kubecon-cfp/
```
