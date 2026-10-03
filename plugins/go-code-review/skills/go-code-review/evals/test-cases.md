# Go Code Review — Eval Test Cases

Each case provides an input Go snippet and the expected review output.

## Case 1: Error not wrapped (mistake #49)

**Input:**
```go
func getUser(id int) (*User, error) {
    u, err := db.Find(id)
    if err != nil {
        return nil, err
    }
    return u, nil
}
```

**Expected output contains:**
- Mistake #49
- Severity: Major
- Fix uses `fmt.Errorf("...: %w", err)`

## Case 2: Mutex copied (mistake #74)

**Input:**
```go
type Cache struct {
    mu   sync.Mutex
    data map[string]string
}

func newCache(src Cache) *Cache {
    return &Cache{mu: src.mu, data: src.data}
}
```

**Expected output contains:**
- Mistake #74
- Severity: Critical
- Fix: pass pointer, do not copy sync types

## Case 3: No issues

**Input:**
```go
func add(a, b int) int {
    return a + b
}
```

**Expected output:**
- Explicit statement that no mistakes from the knowledge base were detected
- No invented issues
