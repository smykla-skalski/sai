---
name: ai-daily-digest
description: >-
  Produce a current AI news digest from a normal Copilot session when the user
  wants a briefing, roundup, or "what happened in AI" summary. The content
  depends on current sources, so browse and verify dates before drafting -
  never write the digest from memory. Not for timeless explanations of how a
  model or technique works.
allowed-tools:
  - agent
  - list_agents
  - read_agent
  - read
  - shell
---

# AI Daily Digest (Copilot)

Assemble a curated, current AI news briefing. The current session agent is the orchestrator: it resolves scope, gathers dated and verified sources per topic (in-session or by delegating to a bundled research agent), checks currency, and synthesizes the digest from the bundled template. Orchestration stays in-session - this skill does not fan out a swarm of agents by default.

The bundled research agent is a native Copilot custom agent under `agents/` (namespaced, e.g. `ai-daily-digest:digest-research-agent`).

## References (read before drafting)

- [references/sources.md](references/sources.md) - source URLs and credibility tiers.
- [references/search-patterns.md](references/search-patterns.md) - per-topic search queries and the Friday weekly-recap section.
- [references/output-template.md](references/output-template.md) - digest structure, section guidelines, and the Length Guidelines table.

## Workflow

### 1. Resolve scope and topics

Parse the request for the focus (technical, business, engineering, leadership, or all) and any date range. Read [references/sources.md](references/sources.md) and [references/search-patterns.md](references/search-patterns.md) to turn the focus into a concrete list of topics/phases to cover. If the day is Friday and the user wants the weekly view, enable the weekly-recap topics from the search patterns. If scope is ambiguous, ask once; otherwise default to all topics for the current day.

### 2. Research (sequential by default)

Gather sources for each topic/phase. Either research each topic yourself in-session (run the relevant searches, hold the dated findings), or delegate one `digest-research-agent` per topic through the `agent` tool when a topic is large or benefits from isolation. Give each delegated agent: the date range, the focus area, the relevant section of [references/search-patterns.md](references/search-patterns.md), and the agent's return contract (a list of dated, sourced items). Validate that each agent reply starts with `## Research: <topic>` and carries dates plus URLs before using it.

Default to sequential, in-session research - or one research agent at a time. Copilot parallel fan-out over-parallelizes and burns AI credits; only fan out independent topics in parallel if the user explicitly asks, then run small waves (<= 5), supervise with list_agents/read_agent, and confirm each agent returned its sources before synthesizing.

### 3. Verify currency

Pin every candidate item to a concrete publication date and keep its source URL. Drop anything outside the requested window and anything you cannot date or verify. No item ships without a real date and a real source - prefer fewer, solid items over padding. Deduplicate items that describe the same event from different URLs.

### 4. Synthesize the digest

Build the briefing using [references/output-template.md](references/output-template.md): fill the template sections with the verified items, format story lines with the template's checkbox + source-link convention, pick the Top 5 across categories by impact, and check each section against the Length Guidelines table. If a section is short, return to step 2 for that topic and gather more before finishing. If the day is light, say so rather than inventing stories.

### 5. Publish (separate step, after the content is correct)

Publication to Notion or any other sink is a separate step performed only after the digest content is verified and correct. Confirm the destination with the user (or follow an explicitly provided target), then publish. Do not couple drafting to publishing - a correct briefing is the deliverable; the sink is downstream.

## Privacy / scope

This is a *current-events* skill: its value is dated, verifiable sources, so always browse before drafting and never fabricate a date, URL, or headline. It is not for timeless conceptual explanations - for "how does X work" questions, answer directly instead of running this workflow.
