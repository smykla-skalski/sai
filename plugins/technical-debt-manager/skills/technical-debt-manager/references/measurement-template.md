# Measurement Template

Append this section to the issue body after the Summary table. Fill in baseline values from the audit.

```markdown
## Measurement & Tracking

### Baseline Metrics (from this audit)
- Total findings: {count}
- Critical/Quick Win ratio: {critical+quick_wins}/{total}
- Categories with most debt: {top 2-3 categories}
- Estimated total effort: {rough sum}

### Re-audit Cadence
- **Quarterly:** Full re-audit recommended (run this skill again)
- **Monthly:** Spot-check top 3 priority items
- **Per-sprint:** Address at least 1 quick win

### KPIs to Track
- **Complexity trend:** Average cyclomatic complexity per module (should decrease)
- **Bug density:** Bugs per KLOC in debt-heavy modules vs clean modules
- **Release frequency:** Time between deployments (debt reduction should improve)
- **SATD count:** Total TODO/FIXME/HACK comments (should decrease quarterly)
- **Dependency freshness:** % of deps within 1 major version of latest
```
