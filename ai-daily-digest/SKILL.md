---
name: ai-daily-digest
description: Daily AI news digest covering technical advances, business news, and engineering impact. Aggregates from research papers, tech blogs, HN, newsletters. Use daily for staying current on AI developments.
argument-hint: "[--focus technical|business|engineering|leadership] [--notion-page-id ID] [--no-notion]"
allowed-tools: WebSearch, WebFetch, Read, Write, Bash, Task, Glob
user-invocable: true
---

# AI Daily Digest Skill

Generate comprehensive daily AI news digest with technical, business, and engineering coverage.

## Arguments

Parse from `$ARGUMENTS`:

- `--focus [technical|business|engineering|leadership|all]` — Default: all
- `--notion-page-id [UUID]` — Notion parent page ID for digest publishing (overrides env var)
- `--no-notion` — Skip Notion publishing entirely (archive-only mode)

## Configuration

### Notion Parent Page ID (required for publishing)

Resolve the Notion parent page ID using this precedence (first match wins):

1. `--notion-page-id` argument
2. `NOTION_PARENT_PAGE_ID` environment variable
3. Interactive prompt — ask the user at runtime

When prompting the user, provide these instructions for finding the page ID:

- Open the target parent page in the browser
- Copy the URL (`https://www.notion.so/Page-Title-{32-hex-chars}`)
- Extract the last 32 hex characters, insert hyphens as `8-4-4-4-12` for UUID format
- Alternative: click "Share" → "Copy link" and extract the ID

Recommend persisting via env var in `~/.zshrc` / `~/.bashrc`:

```bash
export NOTION_PARENT_PAGE_ID="your-page-id-here"
```

Or in `~/.claude/settings.json` under the `"env"` key:

```json
{
  "env": {
    "NOTION_PARENT_PAGE_ID": "your-page-id-here"
  }
}
```

## State Files

All state stored in `./findings/ai-daily-digest/`.

### Last Run Date (`.last-run`)

Format: `YYYY-MM-DD`. Read on startup to calculate date range. If missing, default to past 7 days.

### Covered Stories (`.covered-stories`)

Pipe-separated: `{date}|{story_id}|{url}` — one story per line.

- `story_id` — Normalized: lowercase, hyphen-separated, key terms (e.g., `falcon-h1r-7b-release`, `xai-20b-funding`)
- Keep last 300 entries (trim oldest when exceeding)
- Prevents duplicate stories across days via story_id fuzzy matching and URL matching

Example:

```text
2026-01-28|deepseek-r1-release|https://api-docs.deepseek.com/news/news250120
2026-01-29|falcon-h1r-7b-release|https://falcon-lm.github.io/blog/falcon-h1r-7b/
```

## Workflow

### Phase 1: Setup

1. Read `sources.md` for source URLs and tiers
2. Read `output-template.md` for digest format
3. Parse arguments for focus area and `--notion-page-id`
4. **Resolve Notion page ID** — if `--no-notion` is set, set `notion_page_id` to `null` (archive-only mode). Otherwise check in order: `--notion-page-id` arg → `NOTION_PARENT_PAGE_ID` env var → prompt user interactively. Store resolved value as `notion_page_id` for Phase 18. If user declines to provide an ID, skip Notion publishing (archive-only mode).
5. Read `.last-run` — set date range from last run to today
6. Read `.covered-stories` — build in-memory `covered_ids` and `covered_urls` sets
7. If today is Friday, enable weekly recap mode (see `references/search-patterns.md` → Friday Weekly Recap)

### Phases 2-15: Research

**CRITICAL: Before starting Phase 2, read `references/search-patterns.md` in full.** Execute every phase listed below using the search patterns, collect lists, and quality signals from that file. Each phase has a dedicated section in the reference. Do not skip phases — missing a phase means missing an entire digest section.

| Phase | Topic | Skip unless focus includes |
|-------|-------|---------------------------|
| 2 | Technical research (models, papers, frameworks) | technical |
| 3 | Business research (funding, acquisitions, launches) | business |
| 4 | Engineering impact (dev tools, workflow, job market) | engineering |
| 5 | Leadership research (strategy, org transformation) | leadership |
| 6 | GitHub trending AI repos | technical |
| 7 | AI tools for professionals (9 domains) | all (always run) |
| 8 | AI application domains (7 verticals) | all (always run) |
| 9 | AI safety & ethics | all (always run) |
| 10 | Open source AI ecosystem | technical |
| 11 | AI infrastructure & hardware | technical |
| 12 | Regional AI developments | all (always run) |
| 13 | YouTube AI videos | all (always run) |
| 14 | Cool & thought-provoking research | all (always run) |
| 15 | Newsletter & blog aggregation | all (always run) |

### Phase 16: Synthesis (CRITICAL — Dedup BEFORE Digest)

All deduplication MUST happen here BEFORE generating the digest.

**Step 1: Generate story IDs** for all collected items.

Normalized format — lowercase, hyphen-separated, company/product + action + key detail:

- "Falcon-H1R 7B release" → `falcon-h1r-7b-release`
- "xAI raises $20B" → `xai-20b-funding`
- "Simon Willison on sandboxes" → `simonwillison-sandboxes-post`

**Step 2: Deduplicate within session** — remove same event from different URLs.

**Step 3: Deduplicate against history** — use in-memory `covered_ids` and `covered_urls` from Phase 1. DO NOT re-read or update the file.

Filter out stories where:

1. Exact story_id match in `covered_ids`
2. Similar story_id (same product/company + same action)
3. Exact URL match in `covered_urls`
4. Same announcement, different angle

**Step 4: Rank** by source credibility (tier 1 > tier 2 > tier 3), engagement, relevance.

**Step 5: Categorize** into template sections and select Top 5 from filtered content.

**Step 6: Completeness check** — compare categorized items against the Length Guidelines table in `output-template.md`. If any section is below its target minimum, return to the corresponding research phase and run additional searches from `references/search-patterns.md` to fill the gap. Every section in the template must have content before proceeding.

### Phase 17: Generate Digest

1. Load `output-template.md`
2. Fill sections with filtered items from Phase 16 only
3. Format: `- [ ] **[Title]** — [1-line summary] [Source: URL]`
   - Checkbox `- [ ]` on ALL story items with source URLs (renders as Notion task)
   - NO checkbox on: Top 5 summary, prose bullets, Action Items, Things to Explore, Connections, Sources section
4. If fewer than 5 stories after filtering, note "Light news day"

### Phase 18: Save Digest Files

DO NOT update `.covered-stories` in this phase — wait for verification.

**Step 1:** `mkdir -p ./findings/ai-daily-digest`

**Step 2: Save to Notion**

Skip this step if `notion_page_id` was not resolved in Phase 1 (archive-only mode).

Load Notion tool via ToolSearch (`select:mcp__notion__notion-create-pages`), then create page:

- Parent page ID: use `notion_page_id` resolved in Phase 1
- Title: `🤖 AI Digest {YYYY-MM-DD}`
- Content: Full digest markdown (excluding H1 title)

If page creation fails, warn the user and continue — the archive copy in Step 3 still provides value.

**Step 3:** Write archive copy to `./findings/ai-daily-digest/ai-digest-{YYYY-MM-DD}.md`

**Step 4:** Update `.last-run` with today's date (YYYY-MM-DD).

### Phase 19: Duplicate Verification

Spawn a `general-purpose` verification agent to check today's digest against:

1. `.covered-stories` (should NOT include today's stories yet)
2. Last 3 digests from `./findings/ai-daily-digest/`

Agent checks for: exact duplicates, near duplicates (same company + similar action within 7 days), URL duplicates, topic fatigue (same topic 3+ times in past week).

**On duplicate detection:**

- REMOVE flagged: edit both Notion and archive copies, then proceed to Phase 20
- Borderline only: keep stories, add footer note `*Verification: {N} borderline items retained*`
- All clear: proceed to Phase 20

### Phase 20: Update Covered Stories (FINAL)

Only after Phase 19 passes. Append to `.covered-stories` for each story in final digest:

```text
{date}|{story_id}|{url}
```

Keep file under 300 lines — trim oldest from top if over.

## Output Requirements

- Emojis for section headers (per template)
- Bullet points over paragraphs
- All items must have source URLs
- Top 5 stories section required
- Personal takeaways with actionable items
- Coverage period in header (e.g., "Coverage: Jan 25 - Jan 28 (3 days)")

## Error Handling

- If WebSearch fails for a source, log and continue with others
- Minimum viable digest: at least 5 items total
- If < 5 items, expand date range by 1 day and retry
- Only update `.last-run` on successful digest generation

## Newsletter Integration

Story items use `- [ ]` checkbox format for newsletter curation. User checks stories in Notion → `/ai-newsletter` extracts checked items.

## Example Invocations

```bash
/ai-digest
/ai-digest --focus technical
/ai-digest --focus business
/ai-digest --notion-page-id 12345678-abcd-1234-efgh-123456789abc
/ai-digest --focus technical --notion-page-id 12345678-abcd-1234-efgh-123456789abc
/ai-digest --no-notion
/ai-digest --focus technical --no-notion
```
