---
name: staff-resume
description: Build and refine staff-level engineering resumes through interactive coaching, research-backed best practices, and per-job tailoring. Use when building, improving, or tailoring a resume for Staff/Principal engineer roles.
argument-hint: "<resume-path> [--job-url URL] [--mode coach|tailor|full]"
user-invocable: true
allowed-tools: AskUserQuestion, Edit, Glob, Read, WebFetch, WebSearch, Write
context: fork
agent: general-purpose
---

# Staff Resume Builder

## Arguments

Parse from `$ARGUMENTS`:

- **resume-path:** Path to LaTeX or markdown resume file (required — ask if not provided)
- **--job-url:** Optional — URL of specific job posting to tailor for
- **--mode:** Optional — `coach` (default), `tailor`, `full` (both)

## Scope

Build and refine staff/principal-level engineering resumes. Not designed for non-technical resumes, cover letters, junior/mid-level roles, or academic CVs.

---

## Phase 1: Load Context

### Read Resume

1. Read the resume file at provided path
2. Parse sections: summary, skills, experience, education, activities, open source
3. Identify current structure, bullet points, metrics, scope language

### Read Job Posting (if --job-url provided)

1. Fetch job posting URL
2. Extract: title, level, requirements, tech stack, team description, company info
3. Identify keywords, scope signals, archetype match

---

## Phase 2: Research Best Practices

Read [references/staff-resume-patterns.md](references/staff-resume-patterns.md) in full before starting this phase.

### Web Searches (3-4 searches)

Use WebSearch for each query:

1. `"staff engineer resume" best practices {current_year}` — latest trends
2. `"staff software engineer resume" quantify impact examples` — bullet point patterns
3. If job-url provided: `"{company_name}" engineering culture interview process staff` — company-specific intel
4. `ATS optimization resume {current_year} software engineer` — latest ATS advice

### Synthesize Research

Combine fresh findings with the patterns from the reference file. Note any new patterns or changes from prior research.

---

## Phase 3: Gap Analysis

Evaluate the current resume against these staff-level criteria. For each criterion, mark as **present** or **missing/weak** with specific evidence.

### Structural Gaps

| Criterion | Check |
|-----------|-------|
| **Summary/positioning** | Present? Positions as Staff, not Senior? |
| **Skills organization** | Categorized by domain or flat list? |
| **Section order** | Summary → Skills → Experience → OSS/Leadership → Speaking → Education? |
| **Length** | 1-2 pages? Every line adds value? |
| **ATS friendliness** | Single column? Standard headers? No graphics? |

### Content Gaps

| Criterion | Check |
|-----------|-------|
| **Scope language** | Uses "org-wide", "cross-team", "company-wide"? Or weak: "helped", "worked on"? |
| **Decision authority** | Uses "Architected", "drove", "established"? Or weak: "contributed to", "participated"? |
| **Impact metrics** | Every role has quantified business impact? Revenue, scale, reliability? |
| **Cross-team signals** | Evidence of influence beyond own team? |
| **Technical strategy** | RFCs, architecture decisions, roadmap influence? |
| **Mentoring/leadership** | People grown, teams built, hiring bar set? |
| **Open source framing** | Prominent or buried? |

### Archetype Alignment (if job-url provided)

Determine which archetype the target role maps to (see reference file for definitions). Assess whether the resume's emphasis aligns with the target archetype.

### Present Gap Analysis

Show results as a clear table of present/missing/weak findings, then use AskUserQuestion:

> "Here's how your resume maps against staff-level criteria. Which gaps should we tackle first? Or should we go through all of them systematically?"

---

## Phase 4: Interactive Coaching Session

Skip this phase when `--mode tailor`. Re-read [references/staff-resume-patterns.md](references/staff-resume-patterns.md) Senior vs Staff Language section before rewriting bullets.

**This is the core of the skill.** Go deep on each role, one at a time.

### For Each Role (most recent first)

#### Step 1: Challenge Current Bullets

For each bullet point, ask probing questions:

<example>
- "This bullet says you 'drove X initiative.' How many teams were involved? What was the business outcome?"
- "You mention 800% throughput improvement. What was the business context? How many users did this affect?"
- "This reads as team-level scope. Was there any cross-team or org-wide impact you're not mentioning?"
</example>

#### Step 2: Mine for Hidden Achievements

Ask these questions systematically:

**Scope expansion:**
- "What's the biggest technical decision you made that affected teams beyond yours?"
- "Did you write any RFCs, ADRs, or design docs that became org standards?"
- "Were there times you influenced the product roadmap through technical insight?"

**People impact:**
- "How many engineers did you mentor? Any get promoted?"
- "Did you establish any hiring processes, interview standards, or onboarding programs?"
- "Did you run any guilds, working groups, or cross-team initiatives?"

**Business impact:**
- "Can you connect any technical work to revenue, cost savings, or reliability improvements?"
- "What would have happened if your work didn't exist? What was the counterfactual?"
- "What scale numbers can you attach? Users, RPS, services, data volume?"

**Open source / community:**
- "How many external contributors did you coordinate with?"
- "What companies use the project in production?"
- "What was your specific architectural contribution vs general maintenance?"

#### Step 3: Rewrite Bullets Together

For each bullet, propose a staff-level rewrite using the XYZ formula from the reference file.

<example description="Before/after bullet rewrite">
Before: "Improved Kafka pipeline performance by 800%"
After: "Architected event-driven pipeline redesign processing 2M events/day, reducing p99 latency 800% across 12 downstream services — adopted as org-wide messaging standard"
</example>

**Power verbs (Staff-level):**
```
architected, drove, established, influenced, defined strategy,
evaluated trade-offs, owned end-to-end, scaled from X to Y,
founded initiative, shaped roadmap, designed, led, pioneered
```

**Verbs to eliminate (Senior-level):**
```
helped, assisted, worked on, participated in, was responsible for,
involved in, contributed to, basic knowledge of
```

Show before/after for each bullet and use AskUserQuestion for confirmation or additional context.

### Summary Section

After processing all roles, draft 3 summary options:

1. **Platform/Infra Focus** — for Stripe, Databricks, traditional infra roles
2. **AI Infra Pivot** — for Anthropic, OpenAI, AI-adjacent roles
3. **Open Source Emphasis** — for CNCF-adjacent companies, community-valued orgs

Ask user to pick one or customize.

### Skills Section

Propose categorized skills layout:

```
Systems & Languages:    [primary], [secondary] | [learning]
Distributed Systems:    [patterns, not just tools]
Cloud Native:           [tools with (contributor) tags where applicable]
Data & Messaging:       [tools]
Observability:          [tools with (contributor) tags]
Cloud Platforms:        [platforms] | [patterns like multi-cloud]
AI/ML Infrastructure:   [honest representation of current skills]
```

Rules:
- Remove anything assumed at Staff level (Git, SQL, basic tools)
- Never say "basic" — either you know it or don't list it, because "basic" signals a hobbyist level that undermines Staff positioning
- Add "(contributor)" for OSS projects you maintain
- Categorize by domain, not alphabetically

---

## Phase 5: Job-Specific Tailoring (if job-url provided)

Skip this phase when `--mode coach`. Re-read [references/staff-resume-patterns.md](references/staff-resume-patterns.md) ATS Optimization and Staff Archetypes sections before tailoring.

### Keyword Mapping

1. Extract all technical terms and requirements from job posting
2. Map to user's experience (exact match, partial match, gap)
3. For exact matches: ensure resume mirrors exact language from JD
4. For partial matches: suggest how to frame existing experience
5. For gaps: honestly flag them, suggest how to acknowledge adjacent experience

### ATS Optimization

Apply ATS rules from the reference file. Ensure both acronyms and spelled-out terms appear naturally.

### Archetype Alignment

Reorder and emphasize bullets matching the target archetype (see reference file for archetype → bullet mapping).

### Tailored Summary

Generate a role-specific summary that mirrors the JD language while maintaining authenticity.

---

## Phase 6: Generate Output

### Resume Output

Generate the tailored resume preserving the user's original template/style but with:
- Restructured sections per recommendations
- Rewritten bullets from coaching session
- Updated skills section
- New or revised summary
- Properly ordered sections

### Companion Analysis

Save a markdown analysis alongside the resume:

```markdown
# Resume Tailoring: {Company} — {Role Title}

**Date:** {date}
**Job URL:** {url}
**Archetype:** {archetype}

## Keyword Coverage
- ✅ Exact matches: [list]
- 🟡 Partial matches: [list]
- ❌ Gaps: [list]

## Key Customizations Made
- [bullet changes]
- [summary choice]
- [skills emphasis]

## Interview Talking Points
- [3-5 points connecting resume to role]

## Honest Assessment
- Strengths for this role: [list]
- Weaknesses to prepare for: [list]
```

---

## Phase 7: Final Review

### Quality Checklist

Before delivering, verify:

- [ ] Every bullet has a quantified metric or concrete scope
- [ ] No "helped", "assisted", "worked on", "responsible for" language
- [ ] Summary positions as Staff, not Senior
- [ ] Skills organized by domain, no assumed-skills listed
- [ ] Open source work has its own prominent section (if applicable)
- [ ] Speaking/community has its own section (if applicable)
- [ ] 2 pages max, every line adds value
- [ ] If job-tailored: keywords from JD are present naturally
- [ ] No "basic knowledge of" anything — to prevent diluting the Staff-level signal
- [ ] Career progression shows increasing scope

### Present Final Output

Show:
1. The complete resume
2. Summary of all changes made
3. Tailoring analysis (if job-specific)
4. Suggested next steps (networking, referrals, cover letter points)

---

## Error Handling

- **No resume path:** Ask user to provide file path
- **Can't parse resume:** Ask user to paste raw text content
- **No job URL in tailor mode:** Ask for URL or switch to coach mode
- **Job URL fetch fails:** Ask user to paste job description text
- **User unsure about metrics:** Help estimate with probing questions ("roughly how many?", "order of magnitude?")
- **User pushes back on rewrite:** Respect their voice — offer alternatives, don't force

---

## Sources

- [Tech Interview Handbook — Resume Guide](https://www.techinterviewhandbook.org/resume/)
- [StaffEng.com — Staff Archetypes](https://staffeng.com/guides/staff-archetypes/)
- [Enhancv — Staff SWE Resume Guide](https://enhancv.com/resume-examples/staff-software-engineer/)
- [CVOwl — Staff SWE Resume Tips](https://www.cvowl.com/blog/staff-software-engineer-resume-writing-tips)
- [Toptal — ATS Trends 2025](https://www.toptal.com/techresume/career-advice/the-perfect-tech-resume-in-2025-key-trends-ats-keywords-and-formatting-tips)
- [Columbia Career — Strong Bullet Points](https://www.careereducation.columbia.edu/resources/resumes-impact-creating-strong-bullet-points)
- [Interview Kickstart — FAANG Resume](https://www.interviewkickstart.com/blog/software-engineer-resume-for-faang-companies)
