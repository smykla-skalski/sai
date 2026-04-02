# Table-Driven Patterns by Language

## Go

```go
func TestParseConfig(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    Config
        wantErr string
    }{
        {name: "valid yaml", input: "key: val", want: Config{Key: "val"}},
        {name: "empty input", input: "", wantErr: "empty config"},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseConfig(tt.input)
            if tt.wantErr != "" {
                require.ErrorContains(t, err, tt.wantErr)
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tt.want, got)
        })
    }
}
```

**Go conventions:**
- Slice var = `tests`, loop var = `tt`
- Expected = `want`/`wantErr`, actual = `got`
- Always include `name string` field
- Use `t.Run()` for subtests
- Use `t.Errorf` (not `t.Fatalf`) inside subtests — let other cases run
- Use `go-cmp` for complex struct diffs: `if diff := cmp.Diff(want, got); diff != ""`
- For complex structs: use functional modifier pattern (mutate a valid base)

## Python

```python
@pytest.mark.parametrize("input_val,expected", [
    pytest.param("valid", Result(ok=True), id="valid-input"),
    pytest.param("", None, id="empty-rejects"),
], ids=lambda x: x)
def test_parse(input_val, expected):
    assert parse(input_val) == expected
```

**Python conventions:**
- Always use `id=` in `pytest.param` — default IDs are cryptic
- Use `pytest.raises(ValueError, match=...)` for error cases
- Separate error table from success table if assertion logic differs

## TypeScript/JavaScript

```typescript
const cases: { name: string; input: string; expected: number }[] = [
  { name: "positive", input: "42", expected: 42 },
  { name: "negative", input: "-1", expected: -1 },
];

test.each(cases)("$name", ({ input, expected }) => {
  expect(parse(input)).toBe(expected);
});
```

## Java

```java
@ParameterizedTest(name = "{0}")
@MethodSource("validInputs")
void parsesValidInput(String name, String input, Config expected) {
    assertEquals(expected, parser.parse(input));
}

static Stream<Arguments> validInputs() {
    return Stream.of(
        Arguments.of("yaml", "key: val", new Config("val")),
        Arguments.of("json", "{\"key\":\"val\"}", new Config("val"))
    );
}
```

## Rust

```rust
#[test_case("valid" => Ok(Config { key: "val".into() }) ; "valid input")]
#[test_case("" => Err("empty".into()) ; "empty input")]
fn test_parse(input: &str) -> Result<Config, String> {
    parse_config(input)
}
```
