---
name: kubecon-cfp
description: Interactive KubeCon CFP submission writer. Guides through topic selection, title crafting, abstract writing, and benefits section using acceptance data from 1,100+ talks across 7 KubeCon events (2024-2025). Use when preparing a conference talk proposal for KubeCon/CloudNativeCon, writing a CFP, or asking about KubeCon submission strategy.
argument-hint: [topic or talk idea] [--track AI|Security|Platform|Observability|...] [--format session|lightning|tutorial|panel] [--review]
user-invocable: true
disable-model-invocation: true
allowed-tools:
  - Agent
  - AskUserQuestion
  - Read
  - Write
---

<!-- justify: CF-side-effect Edit/Write fix detected issues in SKILL.md with user approval -->

# KubeCon CFP Submission Writer

Craft a high-quality KubeCon CFP submission using data-driven insights from 1,100+ accepted talks and official reviewer criteria.

## Arguments

Parse from `$ARGUMENTS`:

- **Topic/idea:** Required — rough talk concept (e.g., "API gateway migration to Gateway API at scale")
- **--track:** Optional — target track (AI, Security, Platform, Observability, Operations, Connectivity, etc.)
- **--format:** Optional — session (30min, default), lightning (5min), tutorial (75min), panel (30min)
- **--review:** Optional — review/improve an existing CFP draft instead of writing from scratch

## Workflow

### Phase 1: Load Knowledge Base

Read reference files before starting:

```
Read: references/cfp-criteria.md — scoring dimensions, character limits, format rules
Read: references/talk-patterns.md — title patterns, topic trends, acceptance data
```

### Phase 2: Topic Assessment

Evaluate the user's topic idea against acceptance data:

1. **Track fit** — if --track was provided, validate it matches the topic; otherwise recommend the best track
2. **Trend alignment** — is this a hot/growing, steady, or declining topic?
3. **Saturation check** — how many similar talks were accepted recently? High saturation = need sharper angle
4. **Novelty assessment** — what's the unique angle vs existing talks?
5. **End-user signal** — does this include production experience with real metrics?

Output a brief assessment with recommended track, competitiveness estimate, differentiation angles, and similar accepted talk titles.

### Phase 3: Interactive Refinement

Use AskUserQuestion to gather concrete details:

1. **Production story** — specific company, scale, metrics, timeline
2. **What went wrong** — failures/challenges are more compelling than successes
3. **Takeaway** — what will attendees do differently after this talk?
4. **Unique angle** — why hasn't this been presented before?
5. **Supplemental materials** — previous talks, blog posts, GitHub repos, video recordings

Wait for concrete answers before proceeding because vague submissions get rejected.

### Phase 4: Craft Title (75 chars max)

Generate 5 title options using proven patterns from [references/talk-patterns.md](references/talk-patterns.md). Re-read the title patterns section before generating.

Rules: title case, under 75 characters (hard limit), specific over generic, include scale/numbers when possible, no vendor/product names unless open-source project.

Present options ranked by likely reviewer impact. Let user pick or iterate via AskUserQuestion.

<example>
Topic: "We migrated our API gateways from Kong to Gateway API across 200 microservices"
Track: Connectivity

Title options:
1. "Migrating 200 Microservices to Gateway API Without Downtime" (55 chars)
2. "Gateway API at Scale: Lessons from Replacing Our API Gateway" (60 chars)
3. "From Vendor Lock-in to Gateway API: A 200-Service Journey" (57 chars)
4. "Zero-Downtime Gateway Migration: What Nobody Tells You" (55 chars)
5. "200 Services, 1 Gateway API: Our Migration Playbook" (52 chars)
</example>

Adapt title style to --format: lightning talks need punchier/shorter titles, tutorials should signal hands-on content.

### Phase 5: Write Abstract (1,300 chars max)

Structure: **Hook → Promise → Payoff**

- 1-2 sentences: Problem/challenge that hooks the reader
- 2-3 sentences: What this talk covers, the journey/approach
- 1-2 sentences: Concrete takeaways — "Attendees will learn..."

Rules: third person ("The speaker will..." not "I will..."), complete sentences (gets published on the schedule), specific numbers and metrics, no marketing/sales language, no jargon without context, first sentence must hook — reviewers read 100-200 proposals.

Show character count after writing. Must be ≤1,300.

<example>
Input: Gateway API migration, 200 services, zero downtime, 6-month timeline

Abstract (847 chars):
"Managing API traffic across 200 microservices through a proprietary gateway created vendor lock-in, limited extensibility, and cost $2M annually in licensing. This talk presents a six-month migration to Kubernetes Gateway API that achieved zero downtime while serving 50K requests per second. The speaker will walk through the three-phase migration strategy: shadow traffic validation, canary rollout per service tier, and automated rollback triggers that caught 12 configuration errors before they reached production. Attendees will learn a concrete migration playbook applicable to any gateway transition, specific pitfalls around HTTPRoute weight distribution at scale, and how to build confidence metrics that let teams migrate without fear."
Character count: 847/1,300
</example>

### Phase 6: Write Benefits to the Ecosystem (1,000-1,500 chars)

This is a **separate section visible only to reviewers** — not a copy of the abstract.

Cover: who benefits (specific personas), how this advances the ecosystem (open-source contributions, shared learnings), why now (timeliness), what gap this fills in current conference content.

Show character count after writing. Must be 1,000-1,500.

### Phase 7: Supplemental Materials Guidance

Help the user identify and format supplemental materials: previous talk recordings (strongest signal), blog posts, GitHub repos, LinkedIn profile, published articles.

If user has no materials, suggest creating a blog post or recording a practice talk before submitting.

### Phase 8: Review Mode (--review flag or final pass)

Score the submission against the 4 official criteria from [references/cfp-criteria.md](references/cfp-criteria.md) (1-5 scale): Content, Originality, Relevance, Speaker(s).

Run the pre-submit checklist from [references/cfp-criteria.md](references/cfp-criteria.md) and flag issues.

<example>
Input: --review on a draft titled "Introduction to Service Mesh"

Review output:
- Content: 2/5 — generic topic, no production data or specific metrics
- Originality: 1/5 — service mesh intros presented at 4+ recent KubeCon events
- Relevance: 3/5 — still relevant but saturated
- Speaker(s): N/A — no supplemental materials provided

Flags: title too generic (fails "scroll past" test), no end-user signal, steady/declining topic needs sharp angle. Recommend pivoting to a specific migration story or failure case.
</example>

### Phase 9: Competitive Analysis (optional)

If user wants extra insight, spawn a research agent to search for similar KubeCon talks, identify how the angle differs, and find gaps in existing coverage.

### Phase 10: Save Output

Read [references/output-template.md](references/output-template.md) for the submission format. Save to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/kubecon-cfp/submissions/[title-slugified].md`.

## Scope

Not designed for non-CNCF conferences (DevOpsDays, QCon, re:Invent). The acceptance data, scoring criteria, and track structure are KubeCon/CloudNativeCon-specific.

## Error Handling

- **Vague topic:** Push back hard — ask for specifics, production context, real numbers
- **Wrong track:** Suggest correct track with reasoning
- **Over character limit:** Tighten ruthlessly — cut adjectives, merge sentences, remove hedging
- **No unique angle:** Research what's been presented, find the gap together
- **No supplemental materials:** Suggest creating a blog post or practice recording

## Quality Standards

- Every submission must have concrete production metrics or technical depth
- No generic "best practices" or "introduction to X" proposals (unless Cloud Native Novice track)
- Titles must be memorable — if you'd scroll past it in a schedule, rewrite it
- Abstract first sentence must make a reviewer want to read sentence two

## Example Invocations

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
