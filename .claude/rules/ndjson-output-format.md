# NDJSON output format for review-skill

All review-skill check scripts and the orchestrator (validate.py) emit NDJSON. Every line has `kind` as the first key.

## Record types

### CheckRecord (`kind: "check"`)

```json
{"kind": "check", "check": "FM-name-format", "pass": true, "level": "pass", "tier": "C4", "detail": "Name matches [a-z0-9-]{1,64}"}
```

Key order: `kind`, `check`, `pass`, `level`, `tier` (optional), `detail`, `item` (optional).

### SignalRecord (`kind: "signal"`)

```json
{"kind": "signal", "signal": "FK-P1", "type": "positive", "detected": true, "detail": "5 phases found"}
```

Key order: `kind`, `signal`, `type`, `detected`, `detail`.

### FindingRecord (`kind: "finding"`)

```json
{"kind": "finding", "file": "scripts/foo.sh", "line": 42, "check": "CL-S08", "severity": "medium", "message": "Unquoted variable", "evidence": "echo $var"}
```

Key order: `kind`, `file`, `line`, `check`, `severity`, `message`, `evidence` (optional).

### SummaryRecord (`kind: "summary"`)

```json
{"kind": "summary", "total": 5, "passed": 3, "failed": 2, "skipped": 0, "info": 0}
```

Key order: `kind`, `total`, `passed`, `failed`, `skipped` (when > 0), `info` (when > 0), then extras sorted alphabetically.

## Check ID format

Every check ID follows `{PREFIX}-{slug}`:

- `PREFIX` is 2 uppercase letters, unique per script
- `slug` is lowercase kebab-case
- Informational checks append `-info` as last segment
- Regex: `^[A-Z]{2}-[a-z][a-z0-9-]*(-info)?$`

### Prefix assignments

| Script | Prefix |
| :-- | :-- |
| validate.py (frontmatter) | `FM` |
| check-config.py | `CF` |
| check-content.py | `CT` |
| check-file-refs.py | `FR` |
| check-scripts-dir.py | `SD` |
| check-references.py | `RF` |
| check-read-gates.py | `RG` |
| check-preprocessing.py | `PP` |
| check-ask-user.py | `AQ` |
| check-flag-coverage.py | `FC` |
| check-hooks.py | `HK` |
| check-best-practices.py | `BP` |
| check-fork-candidate.py | `FK` |
| check-lint.py | `CL` |

## Result levels

| Level | `pass` | Meaning |
| :-- | :-- | :-- |
| `"pass"` | `true` | Check ran, passed |
| `"fail"` | `false` | Check ran, found violations |
| `"info"` | `true` | Advisory finding, never fails |
| `"skip"` | `true` | Preconditions not met |

Use static constructors: `CheckRecord.ok()`, `.fail()`, `.info()`, `.skip()`.

## Tier field

Optional string mapping check ID to checklist tier (C1-C7, I1-I29, P1-P17). Regex: `^[CIP]\d{1,2}$`.

## Detail message style

Enforced programmatically in `CheckRecord.__post_init__`:

- Non-empty
- Max 500 chars
- Starts with uppercase letter
- No trailing period

Style conventions (not enforced programmatically):

- Line numbers: `L{n}` format
- File paths: single-quoted relative (`'references/foo.md'`)
- Counts: `{n} {noun}(s)` for dynamic counts
- Fail details: problem description, then fix hint after ` - ` separator
- First-hit evidence: `{n} violation(s) found - first: {snippet}` (truncate to 80 chars)

## Multiple results per check ID

Allowed when iterating over a dynamic set. Use `item` field to identify the specific entity.

## Signal ID format

For check-fork-candidate.py signals: `{PREFIX}-{letter}{digit}` where PREFIX is `FK`. Regex: `^[A-Z]{2}-[A-Z]\d{1,2}$`.
