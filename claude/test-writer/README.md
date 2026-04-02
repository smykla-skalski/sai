# test-writer

Write tests that verify behavior (not implementation), use table-driven/parameterized patterns, and minimize mocking.

## Usage

```bash
claude --plugin-dir claude/test-writer/

# Write tests for a file
/test-writer src/parser.go

# Review existing tests
/test-writer tests/parser_test.go --review

# Override language detection
/test-writer lib/utils.py --lang python
```

## Features

- **Behavior-first testing** — tests survive refactoring, catch real bugs
- **Table-driven by default** — when 3+ cases share the same assertion shape
- **Mock discipline** — only external boundaries, max 2 mocks per test
- **Review mode** — detect 10 anti-patterns in existing tests
- **Multi-language** — Go, Python, TypeScript, Java, Rust

## Philosophy

Test what the code does, not how it does it. If you refactor internals and tests break — the tests are wrong, not the code.

## References

- `references/testing-principles.md` — core testing principles knowledge base
- `references/language-patterns.md` — idiomatic table-driven patterns per language
