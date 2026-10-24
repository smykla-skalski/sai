# Good vs Bad Examples

## Contents

- [Commands](#commands)
- [Architecture](#architecture)
- [Gotchas](#gotchas)
- [Format](#format)

---

## Commands

### Good

```markdown
## Commands
- Build: `npm run build`
- Test (full suite): `npm test`
- Test (focused): `npm test -- --testPathPattern="auth"`
- Lint: `npm run lint`
- Pre-commit: `npm run lint && npm test`
```

Specific, correct, includes a focused-test variant and pre-commit workflow.

### Bad

```markdown
## Commands
- Run tests
- Build the project
```

Missing actual commands, no focused-test option, no lint or pre-commit step.

---

## Architecture

### Good

```markdown
## Architecture
- `src/api/` — Express route handlers; each file exports a router mounted in `src/api/index.ts:12`
- `src/services/` — Business logic called by API handlers; never import from `src/api/`
- `src/db/` — Knex query builders; all migrations in `src/db/migrations/`
- Data flow: Request → route handler → service → db query → response
- The `src/services/billing.ts:34` webhook handler is the only entry point for Stripe events
```

Explains relationships, enforces boundaries, uses file:line pointers.

### Bad

```markdown
## Architecture
src/
  api/
  services/
  db/
  utils/
```

A file tree with no explanation of how components relate or what rules govern them.

---

## Gotchas

### Good

```markdown
## Gotchas
- The payment service uses eventual consistency — always check `transaction.status` before assuming completion (see `services/payment.ts:45`)
- Tests that touch the `orders` table must call `resetOrderSequence()` in `afterEach` or subsequent tests get duplicate key errors (see `test/helpers.ts:12`)
```

Project-specific, actionable, points to exact code locations.

### Bad

```markdown
## Gotchas
- Handle errors gracefully
- Make sure tests pass before committing
- Don't forget to update documentation
```

Generic advice that applies to any project. Claude already knows this.

---

## Format

### Good

```markdown
## Style
- Use `snake_case` for DB column names (differs from JS `camelCase` convention)
- Error responses must include `error_code` field — see `src/errors.ts:8` for registry
- Import order enforced by ESLint — see `.eslintrc.js` (do not duplicate rules here)
```

Concise bullets, only project-specific deviations, pointers to config files.

### Bad

```markdown
## Style

We use TypeScript in this project. TypeScript is a typed superset of JavaScript
that compiles to plain JavaScript. All files should use the `.ts` extension.
When writing functions, make sure to add proper type annotations to all parameters
and return values. Here is an example of how we write functions:

export function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => {
    const price = item.price * item.quantity;
    const discount = item.discount ?? 0;
    return sum + (price - discount);
  }, 0);
}

Always follow this pattern when writing new functions.
```

Long paragraph, embedded code block, tells Claude things it already knows about TypeScript.
