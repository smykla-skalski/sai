# 100 Go Mistakes - Code Review Reference

Source: https://100go.co/

## Code Organization (1-16)

| # | Issue | Check For |
|---|-------|-----------|
| 1 | **Variable Shadowing** | Name redeclared in inner block → confusion, hard-to-catch errors |
| 2 | **Nested Code** | Omit `else` when `if` returns; flip conditions; return early; align happy path left |
| 3 | **Init Functions** | Limited error handling; complicates testing; requires globals → use dedicated init funcs |
| 4 | **Getters/Setters** | Not idiomatic; use only when needed for forward compat |
| 5 | **Interface Pollution** | Discover interfaces, don't create upfront; add when needed, not foreseen |
| 6 | **Producer-Side Interfaces** | Keep interfaces on consumer side; implicit satisfaction enables consumer-driven design |
| 7 | **Returning Interfaces** | Return concrete implementations; interfaces restrict flexibility, create dependencies |
| 8 | **`any` Overuse** | Reserve for genuine needs (marshaling); avoid overgeneralization |
| 9 | **Premature Generics** | Solve real problems, not anticipated; consider duplication vs clarity trade-off |
| 10 | **Type Embedding** | Don't embed for syntactic sugar; don't promote private behaviors |
| 11 | **No Functional Options** | Use for config: unexported struct + option funcs returning `func(*options) error` |
| 12 | **Misorganization** | Organize by context/layer; name packages after what they provide; avoid nano/huge packages |
| 13 | **Utility Packages** | No `common`, `util`, `shared` → use specific, meaningful names |
| 14 | **Package Collisions** | Use distinct var names or import aliases |
| 15 | **Missing Docs** | Document all exported elements; start with element name; use `// Package` prefix |
| 16 | **No Linters** | Use `go vet`, `errcheck`, `golangci-lint`, `gofmt`/`goimports` |

## Data Types (17-29)

| # | Issue | Check For |
|---|-------|-----------|
| 17 | **Octal Literals** | Use `0o` prefix (not `0`); binary `0b`, hex `0x`; underscore separators `1_000_000` |
| 18 | **Integer Overflow** | Runtime overflows silent; compile-time errors; implement detection if needed |
| 19 | **Floating-Point** | Compare within delta; group by magnitude; mult/div before add/sub |
| 20 | **Slice Length/Capacity** | Length = accessible elements; capacity = backing array room |
| 21 | **Slice Init** | Initialize with known length/capacity → reduces allocations, GC pressure |
| 22 | **Nil vs Empty Slice** | Nil = unallocated; empty = zero length but allocated; don't distinguish in APIs |
| 23 | **Empty Check** | Use `len(s) == 0` (works for nil and empty) not nil check |
| 24 | **Slice Copy** | `copy` uses min(len(dst), len(src)) |
| 25 | **Slice Append Side Effects** | Use copy or full slice `s[low:high:max]` to prevent shared array mutations |
| 26 | **Slice Memory Leaks** | Nil excluded pointer elements; copy large slices to avoid capacity leaks |
| 27 | **Map Init** | Create with initial size if known → avoids rebalancing |
| 28 | **Map Memory Leaks** | Maps grow, never shrink → recreate or use pointers |
| 29 | **Value Comparison** | `==` for comparables (bool, numeric, string, chan, ptr, structs, arrays); `reflect.DeepEqual` or custom for slices/maps/funcs |

## Control Structures (30-35)

| # | Issue | Check For |
|---|-------|-----------|
| 30 | **Range Copies** | Range values are copies → use index `slice[i].field` or pointer fields |
| 31 | **Range Evaluation** | Expression evaluated once at loop start → modifications don't affect iteration |
| 32 | **Range Pointers** | Not relevant Go 1.22+ (loop var semantics changed) |
| 33 | **Map Iteration Order** | Unordered; no insertion order; non-deterministic; additions during iteration not guaranteed |
| 34 | **Break Statement** | Breaks innermost for/switch/select → use labels for outer loops |
| 35 | **Defer in Loop** | Executes at func return, not iteration end → extract to helper func |

## Strings (36-41)

| # | Issue | Check For |
|---|-------|-----------|
| 36 | **Rune Concept** | Rune = Unicode code point; UTF-8 = 1-4 bytes; `len()` = bytes not runes |
| 37 | **String Iteration** | Range gives rune indices/values; `[]rune(s)` for indexing; `s[i]` gives bytes |
| 38 | **Trim Functions** | `TrimRight/Left` remove char set; `TrimSuffix/Prefix` remove exact string |
| 39 | **String Concat** | Use `strings.Builder` in loops; `Grow()` for 99% faster vs `+=` |
| 40 | **String Conversions** | bytes package mirrors strings → avoid unnecessary conversions |
| 41 | **Substring Leaks** | Substrings share backing array → use `strings.Clone` (Go 1.18+) |

## Functions/Methods (42-47)

| # | Issue | Check For |
|---|-------|-----------|
| 42 | **Receiver Type** | Pointer: mutation, sync types, large objects; Value: immutable, maps/funcs/chans, small structs |
| 43 | **Named Results** | Use for multiple same-type returns; auto zero-init; enables naked returns |
| 44 | **Named Result Side Effects** | Zero-initialized → assign in all code paths to avoid returning nil instead of error |
| 45 | **Nil Receiver** | Don't return nil pointer → return explicit nil to avoid non-nil interface value |
| 46 | **Filename Input** | Accept `io.Reader` not filename → improves reusability, testing |
| 47 | **Defer Evaluation** | Args/receiver evaluate immediately → pass pointers or wrap in closure |

## Error Management (48-54)

| # | Issue | Check For |
|---|-------|-----------|
| 48 | **Panicking** | Only for unrecoverable: programmer errors, mandatory dependency failures |
| 49 | **Error Wrapping** | `%w` for context/marking (creates coupling); `%v` for transformation (no coupling) |
| 50 | **Error Type Comparison** | Use `errors.As(err, &target)` with wrapped errors (not `==`) |
| 51 | **Error Value Comparison** | Use `errors.Is(err, sentinel)` with wrapped errors (not `==`) |
| 52 | **Handling Twice** | Handle once (log OR return); wrapping allows propagation with context |
| 53 | **Not Handling** | Never ignore; document intentional `_` assignment |
| 54 | **Defer Errors** | Capture and handle: `defer func() { if err := recover()... }()` |

## Concurrency: Foundations (55-60)

| # | Issue | Check For |
|---|-------|-----------|
| 55 | **Concurrency vs Parallelism** | Concurrency = task interleaving; parallelism = simultaneous execution |
| 56 | **Concurrency Speed** | Adds overhead; only helps I/O-bound; CPU-bound often slower → benchmark |
| 57 | **Channels vs Mutexes** | Channels: coordinate/communicate; mutexes: protect shared state |
| 58 | **Race Problems** | Data race = unsync concurrent access; race condition = timing-dependent → use `-race` |
| 59 | **Workload Type** | I/O-bound benefits; CPU-bound typically doesn't |
| 60 | **Contexts** | Deadline (timeout); cancellation (signal); values (context data); detect via `ctx.Done()` |

## Concurrency: Practice (61-74)

| # | Issue | Check For |
|---|-------|-----------|
| 61 | **Context Propagation** | Request-scoped only; don't propagate across request boundaries |
| 62 | **Goroutine Lifecycle** | Provide stop mechanism (context cancel, stop channel); prevent leaks |
| 63 | **Loop Variables** | Capture via closure param: `go func(idx int) { }(i)` |
| 64 | **Select Determinism** | Multiple ready channels = random selection; non-deterministic |
| 65 | **Notification Channels** | Use `chan struct{}` for signaling; lightweight, clear intent |
| 66 | **Nil Channels** | Send/receive blocks forever; use to disable select branches |
| 67 | **Channel Size** | Unbuffered (0) = sync; buffered (>0) = async; default unbuffered |
| 68 | **String Formatting Side Effects** | `fmt` can cause races/deadlocks → test with `-race` |
| 69 | **Append Races** | Shared slice append without sync = data race → use mutex |
| 70 | **Mutex Scope** | Protect entire operation (check+modify), not just variable |
| 71 | **sync.WaitGroup** | `Add(n)` before starting; `Done()` in each; `Wait()` after |
| 72 | **sync.Cond** | Use for efficient condition waiting vs polling |
| 73 | **errgroup** | Simplifies goroutine groups with error handling + context cancel |
| 74 | **Copying Sync Types** | Never copy mutex/chan/sync types → pass pointers |

## Standard Library (75-81)

| # | Issue | Check For |
|---|-------|-----------|
| 75 | **Time Duration** | Use typed constants: `time.Second` not raw ints |
| 76 | **time.After Leaks** | Use `time.NewTimer` + `defer timer.Stop()` |
| 77 | **JSON Mistakes** | Struct tags; type conversions; null handling |
| 78 | **SQL Mistakes** | Prepared statements; `rows.Err()` after iteration; close resources |
| 79 | **Resource Closing** | `defer resp.Body.Close()`, `rows.Close()`, `file.Close()` |
| 80 | **HTTP Response Return** | Always `return` after `http.Error()` to prevent header overwrite |
| 81 | **Default HTTP Client** | Configure timeouts (client + server read/write/idle) |

## Testing (82-91)

| # | Issue | Check For |
|---|-------|-----------|
| 82 | **Test Categories** | Build tags `//go:build integration`, env vars, `-short` mode |
| 83 | **Race Flag** | Run `go test -race ./...` |
| 84 | **Test Modes** | `-parallel N` for concurrency; `-shuffle on` for randomization |
| 85 | **Table-Driven Tests** | Array of test cases with inputs/expected outputs |
| 86 | **Sleep in Tests** | Use channels/sync primitives, not sleep |
| 87 | **Time API** | Mock time operations; use `time.Time` fields |
| 88 | **Test Utilities** | `httptest.NewServer()`, `iotest.TimeoutReader()` |
| 89 | **Benchmarks** | `b.ResetTimer()`, `b.ReportAllocs()`, avoid compiler optimizations |
| 90 | **Test Features** | Subtests `t.Run()`, helpers `t.Helper()`, benchmarks, examples, fuzzing |
| 91 | **Fuzzing** | Auto-generate test cases for edge cases/crashes |

## Optimizations (92-101)

| # | Issue | Check For |
|---|-------|-----------|
| 92 | **CPU Caches** | Cache line contention in concurrent code |
| 93 | **False Sharing** | Multiple goroutines accessing same cache line → pad structs |
| 94 | **Instruction Parallelism** | Structure code to enable parallel instruction execution |
| 95 | **Data Alignment** | Allocate larger types first; misalignment = penalties |
| 96 | **Stack vs Heap** | Stack: fast, func-scoped; heap: slow, GC'd; minimize allocations |
| 97 | **Reduce Allocations** | `sync.Pool`, API optimization, compiler inlining |
| 98 | **Inlining** | Small funcs inlined → speed vs binary size trade-off |
| 99 | **Diagnostics** | pprof (CPU/memory/goroutine profiling), trace (execution) |
| 100 | **GC** | Understand triggers, tuning options, latency impact |
| 101 | **Container Limits** | Go doesn't see Docker/K8s limits → explicit config |

## Common Patterns

**Error Handling:**
```go
// Wrap with context
return fmt.Errorf("fetch user: %w", err)

// Check wrapped errors
errors.As(err, &targetType)
errors.Is(err, sentinelErr)
```

**Concurrency:**
```go
// Goroutine lifecycle
ctx, cancel := context.WithCancel(...)
defer cancel()

// Loop var capture
for i := range items {
  go func(idx int) { use(items[idx]) }(i)
}

// Resource cleanup
defer resp.Body.Close()
```

**Performance:**
```go
// Preallocate
s := make([]T, 0, knownSize)
m := make(map[K]V, knownSize)

// String building
var b strings.Builder
b.Grow(estimatedSize)
```
