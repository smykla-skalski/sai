# staff-resume

Build and refine staff-level engineering resumes through interactive coaching, research-backed best practices, and per-job tailoring.

## Features

- **Gap analysis** against staff-level criteria (scope language, decision authority, impact metrics, cross-team signals)
- **Interactive coaching** — probing questions to mine hidden achievements from each role
- **Bullet rewrites** using XYZ formula with staff-level power verbs
- **Job-specific tailoring** with keyword mapping, ATS optimization, and archetype alignment
- **Staff archetypes** — Tech Lead, Architect, Solver, Right Hand emphasis mapping
- **Multiple summary options** — Platform/Infra, AI Infra Pivot, Open Source focus

## Usage

```
/staff-resume path/to/resume.tex
/staff-resume path/to/resume.tex --job-url https://example.com/job
/staff-resume path/to/resume.md --mode tailor --job-url https://example.com/job
/staff-resume path/to/resume.tex --mode full --job-url https://example.com/job
```

### Modes

- **coach** (default) — gap analysis + interactive coaching + bullet rewrites
- **tailor** — job-specific keyword mapping, ATS optimization, archetype alignment
- **full** — both coaching and tailoring

## Reference Material

- `references/staff-resume-patterns.md` — hiring manager priorities, senior vs staff language, XYZ formula, archetypes, ATS rules
