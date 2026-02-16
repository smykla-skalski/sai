# Search Patterns Reference

## Table of Contents

- [Core Research (Phases 2-5)](#core-research-phases-2-5)
- [GitHub Trending (Phase 6)](#github-trending-phase-6)
- [AI Tools by Domain (Phase 7)](#ai-tools-by-domain-phase-7)
- [AI Application Domains (Phase 8)](#ai-application-domains-phase-8)
- [Safety & Ethics (Phase 9)](#safety--ethics-phase-9)
- [Open Source Ecosystem (Phase 10)](#open-source-ecosystem-phase-10)
- [Infrastructure & Hardware (Phase 11)](#infrastructure--hardware-phase-11)
- [Regional Developments (Phase 12)](#regional-developments-phase-12)
- [YouTube AI Videos (Phase 13)](#youtube-ai-videos-phase-13)
- [Cool & Thought-Provoking (Phase 14)](#cool--thought-provoking-phase-14)
- [Newsletters & Blogs (Phase 15)](#newsletters--blogs-phase-15)
- [Friday Weekly Recap](#friday-weekly-recap)

---

## Core Research (Phases 2-5)

### Phase 2: Technical

Search patterns:

- `AI LLM breakthrough OR release site:arxiv.org {date_range}`
- `AI model release OR launch {date_range}`
- `LLM framework tool release {date_range}`
- `site:huggingface.co blog {date_range}`
- `site:openai.com blog {date_range}`
- `site:anthropic.com news {date_range}`

Collect: new model releases, research paper highlights, framework/tool updates, benchmark results.

### Phase 3: Business

Search patterns:

- `AI startup funding OR acquisition {date_range}`
- `AI company valuation OR investment {date_range}`
- `site:techcrunch.com AI {date_range}`
- `site:venturebeat.com AI {date_range}`
- `OpenAI OR Anthropic OR Google AI business {date_range}`

Collect: funding rounds, acquisitions/mergers, product launches, partnership announcements, market analysis.

### Phase 4: Engineering Impact

Search patterns:

- `AI coding assistant OR developer tools {date_range}`
- `AI engineering workflow productivity {date_range}`
- `AI job market developer skills {date_range}`
- `site:news.ycombinator.com AI OR LLM {date_range}`
- `site:reddit.com/r/MachineLearning {date_range}`
- `site:reddit.com/r/LocalLLaMA {date_range}`

Collect: new dev tools and integrations, workflow automation updates, job market trends, community discussions.

### Phase 5: Leadership

Search patterns:

- `AI leadership engineering management {date_range}`
- `AI team strategy CTO VP engineering {date_range}`
- `site:hbr.org AI leadership management`
- `site:mckinsey.com AI leadership`
- `AI transformation organizational change {date_range}`
- `engineering leadership AI adoption {date_range}`

Collect: AI strategy for engineering orgs, team structure changes, leadership perspectives on AI adoption, org transformation case studies.

---

## GitHub Trending (Phase 6)

Direct fetch:

- `https://github.com/trending?since=daily&spoken_language_code=en`
- `https://github.com/trending/python?since=daily`
- `https://github.com/trending/jupyter-notebook?since=daily`

Search patterns:

- `site:github.com "stars" AI LLM new {date_range}`
- `site:github.com trending machine learning {date_range}`
- `github AI tool "just released" OR "new release" {date_range}`
- `site:news.ycombinator.com "Show HN" github AI {date_range}`

Collect: new AI/ML repos gaining traction (100+ stars recently), framework releases, interesting tools/demos, open-source model implementations.

Use `{repo-owner}-{repo-name}` as story_id. Include repos even if not brand new — check against `.covered-stories` and include if not already covered.

---

## AI Tools by Domain (Phase 7)

For each domain below, search using the listed patterns and collect tools matching the domain's focus. Quality signals for all: actually useful (not demos), accessible pricing, active development, good reviews, clear value proposition.

### Software Engineers

Patterns: `AI developer tools new release`, `AI coding assistant launch`, `AI code review tool`, `AI debugging assistant`, `AI IDE plugin extension`, `AI terminal CLI tool`, `site:producthunt.com AI developer coding`

Collect: coding assistants, dev tools (testing, debugging, docs), CLI tools, IDE plugins, code review tools, DevOps AI.

### Photographers & Videographers

Patterns: `AI photo editing tool new`, `AI video editing software`, `AI image generation photography`, `AI video upscaling enhancement`, `AI color grading tool`, `AI background removal`, `site:producthunt.com AI photo video`

Collect: photo editing, video editing, color grading, background removal, image upscaling, camera apps, video generation, VFX tools.

### Writers & Content Creators

Patterns: `AI writing tool new`, `AI content generation platform`, `"AI for writers" OR "AI writing assistant"`, `AI copywriting tool`, `site:producthunt.com AI writing content`

Collect: writing assistants, content generation platforms, SEO tools, script tools, long-form content, editing/proofreading.

### Designers

Patterns: `AI design tool new`, `AI Figma plugin`, `"AI for designers" tool app`, `AI logo generator OR brand design`, `AI UI UX design tool`, `site:producthunt.com AI design`

Collect: design tools, Figma/Sketch plugins, logo generators, UI/UX assistants, generative design, design system automation.

### Researchers & Academics

Patterns: `AI research tool new`, `AI literature review OR research assistant`, `AI paper summarization tool`, `AI citation management`, `AI data analysis research`

Collect: literature review tools, paper summarization, research assistants, data analysis platforms, citation management.

### Educators & Teachers

Patterns: `AI education tool new`, `AI tutoring platform OR adaptive learning`, `"AI for teachers"`, `AI lesson planning tool`, `AI grading assessment`, `site:producthunt.com AI education learning`

Collect: tutoring platforms, adaptive learning, lesson planning, assessment/grading, curriculum design, student engagement.

### Healthcare Professionals

Patterns: `AI healthcare tool new`, `AI medical imaging OR diagnostics`, `"AI for doctors"`, `AI clinical decision support`, `AI EHR electronic health records`, `AI medical scribing`

Collect: medical imaging, diagnostic assistance, clinical decision support, medical documentation, EHR integration.

### Legal Professionals

Patterns: `AI legal tool new`, `AI contract review OR analysis`, `"AI for lawyers" OR "legal tech AI"`, `AI legal research platform`, `AI document automation legal`

Collect: contract review, legal research, document automation, compliance tools, case law analysis, e-discovery.

### Finance & Accounting

Patterns: `AI finance tool new`, `AI accounting automation`, `"AI for finance"`, `AI fraud detection financial`, `AI forecasting financial`, `site:producthunt.com AI finance fintech`

Collect: accounting automation, financial forecasting, fraud detection, tax preparation, audit assistance, investment analysis.

---

## AI Application Domains (Phase 8)

### Education

Patterns: `AI education platform OR edtech`, `adaptive learning AI`, `AI tutoring breakthrough`, `AI assessment education`

### Healthcare & Biotech

Patterns: `AI drug discovery OR biotech`, `AI diagnostics medical breakthrough`, `AI clinical trials`, `AI protein folding OR molecular`, `AI radiology pathology imaging`

### Creative Industries

Patterns: `AI music generation OR composition`, `AI game development OR procedural generation`, `AI art generation breakthrough`, `AI film production OR VFX`, `AI voice cloning OR synthesis`

### Robotics & Hardware

Patterns: `AI robotics OR humanoid robot`, `embodied AI OR physical AI`, `robot learning OR manipulation`, `autonomous vehicle OR robotaxi`, `drone AI OR aerial robotics`

### Gaming

Patterns: `AI gaming NPC OR game AI`, `procedural generation AI game`, `AI game testing OR QA`, `AI esports OR competitive gaming`

### Scientific Research

Patterns: `AI scientific discovery OR research`, `AI lab automation`, `AI hypothesis generation`, `AI materials science OR chemistry`, `AI climate modeling OR simulation`

### Consumer AI Products

Patterns: `AI consumer app launch`, `AI smartphone feature OR mobile`, `site:producthunt.com AI consumer`, `AI home automation OR smart home`, `AI personal assistant device`

---

## Safety & Ethics (Phase 9)

Patterns: `AI safety research OR alignment`, `AI ethics guidelines OR framework`, `AI regulation OR policy`, `site:anthropic.com alignment OR safety`, `AI incident OR failure`, `interpretability OR explainable AI`, `AI bias fairness`

Collect: safety research, alignment breakthroughs, policy/regulation, ethics frameworks, incident reports, interpretability, bias/fairness research.

---

## Open Source Ecosystem (Phase 10)

Patterns: `open source AI model release`, `open weights OR open source LLM`, `site:huggingface.co open source`, `AI dataset release OR open data`, `EleutherAI OR LAION OR BigScience`

Collect: open source model releases, open weight models, new datasets, community projects, democratization initiatives.

---

## Infrastructure & Hardware (Phase 11)

Patterns: `AI chip OR AI accelerator`, `GPU OR TPU OR AI compute`, `Groq OR Cerebras OR AI hardware`, `AI training infrastructure`, `model serving OR inference optimization`, `edge AI OR on-device AI`, `AI datacenter OR compute cluster`

Collect: chip announcements, custom silicon, training infrastructure, model serving, inference optimization, edge AI, datacenter architecture.

---

## Regional Developments (Phase 12)

Patterns: `European AI OR EU AI regulation`, `China AI OR Chinese AI development`, `Japan AI OR Japanese AI`, `Korea AI OR Korean AI`, `India AI development`, `Mistral OR French AI`

Collect: European AI (Mistral, regulation), Chinese AI (DeepSeek, ByteDance), Japanese/Korean initiatives, Indian ecosystem, regional policy, non-US AI companies.

---

## YouTube AI Videos (Phase 13)

Search patterns:

- `AI tutorial OR explanation site:youtube.com {date_range}`
- `LLM "large language model" site:youtube.com {date_range}`
- `AI news OR update site:youtube.com {date_range}`
- `"AI paper" review OR breakdown site:youtube.com {date_range}`
- `AI coding assistant demo site:youtube.com {date_range}`

Prioritize: paper breakdowns, tool demos, technical deep dives, practical tutorials. Filter out hype/clickbait. Use `youtube-{channel}-{video-slug}` as story_id.

Priority channels are listed in `sources.md` under "YouTube AI Channels".

---

## Cool & Thought-Provoking (Phase 14)

Patterns: `AI "mind-blowing" OR "incredible" demo`, `AI art OR creative unexpected`, `AI philosophical implications`, `site:reddit.com/r/singularity`, `AI ethics dilemma OR thought experiment`

Collect: viral demos, creative/artistic applications, philosophical thought experiments, "wait, that's possible now?" moments, unusual cross-domain applications. Must genuinely provoke thought, not clickbait.

---

## Newsletters & Blogs (Phase 15)

### Specific Known Sources

Check high-quality sources listed in `sources.md` under "Blogs & Newsletters" and "Indie & Smaller Bloggers".

Search: `site:{blog_url} {date_range}` or `site:{blog_url} 2026-02`

### Broader Platform Searches (REQUIRED)

Always search these platforms:

- **Substack**: `site:substack.com AI OR LLM {date_range}`
- **Medium**: `site:medium.com AI machine learning {date_range}`
- **DEV.to**: `site:dev.to AI tutorial OR insights {date_range}`
- **General**: `AI blog post {date_range} analysis insights`, `"AI engineering" blog post this week`
- **Newsletters**: `"AI newsletter" OR "ML newsletter" latest issue`, `AI weekly newsletter {date_range}`

When finding new quality blogs, note in digest under "🆕 New Blogs & Sources Discovered" and consider suggesting addition to sources.md.

---

## Friday Weekly Recap

When running on Friday, enable broader research:

- Extended date range: full week (7 days)
- Additional patterns: `"this week in AI"`, `"AI weekly roundup"`, `top AI stories week`
- Lower-tier sources: more Reddit, Twitter
- Add "📅 Stories You Might Have Missed" section
- Title: "Weekly Recap" instead of "Daily Digest"

### Blog Discovery (Friday)

Search for new indie bloggers:

- `"AI blog" OR "ML blog" interesting {date_range}`
- `site:substack.com AI machine learning`
- `site:medium.com AI LLM practical`
- `site:dev.to AI machine learning tutorial`
- `HN "Show HN" AI blog`

Quality signals: original content, technical depth, practical examples, posted in last 3 months.
