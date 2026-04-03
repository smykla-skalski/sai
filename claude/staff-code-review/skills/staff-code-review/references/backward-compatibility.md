# Backward Compatibility — Deep Reference

Comprehensive checklist for Agent 5 (Backward Compatibility). Organized by change surface with detection heuristics and severity classification.

## Core Principle

A backward-compatible change allows existing consumers to continue working without modification. The burden of proof is on the change author: assume every observable behavior has a dependent consumer (Hyrum's Law).

**Three compatibility dimensions** — a change can break one without breaking others:

1. **Source compatibility**: does consumer code still compile/parse?
2. **Binary/wire compatibility**: does it link/load/deserialize without recompilation?
3. **Behavioral compatibility**: does it produce the same observable results?

---

## Tier 1: Blocking — Existing Consumers Will Fail

These cause immediate breakage for consumers. Must fix or provide migration path before merge.

### API Surface Removals & Renames

**Detection**: removed/renamed endpoints, fields, methods, types, parameters.

- Endpoint/route removal or rename
- Field removal from response body
- Method/function removal from public interface
- Type/class removal or rename
- Parameter removal or rename (breaks named arguments, reflection)
- Enum variant removal

**Heuristic**: any deletion or rename in a public surface is breaking until proven otherwise. Check Research Brief "Callers & Consumers" for usage count.

### Type Changes

**Detection**: field/parameter/return type changes, even widening.

- `string` to `int` (or any type change in existing fields)
- `int32` to `int64` (breaks binary compat in some languages)
- `optional` to `required` (rejects previously valid input)
- Nullable to non-nullable (or vice versa — changes behavior for existing defaults)
- Array to single value (or vice versa)
- Changing error/exception types to non-derived types

### Required Field Additions

**Detection**: new fields/parameters that existing requests won't include.

- New required request parameter without default
- New NOT NULL column without default value
- New required config key without fallback
- Making previously optional field required

### Wire Format Changes

**Detection**: serialization changes that break existing readers.

- Serialization format change (JSON to protobuf, XML to JSON)
- JSON key casing change (`snake_case` to `camelCase`)
- Float representation change (number vs string)
- Date format change (ISO 8601 variants, timezone handling)
- Encoding change (UTF-8 to UTF-16)
- Compression algorithm change
- Message envelope structure change

### Protobuf/gRPC Specific

**Detection**: wire-breaking changes in proto definitions.

- Field number reuse (ambiguous wire decoding — **always blocking**)
- Field number change (equivalent to delete + add)
- Removing field without `reserved` keyword
- Changing field wire type
- Moving fields into/out of `oneof`
- Changing RPC request/response message types
- Changing streaming mode (unary to streaming or vice versa)
- File-level option changes affecting codegen (`java_package`, `go_package`)

### Database Schema — Destructive

**Detection**: schema changes that break current application version.

- Column removal (breaks reads from current code)
- Column rename (breaks all queries referencing old name)
- Column type change (data truncation, precision loss)
- Table removal or rename
- Constraint additions (CHECK, UNIQUE, FK) that reject existing data
- Adding NOT NULL without default on populated table

**Critical rule**: never couple schema and code changes in the same deploy. Schema must be independently backward-compatible.

---

## Tier 2: Warning — Potential Breakage Depending on Usage

May break some consumers depending on how they use the API. Assess with codebase evidence.

### Behavioral / Semantic Changes

**Detection**: same interface, different observable behavior.

- Default value changes (sort order, page size, timeout, locale)
- Algorithm changes (rounding mode, hashing, encoding)
- Error handling changes (new exception types, different error codes)
- Side effect changes (sync to async, immediate to batched, ordering)
- Null/empty handling changes
- Idempotency changes (operation was idempotent, now isn't)
- Timing changes (operation that was instant now involves I/O)
- Event ordering/frequency changes

**Subtle examples**:
- Python 2 `round(0.5) = 1` vs Python 3 `round(0.5) = 0` (banker's rounding) — silent
- Auth API switching from 405 to 401 — clients checking specific codes break
- Moving writes from sync to async batch — immediate queries return stale data

### Hyrum's Law — Implicit Contracts

**Detection**: changes to behaviors not in the contract but potentially depended upon.

**Six categories of implicit observable behaviors:**

1. **Ordering**: JSON key order, array element order, map iteration order
2. **Formatting**: whitespace in responses, URL structure, header casing
3. **Error messages**: clients may parse error text for routing/retry decisions
4. **Timing**: latency characteristics used as health signals
5. **Precision**: numeric precision, float representation
6. **Size patterns**: response size used for progress estimation

**Heuristic**: if a JSON library change, sort algorithm swap, or performance optimization could alter the output shape/order/timing, flag it. Check "Callers & Consumers" for downstream parsers.

**Mitigation**: document what IS vs ISN'T contractual. Consider chaos mocks (randomize non-contractual behaviors) to prevent implicit dependencies from forming.

### New Enum Values in Responses

**Detection**: adding values to enums returned to consumers.

- Breaks clients with exhaustive `switch`/`match` (no default case)
- Particularly dangerous in strongly-typed languages (Go, Rust, Java)
- Safe only if API contract documents "may add values in future"

### Configuration / CLI / Environment

**Detection**: changes to config surface that alter existing behavior.

- Removed or renamed env vars, config keys, CLI flags
- Changed default values that alter behavior
- Changed precedence order (flags > env > config)
- Changed value format/syntax requirements
- Feature flag default flip (off → on)
- Removed flag aliases
- Adding validation to previously unvalidated values
- Config file format change (YAML → TOML) without dual support

### Dependency Version Bumps

**Detection**: transitive compatibility breaks from dependency upgrades.

- Minimum SDK/runtime version increase (drops older platform support)
- Diamond dependency conflicts (upgrading A forces incompatible B)
- Peer dependency version range narrowing
- Dropping support for older language/runtime versions

---

## Tier 3: Info — Additive, Generally Safe

Low risk but worth noting for completeness.

- New optional field in response (safe unless consumer has strict schema validation)
- New endpoint or route (safe, no existing consumers)
- New optional parameter with sensible default
- New nullable database column
- New table or index (no existing queries affected)
- Additive protobuf changes (new field numbers, new messages)
- New enum values in request fields (old clients just don't send them)

---

## Detection Techniques

### What the Agent Should Do

For each changed file/endpoint/schema, systematically check:

1. **Surface scan**: identify all public API changes (added, modified, removed)
2. **Consumer impact**: use Research Brief "Callers & Consumers" to count affected consumers
3. **Contract check**: is the change covered by versioning/deprecation policy?
4. **Migration path**: if breaking, is there expand-and-contract or versioned endpoint?
5. **Rollback safety**: can the previous version still work after this deploys?

### Expand-Migrate-Contract Pattern

The gold standard for breaking changes:

1. **Expand**: add new columns/fields/endpoints alongside old (backward-compatible)
2. **Expand code**: write to both old and new
3. **Migrate**: backfill historical data
4. **Switch reads**: consumers start reading from new
5. **Contract code**: stop writing to old
6. **Contract schema**: drop old elements

**Flag when**: a PR makes a breaking change in a single step instead of using expand-and-contract.

### Versioning Check

- API version bumped appropriately? (major for breaking per semver)
- Deprecated endpoints annotated with sunset date?
- Migration guide provided for breaking changes?
- Changelog entry documents the breaking change?

---

## Cross-Cutting Concerns

### Rollback Compatibility

**The overlooked dimension**: can the system rollback to the previous version after this change deploys?

- Database migrations: are they reversible? Does old code work with new schema?
- Config changes: does old code handle new config format gracefully?
- Cache format changes: does old code handle new cache entries?
- Queue message format: can old consumers process new message shapes?

### Multi-Service Coordination

**Detection**: changes that require coordinated deployment across services.

- Shared protobuf/schema changes consumed by multiple services
- API contract changes between producer and consumer services
- Shared library version bumps requiring lockstep upgrades
- Feature flags that must be flipped across services simultaneously

### Data Compatibility

- Stored data written by new code must be readable by old code (rollback scenario)
- Serialized objects in caches, queues, or databases must remain deserializable
- File format changes must handle reading old format files

---

## Severity Calibration

| Severity | Criteria | Action |
|---|---|---|
| **blocking:** | Existing consumers will fail immediately. No migration path provided. | Must fix or add migration before merge |
| **issue:** | Breaking change with migration path, but path is incomplete or undocumented | Document migration, add deprecation notices |
| **question:** | Potentially breaking but need consumer usage data to assess | Ask author about known consumers, check telemetry |
| **suggestion:** | Non-breaking but could become breaking without guardrails | Recommend versioning strategy, deprecation policy |
| **thought:** | Additive change that's safe now but creates future compatibility surface | Note for awareness |

**Research Brief integration for severity decisions:**
- High caller count + breaking change = **blocking** (e.g., "47 callers makes this rename blocking")
- Zero callers + breaking change = downgrade to **suggestion** ("no consumers found, but add deprecation notice before removing")
- Internal-only API + breaking change = lower severity than public API
- Change behind feature flag = lower severity (can be toggled off)

---

## Sources

- Google AIP-180 — Backward Compatibility: https://google.aip.dev/180
- Buf Breaking Change Rules: https://buf.build/docs/breaking/rules/
- Microsoft .NET Compatibility Rules: https://learn.microsoft.com/en-us/dotnet/core/compatibility/library-change-rules
- PlanetScale — Backward Compatible DB Changes: https://planetscale.com/blog/backward-compatible-databases-changes
- Martin Fowler — Parallel Change: https://martinfowler.com/bliki/ParallelChange.html
- Prisma — Expand and Contract Pattern: https://www.prisma.io/dataguide/types/relational/expand-and-contract-pattern
- Hyrum's Law: https://www.hyrumslaw.com/
- Stack Overflow — Backwards Compatibility in Distributed Systems: https://stackoverflow.blog/2020/05/13/ensuring-backwards-compatibility-in-distributed-systems/
- GraphQL Schema Compatibility: https://the-guild.dev/graphql/hive/docs/management/non-breaking-changes
- Protobuf Backward and Forward Compatibility: https://earthly.dev/blog/backward-and-forward-compatibility/
- Kotlin Backward Compatibility Guidelines: https://kotlinlang.org/docs/api-guidelines-backward-compatibility.html
- InfoQ — Breaking Changes Beyond Semver: https://www.infoq.com/articles/breaking-changes-are-broken-semver/
- Silent Breaking Changes: https://dev.to/eugenioenko/identifying-silent-breaking-changes-1d13
