# Review Plan

Review implementation plans for completeness, quality, and executor-readiness against planning-agent template standards.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install review-plan@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/review-plan/
```

## Usage

```bash
/review-plan tmp/tasks/add-retry-logic/implementation_plan.md
/review-plan tmp/tasks/add-retry-logic/implementation_plan.md --fix
```

## Skills

- **review-plan**: Audit implementation plans for mandatory sections, workflow commands, git configuration, execution phases, and self-containment. Outputs a verdict-based quality report (PASS / NEEDS WORK / FAIL) with executor-readiness assessment.

## License

MIT
