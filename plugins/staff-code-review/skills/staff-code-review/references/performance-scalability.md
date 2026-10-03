# Performance & Scalability — Deep Reference

Comprehensive checklist for Agent 4 (Performance & Scalability). Organized by severity tier with detection heuristics and framework-based analysis.

## Analysis Frameworks

Apply these frameworks to contextualize findings. Not every framework applies to every PR — pick what fits.

### USE Method (Brendan Gregg) — For Resources

**U**tilization, **S**aturation, **E**rrors for every resource the PR touches:

| Resource | Utilization | Saturation | Errors |
|---|---|---|---|
| CPU | % busy time | Run queue length | Machine check exceptions |
| Memory | Used / total | Swap usage, OOM kills | Allocation failures |
| Disk I/O | % busy | Wait queue depth | Device errors |
| Network | Bandwidth usage | Retransmits, drops | Interface errors |
| DB connection pool | Active / max | Queued waiters | Timeout errors |
| Thread/goroutine pool | Busy / total | Pending work queue | Rejected tasks |
| Mutex/lock | Hold time | Blocked waiters | Deadlocks |

Rule of thumb: 70%+ utilization is a warning, 100% is a bottleneck. Brief bursts at 100% cause queueing even when average is low.

### RED Method (Tom Wilkie) — For Services

For every service endpoint the PR adds or modifies:

- **Rate**: requests per second — does the PR add instrumentation?
- **Errors**: failed requests per second — are error paths counted?
- **Duration**: latency distribution (p50, p95, p99) — are histograms in place?

### Four Golden Signals (Google SRE) — For Production Readiness

- **Latency**: time to serve requests (distinguish success vs failure latency)
- **Traffic**: demand on the system
- **Errors**: rate of failed requests
- **Saturation**: how full the system is (most useful leading indicator)

---

## Tier 1: Blocking Issues

These cause outages, data loss, or cascading failures at scale. Must fix before merge.

### N+1 Query Patterns

**Detection**: ORM lazy loading inside loops, individual DB calls for each item in a collection.

```python
# BAD: N+1 — one query per order
for order in orders:
    items = db.query(Item).filter(Item.order_id == order.id).all()

# GOOD: eager loading
orders = db.query(Order).options(joinedload(Order.items)).all()
```

```go
// BAD: N+1 in Go
for _, user := range users {
    profile, _ := db.GetProfile(user.ID)
}

// GOOD: batch fetch
profiles, _ := db.GetProfilesByUserIDs(userIDs)
```

### Unbounded Data Fetching

**Detection**: queries without LIMIT, `fetchAll()` without bounds, API endpoints without pagination defaults.

Impact at scale: 700k-row table unbounded fetch = 140MB data transfer, 200-400MB memory vs 2KB with LIMIT.

**Check for**:
- Default page size on all list endpoints
- Maximum page size enforced server-side
- Cursor/keyset pagination for deep pages (OFFSET degrades linearly)

### Resource Leaks

**5 critical resource types** to check cleanup paths for:

1. **Memory**: event listeners never removed, closures holding large objects, static collections growing unbounded
2. **File handles**: OS limit 1,024-65,536 per process
3. **DB connections**: pools of 10-100; single leak cascades to service failure
4. **Network sockets**: OS limit ~65,535
5. **Thread/goroutine pools**: unshutdown threads exhaust capacity

**Universal heuristic**: every resource acquisition has corresponding cleanup. Cleanup occurs in finally/defer. Early returns don't bypass cleanup. Loops allocating resources clean them up within the loop body.

```go
// BAD: connection leak on error
conn, err := pool.Get()
result, err := conn.Query(...)
if err != nil {
    return err  // conn never returned to pool
}
conn.Close()

// GOOD: defer cleanup immediately
conn, err := pool.Get()
if err != nil { return err }
defer conn.Close()
```

### Missing Timeouts

**Every outbound call needs a timeout**: HTTP, DB, message queue, lock acquisition, channel receive.

```go
// BAD: blocks forever
resp, err := http.Get(url)

// GOOD: context with timeout
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
resp, err := client.Do(req)
```

### Race Conditions on Shared State

**Detection**: shared mutable state accessed by multiple threads/goroutines without synchronization.

- Go: maps panic on concurrent write — use `sync.Map` or mutex
- Java: `HashMap` corrupts on concurrent access — use `ConcurrentHashMap`
- Check with `go run -race` for Go code

### Goroutine/Thread Leaks

**Detection**: goroutines blocked on channels that never close, missing context cancellation, `go func()` without lifecycle management.

```go
// BAD: goroutine leak — channel never closed if ctx cancelled
go func() {
    result := expensiveWork()
    ch <- result  // blocks forever if nobody reads
}()

// GOOD: select with context
go func() {
    result := expensiveWork()
    select {
    case ch <- result:
    case <-ctx.Done():
    }
}()
```

### Retry Storms

**Detection**: retry logic without exponential backoff and jitter.

```
// BAD: immediate retry — multiplies load during outage
for i := 0; i < 3; i++ {
    err = callService()
    if err == nil { break }
}

// GOOD: exponential backoff + jitter
backoff = baseDelay * 2^attempt + random_jitter
```

Google SRE mandates exponential backoff with jitter on all RPC retry implementations.

### Synchronous Blocking I/O on Hot Path

**Detection**: file reads, network calls, or DB queries executed synchronously on the request-handling thread where async alternatives exist.

### Transaction Scope Too Wide

**Detection**: database transaction held open across network calls, user input, or other high-latency operations. Holds locks, blocks other queries, risks timeout.

---

## Tier 2: Issues

Will cause problems at scale. Should fix, but may not block merge depending on context.

### Database Access

- **Missing indexes**: new WHERE/ORDER BY/JOIN columns without corresponding index
- **SELECT ***: over-fetching columns; select only what's needed
- **Client-side filtering**: `fetchAll()` then filter in app code — push to DB
- **Client-side aggregation**: `sum()` in code vs `SUM()` in SQL
- **Offset pagination**: `OFFSET 10000` degrades linearly; use cursor/keyset for deep pages
- **Implicit type conversions**: function-wrapped columns prevent index usage

### Caching

- **No cache strategy**: expensive repeated computation without caching
- **Cache stampede**: no protection when cache expires under load (solutions: distributed lock, singleflight, probabilistic early expiration with beta=1.5, stale-while-revalidate)
- **TTLs without jitter**: synchronized expiration causes thundering herd
- **Cache without eviction**: unbounded growth; must have max size + eviction policy
- **Cache failure mode**: app fails instead of degrading when cache is down

### Algorithmic and Compute

- **String concatenation in loops**: Go `+=` is 91x slower, 474x more memory vs `strings.Builder`; Java similar with `StringBuilder`
- **Nested loops where hash lookup suffices**: Python nested loops 1,864x slower than dict lookup at n=10,000
- **JSON serialization on hot path**: protobuf is 5-10x faster, 50-80% smaller
- **Regex in loops**: Python `re.match()` inside loop without `re.compile()` = 2x overhead
- **Sequential awaits**: JS `await` in loop is 9-75x slower than `Promise.all()`

### Network and I/O

- **Chatty APIs**: single request triggers 3+ downstream calls; 300-500% worse response times
- **Missing batching**: N individual requests where 1 batch suffices (DataLoader pattern)
- **Connection reuse disabled**: DNS+TCP+TLS = 50-150ms per new connection; keep-alive must be enabled
- **Fan-out without bounded concurrency**: unbounded goroutine/thread spawning per request

### Concurrency

- **Lock granularity too coarse**: global mutex causing contention; consider sharded locks, RWMutex, lock-free structures
- **Queue/buffer without max size**: unbounded queues are the #1 backpressure failure
- **Deadlock risk**: multiple locks acquired in inconsistent order

### Logging

- **Verbose logging on hot paths**: DEBUG/INFO in request path increases disk I/O, GC pressure
- **Missing level guard**: `if logger.isDebugEnabled()` before expensive log construction

---

## Tier 3: Suggestions

Non-blocking. Worth noting for awareness or future improvement.

- **Missing instrumentation**: new code paths without latency/error/throughput metrics
- **No benchmark results**: perf-sensitive changes without before/after numbers
- **Reads hitting primary**: read-heavy queries that could use replicas
- **No cache warm-up**: first-request penalty after deploy; pre-warming strategy absent
- **No graceful degradation**: overload scenario not considered (shed load, return cached/partial results)
- **Suboptimal algorithm**: works but could be more efficient (not blocking if scale is small)
- **Connection pool sizing undocumented**: pool size should be justified (formula: `(cores * 2) + spindles`)
- **Missing circuit breaker**: downstream dependency failure causes cascading retry load

---

## Language-Specific Patterns

### Go
- String `+=` in loops → `strings.Builder` with `Grow()`
- Goroutine leaks → every goroutine needs cancellation via context
- Concurrent map access → `sync.Map` or mutex (bare map panics)
- Missing `defer` for cleanup → connections, files, locks
- Missing `context.WithTimeout` on outbound calls
- `go run -race` should pass

### Java
- `String.format()` and autoboxing on hot paths
- Resources not using try-with-resources → connection leaks
- Thread pools not shut down → `ExecutorService.shutdown()` in finally
- O(n^2) stream iteration inside loops

### Python
- Nested loops → dict lookup (1,864x faster at n=10k)
- `list()` on QuerySet before slicing forces full evaluation
- Application-side aggregation instead of SQL aggregate functions
- `re.match()` in loops without `re.compile()`

### JavaScript/Node.js
- `JSON.parse` in loop → 46x slowdown at 100k iterations
- Sequential `await` in loops → `Promise.all()` (9-75x faster)
- Event listeners never removed → memory leak
- `setInterval` without `clearInterval`

---

## Sources

- Brendan Gregg — USE Method: https://www.brendangregg.com/usemethod.html
- Brendan Gregg — Performance Methodologies: https://www.brendangregg.com/methodology.html
- Brendan Gregg — Flame Graphs: https://www.brendangregg.com/flamegraphs.html
- Tom Wilkie — RED Method via BetterStack: https://betterstack.com/community/guides/monitoring/red-use-metrics/
- Google SRE Best Practices: https://sre.google/sre-book/service-best-practices/
- Google RAIL Model: https://web.dev/articles/rail
- Uber uReview: https://www.uber.com/blog/ureview/
- Go String Concatenation: https://cristiancurteanu.com/why-your-string-concatenation-is-killing-performance-the-hidden-o-n2-trap-in-go/
- Go Concurrency Pitfalls: https://cristiancurteanu.com/7-common-concurrency-pitfalls-in-go-and-how-to-avoid-them/
- Loop Performance Empirical Study: https://stackinsight.dev/blog/loop-performance-empirical-study
- Unbounded Data Fetching: https://dev.to/sanmish4/unbounded-data-fetching-a-silent-performance-anti-pattern-in-api-and-database-layers-1dnk
- Cache Stampede: https://howtech.substack.com/p/thundering-herd-problem-cache-stampede
- Connection Pool Exhaustion: https://howtech.substack.com/p/connection-pool-exhaustion-the-silent
- Chatty Service Anti-Pattern: https://aimconsulting.com/insights/chatty-service-anti-pattern-explained/
- Resource Leak Detection: https://www.propelcode.ai/blog/resource-leak-detection-code-review-comprehensive-guide
- Protobuf vs JSON: https://www.gravitee.io/blog/protobuf-vs-json
- Backpressure Strategies: https://medium.com/@drewjaja/5-ways-of-handling-backpressure-in-distributed-systems-09517ed6eadc
- Designing Data-Intensive Applications — Martin Kleppmann
- Systems Performance — Brendan Gregg
